"""Implementação da memória de curto prazo (v0) sobre Redis.

Chaves `stm:{session_id}:{key}` com TTL; o valor armazena um documento
JSON com `value`, `ttl_seconds`, `created_at` e `expires_at`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis

from app.modules.memory.domain import ShortTermMemoryEntry

DEFAULT_TTL_SECONDS = 86_400
KEY_PREFIX = "stm"


def _parse_iso(value: str | None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(UTC)


class RedisShortTermMemory:
    """Adaptador STM sobre Redis (memória de trabalho por sessão)."""

    def __init__(self, redis_client: aioredis.Redis[str], *, key_prefix: str = KEY_PREFIX) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix

    def _key(self, session_id: str, key: str) -> str:
        return f"{self._key_prefix}:{session_id}:{key}"

    async def set(
        self, session_id: str, key: str, value: Any, *, ttl: int = DEFAULT_TTL_SECONDS
    ) -> ShortTermMemoryEntry:
        now = datetime.now(UTC)
        doc = {
            "value": value,
            "ttl_seconds": ttl,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
        }
        await self._redis.set(
            self._key(session_id, key), json.dumps(doc, ensure_ascii=False, default=str), ex=ttl
        )
        return ShortTermMemoryEntry(
            session_id=session_id,
            key=key,
            value=value,
            ttl_seconds=ttl,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )

    async def get(self, session_id: str, key: str) -> ShortTermMemoryEntry | None:
        raw = await self._redis.get(self._key(session_id, key))
        if raw is None:
            return None
        doc = json.loads(raw)
        return ShortTermMemoryEntry(
            session_id=session_id,
            key=key,
            value=doc.get("value"),
            ttl_seconds=int(doc.get("ttl_seconds", DEFAULT_TTL_SECONDS)),
            created_at=_parse_iso(doc.get("created_at")),
            expires_at=_parse_iso(doc.get("expires_at")),
        )

    async def delete(self, session_id: str, key: str) -> bool:
        removed = await self._redis.delete(self._key(session_id, key))
        return removed > 0

    async def list_keys(self, session_id: str) -> list[str]:
        prefix = f"{self._key_prefix}:{session_id}:"
        keys: list[str] = []
        async for raw_key in self._redis.scan_iter(match=f"{prefix}*", count=100):
            key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
            if key.startswith(prefix):
                keys.append(key[len(prefix) :])
        return keys

    async def flush_session(self, session_id: str) -> int:
        prefix = f"{self._key_prefix}:{session_id}:"
        keys: list[str] = []
        async for raw_key in self._redis.scan_iter(match=f"{prefix}*", count=100):
            key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
            if key.startswith(prefix):
                keys.append(key)
        if not keys:
            return 0
        return await self._redis.delete(*keys)
