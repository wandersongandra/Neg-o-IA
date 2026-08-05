"""Interface HTTP e WebSocket do módulo conversation.

HTTP (prefixo /conversation): status, sessões, histórico e chat síncrono.
WS (/ws/conversation): chat assíncrono com streaming de tokens.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.modules.api.rate_limit import RateLimiter
from app.modules.api.websocket import (
    POLICY_CLOSE_CODE,
    SHUTDOWN_CLOSE_CODE,
    TRY_AGAIN_CLOSE_CODE,
    connection_manager,
)
from app.modules.configuration.settings import get_settings
from app.modules.conversation.application import get_conversation_service
from app.modules.security.infrastructure import get_security_service
from app.modules.security.router import require_api_key

logger = structlog.get_logger("negao.conversation")
router = APIRouter(prefix="/conversation", tags=["conversation"])
ws_router = APIRouter(tags=["conversation"])

IDLE_TIMEOUT_SECONDS = 60.0
MAX_IDLE_PINGS = 2
TOKEN_CHUNK_WORDS = 3

_ws_limiter: RateLimiter | None = None


class SessionCreateRequest(BaseModel):
    user_id: str | None = None


class SessionRenameRequest(BaseModel):
    name: str | None = None


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def _get_ws_limiter() -> RateLimiter:
    global _ws_limiter
    if _ws_limiter is None:
        _ws_limiter = RateLimiter(limit=get_settings().rate_limit_burst)
    return _ws_limiter


def _chunk_text(text: str, words_per_chunk: int = TOKEN_CHUNK_WORDS) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


@router.get("/status")
async def conversation_status() -> dict[str, object]:
    try:
        sessions = await get_conversation_service().list_sessions()
        return {"sessions": len(sessions), "degraded": False}
    except Exception:
        return {"sessions": 0, "degraded": True}


@router.post("/sessions")
async def create_session(
    body: SessionCreateRequest | None = None,
    auth: object = Depends(require_api_key),
) -> dict[str, object]:
    session = await get_conversation_service().start_session(
        user_id=getattr(auth, "principal", None)
    )
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "created_at": session.created_at,
        "message_count": session.message_count,
    }


@router.get("/sessions")
async def list_sessions(
    auth: object = Depends(require_api_key),
) -> dict[str, object]:
    sessions = await get_conversation_service().list_sessions()
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "message_count": s.message_count,
                "name": getattr(s, "name", None),
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    auth: object = Depends(require_api_key),
) -> dict[str, object]:
    messages = await get_conversation_service().get_messages(session_id)
    return {
        "session_id": session_id,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
    }


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    body: SessionRenameRequest,
    auth: object = Depends(require_api_key),
) -> dict[str, object]:
    ok = await get_conversation_service().rename_session(session_id, body.name)
    if not ok:
        raise HTTPException(status_code=404, detail="sessão não encontrada")
    return {"session_id": session_id, "name": body.name, "updated_at": get_settings().redis_url}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    auth: object = Depends(require_api_key),
) -> dict[str, object]:
    ok = await get_conversation_service().delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="sessão não encontrada")
    return {"deleted": True, "session_id": session_id}


@router.post("/sessions/{session_id}/messages")
async def post_message(
    session_id: str,
    body: MessageRequest,
    auth: object = Depends(require_api_key),
) -> dict[str, object]:
    try:
        result = await get_conversation_service().chat(
            session_id, body.text, user_id=getattr(auth, "principal", None)
        )
    except Exception as exc:
        logger.exception("conversation_chat_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Falha ao processar a conversa") from exc
    return {
        "text": result.text,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback_used,
    }


@ws_router.websocket("/ws/conversation")
async def conversation_websocket(ws: WebSocket) -> None:
    await ws.accept()
    client_ip = ws.client.host if ws.client else "unknown"
    allowed, _, _, _ = await _get_ws_limiter().allow(client_ip)
    if not allowed:
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="rate limited")
        return
    auth = get_security_service().authenticate_api_key(
        ws.query_params.get("api_key", "")
    )
    if not auth.authenticated:
        logger.warning("conversation_ws_auth_failed", reason=auth.reason)
        await ws.close(code=POLICY_CLOSE_CODE, reason="invalid api key")
        return
    metadata = connection_manager.connect(ws)
    if metadata is None:
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="max connections reached")
        return
    client_id = metadata["client_id"]
    service = get_conversation_service()
    session_id: str | None = None
    idle_pings = 0
    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    ws.receive_json(), timeout=IDLE_TIMEOUT_SECONDS
                )
            except TimeoutError:
                idle_pings += 1
                await ws.send_json(
                    {
                        "type": "ping",
                        "server_time": str(asyncio.get_event_loop().time()),
                    }
                )
                if idle_pings >= MAX_IDLE_PINGS:
                    await ws.close(code=SHUTDOWN_CLOSE_CODE, reason="inactive")
                    return
                continue
            except WebSocketDisconnect:
                break
            idle_pings = 0
            if not isinstance(raw, dict) or not isinstance(raw.get("type"), str):
                await ws.send_json({"type": "error", "detail": "mensagem inválida"})
                continue
            msg_type = raw.get("type")
            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
            elif msg_type == "start":
                session = await service.start_session(user_id=auth.principal)
                session_id = session.session_id
                await ws.send_json(
                    {"type": "session", "session_id": session_id, "created": True}
                )
            elif msg_type == "chat":
                text = raw.get("text")
                if not isinstance(text, str) or not text.strip():
                    await ws.send_json({"type": "error", "detail": "texto vazio"})
                    continue
                target = raw.get("session_id") or session_id
                if not target:
                    session = await service.start_session(user_id=auth.principal)
                    target = session.session_id
                    session_id = target
                    await ws.send_json(
                        {"type": "session", "session_id": target, "created": True}
                    )
                try:
                    result = await service.chat(target, text, user_id=auth.principal)
                except Exception as exc:
                    logger.exception("conversation_ws_chat_failed", error=str(exc))
                    await ws.send_json(
                        {"type": "error", "detail": "falha ao processar a conversa"}
                    )
                    continue
                for chunk in _chunk_text(result.text):
                    await ws.send_json({"type": "tokens", "delta": chunk})
                await ws.send_json(
                    {
                        "type": "done",
                        "text": result.text,
                        "model": result.model,
                        "latency_ms": result.latency_ms,
                        "fallback_used": result.fallback_used,
                        "session_id": target,
                    }
                )
            elif msg_type == "reset":
                target = raw.get("session_id") or session_id
                if target:
                    await service.reset_session(target)
                    await ws.send_json({"type": "reset_ok", "session_id": target})
            else:
                await ws.send_json({"type": "error", "detail": "tipo de mensagem não suportado"})
    except Exception:
        logger.exception("conversation_ws_error", client_id=client_id)
    finally:
        connection_manager.disconnect(ws)
