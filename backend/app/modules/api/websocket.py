"""WebSocket endpoint do NEGÃO AI — protocolo JSON com heartbeat.

Protocolo (client → server): `{"type":"ping","ts":<float>}`.
Protocolo (server → client): `{"type":"pong","ts":<float>,"server_time":<iso>}`,
`{"type":"lifecycle","event":"connected"|"disconnected","client_id":...}`,
`{"type":"error","detail":...}`.

Acesso é default-deny: `api_key` via query param é SEMPRE exigida.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.modules.api.rate_limit import RateLimiter
from app.modules.configuration.settings import get_settings
from app.modules.security.infrastructure import get_security_service

logger = structlog.get_logger("negao.ws")
router = APIRouter(tags=["infra"])

IDLE_TIMEOUT_SECONDS = 60.0
MAX_IDLE_PINGS = 2
SHUTDOWN_CLOSE_CODE = 1001
POLICY_CLOSE_CODE = 1008
TRY_AGAIN_CLOSE_CODE = 1013


class ConnectionManager:
    """Registro central das conexões WebSocket ativas."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, dict[str, str]] = {}
        self._max_connections = get_settings().ws_max_connections

    def connect(self, ws: WebSocket) -> dict[str, str] | None:
        """Registra a conexão; retorna os metadados ou None se o limite for atingido."""
        if len(self._connections) >= self._max_connections:
            logger.warning("ws_connection_rejected", active=len(self._connections))
            return None
        metadata = {
            "client_id": str(uuid.uuid4()),
            "connected_at": datetime.now(UTC).isoformat(),
        }
        self._connections[ws] = metadata
        logger.info(
            "ws_connected",
            client_id=metadata["client_id"],
            active=len(self._connections),
        )
        return metadata

    def disconnect(self, ws: WebSocket) -> None:
        metadata = self._connections.pop(ws, None)
        if metadata is not None:
            logger.info(
                "ws_disconnected",
                client_id=metadata["client_id"],
                active=len(self._connections),
            )

    async def send_personal(self, ws: WebSocket, message: dict[str, object]) -> None:
        await ws.send_json(message)

    async def broadcast(self, message: dict[str, object]) -> None:
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("ws_broadcast_failed", exc_info=True)

    def active_count(self) -> int:
        return len(self._connections)

    async def disconnect_all(self) -> None:
        connections = list(self._connections)
        self._connections.clear()
        for ws in connections:
            try:
                await ws.close(code=SHUTDOWN_CLOSE_CODE, reason="server shutdown")
            except Exception:
                logger.debug("ws_close_failed", exc_info=True)


connection_manager = ConnectionManager()

_ws_limiter: RateLimiter | None = None


def _get_ws_limiter() -> RateLimiter:
    global _ws_limiter
    if _ws_limiter is None:
        _ws_limiter = RateLimiter(limit=get_settings().rate_limit_burst)
    return _ws_limiter


async def _check_rate_limit(ws: WebSocket) -> bool:
    client_ip = ws.client.host if ws.client else "unknown"
    allowed, _, _, _ = await _get_ws_limiter().allow(client_ip)
    if not allowed:
        logger.warning("ws_rate_limited", client_ip=client_ip)
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="rate limited")
        return False
    return True


async def _handle_message(ws: WebSocket, raw: object) -> None:
    if not isinstance(raw, dict) or raw.get("type") != "ping":
        await ws.send_json({"type": "error", "detail": "unsupported message type"})
        return
    await ws.send_json(
        {
            "type": "pong",
            "ts": raw.get("ts"),
            "server_time": datetime.now(UTC).isoformat(),
        }
    )


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    if not await _check_rate_limit(ws):
        return
    auth = get_security_service().authenticate_api_key(
        ws.query_params.get("api_key", "")
    )
    if not auth.authenticated:
        logger.warning("ws_auth_failed", reason=auth.reason)
        await ws.close(code=POLICY_CLOSE_CODE, reason="invalid api key")
        return
    metadata = connection_manager.connect(ws)
    if metadata is None:
        await ws.close(code=TRY_AGAIN_CLOSE_CODE, reason="max connections reached")
        return
    client_id = metadata["client_id"]
    await ws.send_json(
        {"type": "lifecycle", "event": "connected", "client_id": client_id}
    )
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
                        "ts": time.time(),
                        "server_time": datetime.now(UTC).isoformat(),
                    }
                )
                if idle_pings >= MAX_IDLE_PINGS:
                    logger.info("ws_closed_inactive", client_id=client_id)
                    await ws.close(code=SHUTDOWN_CLOSE_CODE, reason="inactive")
                    return
                continue
            except WebSocketDisconnect:
                break
            idle_pings = 0
            await _handle_message(ws, raw)
    except Exception:
        logger.exception("ws_error", client_id=client_id)
    finally:
        try:
            await ws.send_json({"type": "lifecycle", "event": "disconnected"})
        except Exception:
            logger.debug("ws_lifecycle_send_failed", client_id=client_id)
        connection_manager.disconnect(ws)
