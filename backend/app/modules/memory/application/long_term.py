"""Memória longa persistida em PostgreSQL/pgvector."""

from __future__ import annotations

import logging
from typing import Any

from app.modules.events.envelope import build_envelope
from app.modules.memory.domain import LongTermMemoryEntry, MemoryPolicy, MemorySearchHit
from app.modules.memory.infrastructure.long_term import PostgresLongTermMemory

_LOGGER = logging.getLogger("app.modules.memory.long_term")
PRODUCER = "memory"
_service: LongTermMemoryService | None = None


class LongTermMemoryService:
    def __init__(self, store: PostgresLongTermMemory | None = None) -> None:
        self._store = store or PostgresLongTermMemory()

    async def remember(
        self,
        user_id: str,
        content: str,
        *,
        session_id: str | None = None,
        source: str = "manual",
        importance: float = 0.5,
        retention_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermMemoryEntry:
        normalized = content.strip()
        if not normalized or len(normalized) > 4000:
            raise ValueError("memory content must contain 1..4000 characters")
        if not 0 <= importance <= 1:
            raise ValueError("memory importance must be between 0 and 1")
        entry = await self._store.remember(
            user_id,
            normalized,
            session_id=session_id,
            source=source,
            importance=importance,
            retention_days=retention_days,
            metadata=metadata or {},
        )
        await self._publish(
            "memory.long_term.written",
            {"user_id": user_id, "memory_id": entry.id, "source": source},
            session_id=session_id,
        )
        return entry

    async def search(self, user_id: str, query: str, *, limit: int = 5) -> list[MemorySearchHit]:
        normalized = query.strip()
        if not normalized:
            return []
        hits = await self._store.search(user_id, normalized, limit=max(1, min(limit, 10)))
        await self._publish(
            "memory.long_term.recalled",
            {"user_id": user_id, "hits": len(hits)},
        )
        return hits

    async def delete(self, user_id: str, memory_id: str) -> bool:
        removed = await self._store.delete(user_id, memory_id)
        if removed:
            await self._publish(
                "memory.long_term.deleted",
                {"user_id": user_id, "memory_id": memory_id},
            )
        return removed

    async def get_policy(self, user_id: str) -> MemoryPolicy:
        return await self._store.get_policy(user_id)

    async def update_policy(
        self,
        user_id: str,
        *,
        auto_capture_enabled: bool,
        retention_days: int,
    ) -> MemoryPolicy:
        if not 1 <= retention_days <= 3650:
            raise ValueError("retention_days must be between 1 and 3650")
        return await self._store.set_policy(
            user_id,
            auto_capture_enabled=auto_capture_enabled,
            retention_days=retention_days,
        )

    async def maybe_capture_conversation(
        self,
        user_id: str,
        session_id: str,
        content: str,
    ) -> LongTermMemoryEntry | None:
        policy = await self.get_policy(user_id)
        if not policy.auto_capture_enabled:
            return None
        normalized = content.strip()
        if len(normalized) < 20:
            return None
        return await self.remember(
            user_id,
            normalized,
            session_id=session_id,
            source="conversation",
            importance=0.35,
            retention_days=policy.retention_days,
            metadata={"capture": "automatic"},
        )

    async def build_context(self, user_id: str, query: str, *, limit: int = 5) -> str:
        hits = await self.search(user_id, query, limit=limit)
        if not hits:
            return ""
        lines = [
            f"- [{hit.entry.source}; score={hit.score:.2f}] {hit.entry.content}"
            for hit in hits
        ]
        return "\n".join(lines)

    async def _publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    payload,
                    user_id=payload.get("user_id"),
                    session_id=session_id,
                )
            )
        except Exception as exc:
            _LOGGER.warning(
                "long_term_memory_event_failed",
                extra={"event_type": event_type, "error": str(exc)},
            )


def get_long_term_memory_service() -> LongTermMemoryService:
    global _service
    if _service is None:
        _service = LongTermMemoryService()
    return _service
