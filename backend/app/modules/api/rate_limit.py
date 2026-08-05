"""Rate limiter de janela fixa com fallback em memória.

Backend primário: Redis (`INCR` + `EXPIRE` em `rl:{key}:{window}`).
Quando o Redis está indisponível, cai para um contador in-memory
protegido por lock (perde o estado se o processo reiniciar).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

_REDIS_RECHECK_SECONDS = 30.0
_REDIS_PING_TIMEOUT = 0.5
_DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    """Contador de janela fixa por chave (IP ou principal autenticado)."""

    def __init__(
        self,
        limit: int,
        *,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
        redis_client: aioredis.Redis[str] | None = None,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        if redis_client is None:
            from app.infrastructure.redis import get_redis

            redis_client = get_redis()
        self._redis = redis_client
        self._redis_available: bool | None = None
        self._last_redis_check = 0.0
        self._redis_check_lock = asyncio.Lock()
        self._counts: dict[str, int] = {}
        self._memory_lock = asyncio.Lock()

    def _key(self, key: str, window: int) -> str:
        return f"rl:{key}:{window}"

    def _retry_after(self, window: int) -> int:
        window_end = (window + 1) * self._window_seconds
        return max(1, int(window_end - time.time()) + 1)

    async def allow(self, key: str) -> tuple[bool, int, int, int]:
        """Retorna (permitido, limite, restantes, retry_after_seconds)."""
        window = int(time.time()) // self._window_seconds
        if await self._redis_alive():
            try:
                return await self._allow_redis(key, window)
            except Exception:
                self._redis_available = False
        return await self._allow_memory(key, window)

    async def _redis_alive(self) -> bool:
        if self._redis_available:
            return True
        now = time.monotonic()
        if now - self._last_redis_check < _REDIS_RECHECK_SECONDS:
            return False
        async with self._redis_check_lock:
            if now - self._last_redis_check >= _REDIS_RECHECK_SECONDS:
                try:
                    pong = await asyncio.wait_for(
                        self._redis.ping(), timeout=_REDIS_PING_TIMEOUT
                    )
                    self._redis_available = bool(pong)
                except Exception:
                    self._redis_available = False
                finally:
                    self._last_redis_check = time.monotonic()
        return bool(self._redis_available)

    async def _allow_redis(self, key: str, window: int) -> tuple[bool, int, int, int]:
        redis_key = self._key(key, window)
        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, self._window_seconds, nx=True)
        if count <= self._limit:
            return True, self._limit, self._limit - count, 0
        return False, self._limit, 0, self._retry_after(window)

    async def _allow_memory(self, key: str, window: int) -> tuple[bool, int, int, int]:
        memory_key = self._key(key, window)
        async with self._memory_lock:
            self._prune_memory(window)
            count = self._counts.get(memory_key, 0) + 1
            self._counts[memory_key] = count
        if count <= self._limit:
            return True, self._limit, self._limit - count, 0
        return False, self._limit, 0, self._retry_after(window)

    def _prune_memory(self, current_window: int) -> None:
        for memory_key in list(self._counts):
            window = int(memory_key.rsplit(":", 1)[1])
            if window < current_window:
                del self._counts[memory_key]


def _extract_key(request: Request) -> str:
    auth_result = getattr(request.state, "auth_result", None)
    principal = getattr(auth_result, "principal", None)
    if isinstance(principal, str) and principal:
        return principal
    return request.client.host if request.client else "unknown"


def make_rate_limit_dependency(limit: int) -> Callable[[Request], Awaitable[None]]:
    """Cria uma dependência FastAPI que aplica o limite informado por requisição."""
    limiter = RateLimiter(limit=limit)

    async def rate_limit_dependency(request: Request) -> None:
        allowed, limit_, remaining, retry_after = await limiter.allow(
            _extract_key(request)
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(limit_),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                    "Retry-After": str(retry_after),
                },
            )

    return rate_limit_dependency
