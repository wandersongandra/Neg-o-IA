"""Camada de aplicação do módulo memory — MemoryService."""

from __future__ import annotations

import logging
from typing import Any

from app.modules.events.envelope import build_envelope
from app.modules.memory.domain import ShortTermMemoryEntry
from app.modules.memory.events import EVENT_MEMORY_READ_COMPLETED, EVENT_MEMORY_WRITTEN
from app.modules.memory.infrastructure import DEFAULT_TTL_SECONDS, RedisShortTermMemory

_LOGGER = logging.getLogger("app.modules.memory.application")
PRODUCER = "memory"
_memory_service: MemoryService | None = None


class MemoryService:
    """Facade da memória de curto prazo, sempre isolada por usuário."""

    def __init__(self, store: RedisShortTermMemory) -> None:
        self._store = store

    async def record_session_data(
        self,
        user_id: str,
        session_id: str,
        key: str,
        value: Any,
        *,
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> ShortTermMemoryEntry:
        entry = await self._store.set(user_id, session_id, key, value, ttl=ttl)
        await self._publish(
            EVENT_MEMORY_WRITTEN,
            {
                "user_id": user_id,
                "session_id": session_id,
                "key": key,
                "ttl_seconds": ttl,
            },
        )
        return entry

    async def recall_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        keys = await self._store.list_keys(user_id, session_id)
        result: dict[str, Any] = {}
        for key in keys:
            entry = await self._store.get(user_id, session_id, key)
            if entry is not None:
                result[key] = entry.value
        await self._publish(
            EVENT_MEMORY_READ_COMPLETED,
            {"user_id": user_id, "session_id": session_id, "entries": len(result)},
        )
        return result

    async def flush_session(self, user_id: str, session_id: str) -> int:
        return await self._store.flush_session(user_id, session_id)

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    payload,
                    user_id=payload.get("user_id"),
                    session_id=payload.get("session_id"),
                )
            )
        except Exception as exc:
            _LOGGER.warning(
                "falha ao publicar evento de memória",
                extra={"event_type": event_type, "error": str(exc)},
            )


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        from app.infrastructure.redis import get_redis

        _memory_service = MemoryService(RedisShortTermMemory(redis_client=get_redis()))
    return _memory_service
