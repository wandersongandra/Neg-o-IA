"""Router do módulo voice — HTTP (status/transcribe/synthesize) + WebSocket /ws/voice.

Autenticação do WebSocket é idêntica ao /ws existente: `accept()` primeiro,
depois `api_key` via query param (close 1008) e burst rate limit. A conexão
é registrada no `connection_manager` compartilhado (limite global de conexões).

Protocolo do cliente: `{"type":"start","session_id":str|None}` inicia sessão,
frames binários acumulam áudio, `{"type":"end"}` transcreve, e
`{"type":"speak","text":str}` devolve um frame binário de áudio TTS.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Annotated, Any

import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from app.modules.api.rate_limit import RateLimiter
from app.modules.api.websocket import connection_manager
from app.modules.configuration.settings import get_settings
from app.modules.security.domain import AuthResult
from app.modules.security.infrastructure import get_security_service
from app.modules.security.router import require_api_key
from app.modules.voice.application import VoiceService
from app.modules.voice.domain import VoiceProviderError, VoiceUnavailableError

router = APIRouter(prefix="/voice", tags=["voice"])
voice_ws_router = APIRouter(tags=["voice"])

logger = structlog.get_logger("negao.voice")

IDLE_TIMEOUT_SECONDS = 60.0
POLICY_CLOSE_CODE = 1008
TRY_AGAIN_CLOSE_CODE = 1013
INACTIVE_CLOSE_CODE = 1001

_WS_AUDIO_CONTENT_TYPE = "audio/webm"

_BOUNDARY_RE = re.compile(r"boundary=([^;\"\s]+)")
_PART_CONTENT_TYPE_RE = re.compile(r"content-type:\s*([^;\r\n]+)")


def _parse_multipart_file(body: bytes, content_type: str) -> tuple[bytes, str] | None:
    """Extrai o primeiro campo `file` de um body multipart/form-data (sem lib externa)."""
    match = _BOUNDARY_RE.search(content_type)
    if match is None:
        return None
    parts = body.split(b"--" + match.group(1).encode("utf-8"))
    for part in parts:
        if not part.startswith(b"\r\n"):
            continue
        part = part[2:]
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        headers_block = part[:header_end].decode("utf-8", errors="replace").lower()
        payload = part[header_end + 4 :]
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if (
            "content-disposition: form-data" not in headers_block
            or 'name="file"' not in headers_block
        ):
            continue
        part_ct = _PART_CONTENT_TYPE_RE.search(headers_block)
        return payload, part_ct.group(1) if part_ct else _WS_AUDIO_CONTENT_TYPE
    return None


async def _extract_audio_upload(request: Request) -> tuple[bytes, str]:
    """Lê o áudio do request: body cru, ou o campo `file` se multipart/form-data."""
    raw = await request.body()
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("multipart/form-data"):
        return raw, content_type or _WS_AUDIO_CONTENT_TYPE
    parsed = _parse_multipart_file(raw, content_type)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid multipart body — campo 'file' ausente",
        )
    return parsed

_voice_ws_limiter: RateLimiter | None = None


class _SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


@dataclass
class _WsVoiceSession:
    """Estado de uma sessão de voz no WebSocket (acumulador de áudio)."""

    session_id: str | None = None
    audio: bytearray | None = None


def _get_voice_ws_limiter() -> RateLimiter:
    global _voice_ws_limiter
    if _voice_ws_limiter is None:
        _voice_ws_limiter = RateLimiter(limit=get_settings().rate_limit_burst)
    return _voice_ws_limiter


def _get_voice_service() -> VoiceService:
    from app.modules.voice.application import get_voice_service

    return get_voice_service()


async def _check_rate_limit(ws: WebSocket) -> bool:
    client_ip = ws.client.host if ws.client else "unknown"
    allowed, _, _, _ = await _get_voice_ws_limiter().allow(client_ip)
    if not allowed:
        logger.warning("voice_ws_rate_limited", client_ip=client_ip)
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="rate limited")
        return False
    return True


async def _handle_voice_audio(ws: WebSocket, session: _WsVoiceSession, audio: bytes) -> None:
    if session.audio is None:
        await ws.send_json({"type": "error", "detail": "no active session"})
        return
    session.audio.extend(audio)


async def _handle_voice_end(ws: WebSocket, session: _WsVoiceSession) -> None:
    if session.audio is None or not session.audio:
        await ws.send_json({"type": "error", "detail": "no audio to transcribe"})
        return
    audio = bytes(session.audio)
    session.audio = None
    try:
        result = await _get_voice_service().transcribe(
            audio, content_type=_WS_AUDIO_CONTENT_TYPE
        )
    except (VoiceUnavailableError, VoiceProviderError) as exc:
        logger.warning("voice_ws_transcribe_failed", error=str(exc))
        await ws.send_json({"type": "error", "detail": str(exc)})
        return
    await ws.send_json(
        {"type": "transcript", "text": result.text, "session_id": session.session_id}
    )


async def _handle_voice_speak(ws: WebSocket, message: dict[str, Any]) -> None:
    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        await ws.send_json({"type": "error", "detail": "speak requires non-empty text"})
        return
    try:
        result = await _get_voice_service().synthesize(text.strip())
    except VoiceProviderError as exc:
        logger.warning("voice_ws_synthesize_failed", error=str(exc))
        await ws.send_json({"type": "error", "detail": str(exc)})
        return
    await ws.send_bytes(result.data)
    await ws.send_json(
        {"type": "audio", "content_type": result.content_type, "bytes": len(result.data)}
    )


async def _handle_voice_json(ws: WebSocket, session: _WsVoiceSession, raw_text: str) -> None:
    try:
        message = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        await ws.send_json({"type": "error", "detail": "invalid json"})
        return
    if not isinstance(message, dict):
        await ws.send_json({"type": "error", "detail": "message must be a JSON object"})
        return
    message_type = message.get("type")
    if message_type == "start":
        session_id = message.get("session_id")
        session.session_id = session_id if isinstance(session_id, str) else None
        session.audio = bytearray()
        return
    if message_type == "end":
        await _handle_voice_end(ws, session)
        return
    if message_type == "speak":
        await _handle_voice_speak(ws, message)
        return
    await ws.send_json({"type": "error", "detail": "unsupported message type"})


async def _handle_voice_frame(
    ws: WebSocket, session: _WsVoiceSession, raw: MutableMapping[str, Any]
) -> None:
    text = raw.get("text")
    if text is not None:
        await _handle_voice_json(ws, session, text)
        return
    audio = raw.get("bytes")
    if audio is not None:
        await _handle_voice_audio(ws, session, audio)


async def _voice_session_loop(ws: WebSocket, client_id: str) -> None:
    session = _WsVoiceSession()
    while True:
        try:
            raw = await asyncio.wait_for(ws.receive(), timeout=IDLE_TIMEOUT_SECONDS)
        except TimeoutError:
            logger.info("voice_ws_closed_inactive", client_id=client_id)
            await ws.close(code=INACTIVE_CLOSE_CODE, reason="inactive")
            return
        except WebSocketDisconnect:
            return
        if raw.get("type") != "websocket.receive":
            return
        await _handle_voice_frame(ws, session, raw)


@voice_ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    if not await _check_rate_limit(ws):
        return
    auth = get_security_service().authenticate_api_key(ws.query_params.get("api_key", ""))
    if not auth.authenticated:
        logger.warning("voice_ws_auth_failed", reason=auth.reason)
        await ws.close(code=POLICY_CLOSE_CODE, reason="invalid api key")
        return
    metadata = connection_manager.connect(ws)
    if metadata is None:
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="max connections reached")
        return
    client_id = metadata["client_id"]
    logger.info("voice_ws_connected", client_id=client_id)
    try:
        await _voice_session_loop(ws, client_id)
    except Exception:
        logger.exception("voice_ws_error", client_id=client_id)
    finally:
        connection_manager.disconnect(ws)
        logger.info("voice_ws_disconnected", client_id=client_id)


@router.get("/status")
async def voice_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "stt_available": bool(settings.nvidia_api_key),
        "tts_available": True,
        "stt_model": settings.brain_stt_model,
        "tts_voice": settings.tts_voice,
    }


@router.post("/transcribe")
async def voice_transcribe(
    request: Request,
    _auth: Annotated[AuthResult, Depends(require_api_key)],
) -> dict[str, str]:
    audio, content_type = await _extract_audio_upload(request)
    try:
        result = await _get_voice_service().transcribe(audio, content_type=content_type)
    except VoiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except VoiceProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {"text": result.text}


@router.post("/synthesize")
async def voice_synthesize(body: _SynthesizeRequest) -> Response:
    try:
        result = await _get_voice_service().synthesize(body.text.strip())
    except VoiceProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return Response(content=result.data, media_type=result.content_type)
