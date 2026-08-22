"""HTTP e WebSocket do módulo voice.

O WebSocket `/ws/voice` usa o protocolo versionado Voice V1. A V0 mantém
STT/TTS batch, mas liga o transcript ao ConversationService existente e
devolve a resposta em texto + um frame binário de áudio.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import MutableMapping
from dataclasses import dataclass, field
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
from app.modules.conversation.application import get_conversation_service
from app.modules.security.domain import AuthResult
from app.modules.security.infrastructure import authenticate_ws
from app.modules.security.router import require_authenticated_user
from app.modules.voice.application import VoiceService
from app.modules.voice.domain import (
    VoiceProtocolError,
    VoiceProviderError,
    VoiceSessionState,
    VoiceUnavailableError,
    transition_voice_state,
)

router = APIRouter(prefix="/voice", tags=["voice"])
voice_ws_router = APIRouter(tags=["voice"])

logger = structlog.get_logger("negao.voice")

VOICE_PROTOCOL_VERSION = 1
VOICE_AUDIO_CONTENT_TYPE = "audio/webm"
VOICE_AUDIO_FORMAT = "audio/webm"
POLICY_CLOSE_CODE = 1008
TRY_AGAIN_CLOSE_CODE = 1013
MESSAGE_TOO_BIG_CLOSE_CODE = 1009
INACTIVE_CLOSE_CODE = 1001

_BOUNDARY_RE = re.compile(r"boundary=([^;\"\s]+)")
_PART_CONTENT_TYPE_RE = re.compile(r"content-type:\s*([^;\r\n]+)")
_AUDIO_CONTENT_TYPE_RE = re.compile(r"^audio/webm(?:;codecs=opus)?$", re.IGNORECASE)

_voice_ws_limiter: RateLimiter | None = None
_active_voice_sessions = 0
_voice_session_lock = asyncio.Lock()


class _SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


@dataclass
class _WsVoiceSession:
    """Estado de uma conexão Voice V1, sem persistir áudio bruto."""

    auth: AuthResult
    state: VoiceSessionState = VoiceSessionState.CONNECTED
    session_id: str | None = None
    interaction_id: str | None = None
    audio_format: str = VOICE_AUDIO_FORMAT
    audio: bytearray = field(default_factory=bytearray)
    turn_started_at: float | None = None
    connected_at: float = field(default_factory=time.monotonic)


def _get_voice_ws_limiter() -> RateLimiter:
    global _voice_ws_limiter
    if _voice_ws_limiter is None:
        _voice_ws_limiter = RateLimiter(limit=get_settings().rate_limit_burst)
    return _voice_ws_limiter


def _get_voice_service() -> VoiceService:
    from app.modules.voice.application import get_voice_service

    return get_voice_service()


async def _reserve_voice_session() -> bool:
    global _active_voice_sessions
    async with _voice_session_lock:
        limit = get_settings().voice_max_concurrent_sessions
        if _active_voice_sessions >= limit:
            return False
        _active_voice_sessions += 1
        return True


async def _release_voice_session() -> None:
    global _active_voice_sessions
    async with _voice_session_lock:
        _active_voice_sessions = max(0, _active_voice_sessions - 1)


async def _check_rate_limit(ws: WebSocket, bucket: str | None = None) -> bool:
    client_ip = ws.client.host if ws.client else "unknown"
    allowed, _, _, _ = await _get_voice_ws_limiter().allow(bucket or client_ip)
    if not allowed:
        logger.warning("voice_ws_rate_limited", client_ip=client_ip)
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="rate limited")
        return False
    return True


def _transition(session: _WsVoiceSession, event: str) -> None:
    session.state = transition_voice_state(session.state, event)


async def _send_state(ws: WebSocket, session: _WsVoiceSession) -> None:
    await ws.send_json(
        {
            "type": "voice.state",
            "version": VOICE_PROTOCOL_VERSION,
            "state": session.state.value,
            "session_id": session.session_id,
            "interaction_id": session.interaction_id,
        }
    )


async def _send_error(
    ws: WebSocket,
    session: _WsVoiceSession,
    code: str,
    message: str,
    *,
    close_code: int | None = None,
) -> None:
    await ws.send_json(
        {
            "type": "voice.error",
            "version": VOICE_PROTOCOL_VERSION,
            "code": code,
            "message": message,
            "interaction_id": session.interaction_id,
        }
    )
    if close_code is not None:
        await ws.close(code=close_code, reason=code)


async def _recover_turn(
    ws: WebSocket,
    session: _WsVoiceSession,
    code: str,
    message: str,
) -> None:
    session.audio.clear()
    session.turn_started_at = None
    try:
        session.state = transition_voice_state(session.state, "turn.error")
    except VoiceProtocolError:
        session.state = VoiceSessionState.ERROR
    await _send_error(ws, session, code, message)
    if session.state is VoiceSessionState.ERROR:
        try:
            session.state = transition_voice_state(session.state, "recover")
        except VoiceProtocolError:
            return
    await _send_state(ws, session)


def _parse_protocol_message(raw_text: str) -> dict[str, Any]:
    try:
        message = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise VoiceProtocolError("invalid json") from exc
    if not isinstance(message, dict):
        raise VoiceProtocolError("message must be a JSON object")
    if message.get("version") != VOICE_PROTOCOL_VERSION:
        raise VoiceProtocolError("unsupported protocol version")
    if not isinstance(message.get("type"), str):
        raise VoiceProtocolError("message type is required")
    return message


def _bounded_text(message: dict[str, Any], key: str, max_length: int) -> str:
    value = message.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise VoiceProtocolError(f"invalid {key}")
    return value.strip()


async def _handle_session_start(
    ws: WebSocket, session: _WsVoiceSession, message: dict[str, Any]
) -> None:
    if session.state is not VoiceSessionState.CONNECTED:
        raise VoiceProtocolError("session already started")
    requested_session = _bounded_text(message, "session_id", 64)
    if not session.auth.session_id or requested_session != session.auth.session_id:
        await _send_error(
            ws,
            session,
            "SESSION_MISMATCH",
            "A sessão de voz não corresponde ao ticket.",
            close_code=POLICY_CLOSE_CODE,
        )
        return
    owner_id = session.auth.effective_user_id
    if owner_id is None or not await get_conversation_service().owns_session(
        requested_session, owner_id
    ):
        await _send_error(
            ws,
            session,
            "SESSION_NOT_FOUND",
            "A sessão de voz não pertence ao usuário autenticado.",
            close_code=POLICY_CLOSE_CODE,
        )
        return
    session.session_id = requested_session
    session.interaction_id = _bounded_text(message, "interaction_id", 128)
    _transition(session, "session.start")
    await ws.send_json(
        {
            "type": "voice.session.started",
            "version": VOICE_PROTOCOL_VERSION,
            "session_id": session.session_id,
        }
    )
    await _send_state(ws, session)


async def _handle_turn_start(
    ws: WebSocket, session: _WsVoiceSession, message: dict[str, Any]
) -> None:
    if session.state not in {VoiceSessionState.SESSION_READY, VoiceSessionState.IDLE}:
        raise VoiceProtocolError("turn.start is not valid in the current state")
    audio_format = message.get("format")
    if audio_format != VOICE_AUDIO_FORMAT:
        raise VoiceProtocolError("unsupported audio format")
    session.interaction_id = _bounded_text(message, "interaction_id", 128)
    session.audio_format = audio_format
    session.audio.clear()
    session.turn_started_at = time.monotonic()
    _transition(session, "turn.start")
    await _send_state(ws, session)


async def _handle_audio_chunk(ws: WebSocket, session: _WsVoiceSession, audio: bytes) -> None:
    settings = get_settings()
    if session.state is not VoiceSessionState.LISTENING:
        await _send_error(ws, session, "INVALID_STATE", "Inicie um turno antes do áudio.")
        return
    if len(audio) > settings.voice_max_chunk_bytes:
        await _send_error(
            ws,
            session,
            "AUDIO_CHUNK_TOO_LARGE",
            "O bloco de áudio excede o limite permitido.",
            close_code=MESSAGE_TOO_BIG_CLOSE_CODE,
        )
        return
    if session.turn_started_at is not None:
        elapsed = time.monotonic() - session.turn_started_at
        if elapsed > settings.voice_max_turn_seconds:
            await _send_error(
                ws,
                session,
                "TURN_TIMEOUT",
                "O turno de voz excedeu o tempo máximo.",
                close_code=MESSAGE_TOO_BIG_CLOSE_CODE,
            )
            return
    if len(session.audio) + len(audio) > settings.voice_max_turn_bytes:
        await _send_error(
            ws,
            session,
            "AUDIO_TURN_TOO_LARGE",
            "O turno de áudio excede o limite permitido.",
            close_code=MESSAGE_TOO_BIG_CLOSE_CODE,
        )
        return
    session.audio.extend(audio)


async def _handle_turn(ws: WebSocket, session: _WsVoiceSession) -> None:
    if session.state is not VoiceSessionState.LISTENING:
        raise VoiceProtocolError("turn.end is not valid in the current state")
    if not session.audio:
        await _recover_turn(ws, session, "EMPTY_AUDIO", "Não recebemos áudio neste turno.")
        return
    if session.turn_started_at is not None:
        if time.monotonic() - session.turn_started_at > get_settings().voice_max_turn_seconds:
            await _recover_turn(
                ws, session, "TURN_TIMEOUT", "O turno de voz excedeu o tempo máximo."
            )
            return
    audio = bytes(session.audio)
    session.audio.clear()
    session.turn_started_at = None
    _transition(session, "turn.end")
    await _send_state(ws, session)

    started_at = time.monotonic()
    try:
        transcript = await _get_voice_service().transcribe(
            audio, content_type=VOICE_AUDIO_CONTENT_TYPE
        )
    except (VoiceUnavailableError, VoiceProviderError):
        logger.warning("voice_ws_transcribe_failed", session_id=session.session_id)
        await _recover_turn(ws, session, "STT_FAILED", "Não foi possível transcrever o áudio.")
        return
    logger.info(
        "voice_stt_completed",
        session_id=session.session_id,
        interaction_id=session.interaction_id,
        duration_ms=int((time.monotonic() - started_at) * 1000),
    )
    if not transcript.text.strip():
        await _recover_turn(ws, session, "STT_EMPTY", "Não foi possível identificar uma fala.")
        return

    _transition(session, "transcript.final")
    await ws.send_json(
        {
            "type": "voice.transcript.final",
            "version": VOICE_PROTOCOL_VERSION,
            "interaction_id": session.interaction_id,
            "text": transcript.text,
        }
    )
    await _send_state(ws, session)
    await ws.send_json(
        {
            "type": "voice.response.started",
            "version": VOICE_PROTOCOL_VERSION,
            "interaction_id": session.interaction_id,
        }
    )

    try:
        conversation = await asyncio.wait_for(
            get_conversation_service().chat(
                session.session_id or "",
                transcript.text,
                user_id=session.auth.effective_user_id,
            ),
            timeout=get_settings().voice_conversation_timeout_seconds,
        )
    except Exception:
        logger.exception(
            "voice_conversation_failed",
            session_id=session.session_id,
            interaction_id=session.interaction_id,
        )
        await _recover_turn(
            ws, session, "CONVERSATION_FAILED", "Não foi possível processar a conversa."
        )
        return

    _transition(session, "response.text")
    await ws.send_json(
        {
            "type": "voice.response.text",
            "version": VOICE_PROTOCOL_VERSION,
            "interaction_id": session.interaction_id,
            "text": conversation.text,
        }
    )
    await _send_state(ws, session)

    try:
        audio_result = await _get_voice_service().synthesize(conversation.text)
    except VoiceProviderError:
        logger.warning(
            "voice_ws_synthesize_failed",
            session_id=session.session_id,
            interaction_id=session.interaction_id,
        )
        await _recover_turn(
            ws, session, "TTS_FAILED", "A resposta foi gerada, mas não foi possível falar."
        )
        return

    _transition(session, "response.audio")
    await ws.send_json(
        {
            "type": "voice.response.audio",
            "version": VOICE_PROTOCOL_VERSION,
            "interaction_id": session.interaction_id,
            "format": audio_result.content_type,
            "bytes": len(audio_result.data),
        }
    )
    await ws.send_bytes(audio_result.data)
    _transition(session, "response.completed")
    await ws.send_json(
        {
            "type": "voice.response.completed",
            "version": VOICE_PROTOCOL_VERSION,
            "interaction_id": session.interaction_id,
        }
    )
    await _send_state(ws, session)


async def _handle_voice_json(ws: WebSocket, session: _WsVoiceSession, raw_text: str) -> bool:
    try:
        message = _parse_protocol_message(raw_text)
        message_type = message["type"]
        if message_type == "voice.session.start":
            await _handle_session_start(ws, session, message)
        elif message_type == "voice.turn.start":
            await _handle_turn_start(ws, session, message)
        elif message_type == "voice.turn.end":
            await _handle_turn(ws, session)
        elif message_type == "voice.session.stop":
            _transition(session, "session.stop")
            await ws.send_json(
                {
                    "type": "voice.session.stopped",
                    "version": VOICE_PROTOCOL_VERSION,
                    "session_id": session.session_id,
                }
            )
            return True
        else:
            raise VoiceProtocolError("unsupported message type")
    except VoiceProtocolError as exc:
        await _send_error(ws, session, "INVALID_MESSAGE", str(exc))
    return False


async def _handle_voice_frame(
    ws: WebSocket, session: _WsVoiceSession, raw: MutableMapping[str, Any]
) -> bool:
    text = raw.get("text")
    if isinstance(text, str):
        return await _handle_voice_json(ws, session, text)
    audio = raw.get("bytes")
    if isinstance(audio, bytes):
        await _handle_audio_chunk(ws, session, audio)
    return False


async def _voice_session_loop(ws: WebSocket, session: _WsVoiceSession, client_id: str) -> None:
    settings = get_settings()
    while True:
        elapsed = time.monotonic() - session.connected_at
        remaining = settings.voice_session_max_seconds - elapsed
        if remaining <= 0:
            await _send_error(
                ws,
                session,
                "SESSION_MAX_TIMEOUT",
                "A sessão de voz atingiu o tempo máximo.",
            )
            await ws.close(code=INACTIVE_CLOSE_CODE, reason="session max timeout")
            return
        try:
            raw = await asyncio.wait_for(
                ws.receive(),
                timeout=min(settings.voice_idle_timeout_seconds, remaining),
            )
        except TimeoutError:
            logger.info("voice_ws_closed_inactive", client_id=client_id)
            await _send_error(
                ws,
                session,
                "IDLE_TIMEOUT",
                "A sessão de voz foi encerrada por inatividade.",
            )
            await ws.close(code=INACTIVE_CLOSE_CODE, reason="inactive")
            return
        except WebSocketDisconnect:
            return
        if raw.get("type") != "websocket.receive":
            return
        if await _handle_voice_frame(ws, session, raw):
            await ws.close(code=1000, reason="session stopped")
            return


@voice_ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(ws: WebSocket) -> None:
    """Autentica o ticket antes do accept e executa uma sessão Voice V1."""
    auth = await authenticate_ws(
        ws,
        expected_purpose="voice",
        allow_api_key_fallback=False,
    )
    if not auth.authenticated or not auth.session_id:
        logger.warning("voice_ws_auth_failed", reason=auth.reason)
        await ws.close(code=POLICY_CLOSE_CODE, reason="invalid voice ticket")
        return
    if not await _check_rate_limit(ws, auth.effective_user_id):
        return
    if not await _reserve_voice_session():
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="voice session limit")
        return

    await ws.accept()
    metadata = connection_manager.connect(ws)
    if metadata is None:
        await _release_voice_session()
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="max connections reached")
        return
    client_id = metadata["client_id"]
    session = _WsVoiceSession(auth=auth)
    logger.info("voice_ws_connected", client_id=client_id, session_id=auth.session_id)
    try:
        await _voice_session_loop(ws, session, client_id)
    except Exception:
        logger.exception("voice_ws_error", client_id=client_id, session_id=session.session_id)
    finally:
        connection_manager.disconnect(ws)
        await _release_voice_session()
        logger.info("voice_ws_disconnected", client_id=client_id, session_id=session.session_id)


def _parse_multipart_file(body: bytes, content_type: str) -> tuple[bytes, str] | None:
    """Extrai o primeiro campo `file` de um body multipart/form-data."""
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
        return payload, part_ct.group(1).strip() if part_ct else VOICE_AUDIO_CONTENT_TYPE
    return None


async def _extract_audio_upload(request: Request) -> tuple[bytes, str]:
    """Lê áudio batch com teto de bytes e content-type explícito."""
    settings = get_settings()
    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit():
        if int(declared_length) > settings.voice_max_turn_bytes + 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="audio payload too large",
            )
    raw = await request.body()
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        parsed = _parse_multipart_file(raw, content_type)
        if parsed is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid multipart body — campo 'file' ausente",
            )
        raw, content_type = parsed
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty audio")
    if len(raw) > settings.voice_max_turn_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="audio payload too large",
        )
    if not _AUDIO_CONTENT_TYPE_RE.fullmatch(content_type.strip()):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported audio format",
        )
    return raw, VOICE_AUDIO_CONTENT_TYPE


@router.get("/status")
async def voice_status(
    _auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, object]:
    settings = get_settings()
    return {
        "stt_available": bool(settings.nvidia_api_key),
        "tts_available": True,
        "stt_model": settings.brain_stt_model,
        "tts_voice": settings.tts_voice,
        "protocol_version": VOICE_PROTOCOL_VERSION,
        "audio_format": VOICE_AUDIO_FORMAT,
        "limits": {
            "max_chunk_bytes": settings.voice_max_chunk_bytes,
            "max_turn_bytes": settings.voice_max_turn_bytes,
            "max_turn_seconds": settings.voice_max_turn_seconds,
        },
    }


@router.post("/transcribe")
async def voice_transcribe(
    request: Request,
    _auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> dict[str, str]:
    audio, content_type = await _extract_audio_upload(request)
    try:
        result = await _get_voice_service().transcribe(audio, content_type=content_type)
    except VoiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT indisponível no momento",
        ) from exc
    except VoiceProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível transcrever o áudio",
        ) from exc
    return {"text": result.text}


@router.post("/synthesize")
async def voice_synthesize(
    body: _SynthesizeRequest,
    _auth: Annotated[AuthResult, Depends(require_authenticated_user)],
) -> Response:
    try:
        result = await _get_voice_service().synthesize(body.text.strip())
    except VoiceProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível sintetizar a resposta",
        ) from exc
    return Response(content=result.data, media_type=result.content_type)
