"""Acesso ao Redis — cache, memória de curto prazo e streams."""

from __future__ import annotations

import asyncio
from functools import lru_cache

import redis.asyncio as aioredis

from app.modules.configuration.settings import get_settings


@lru_cache
def get_redis_client(redis_url: str) -> aioredis.Redis[str]:
    """Cria (e cacheia por URL) o cliente async do Redis."""
    return aioredis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=2.0,
    )


def get_redis() -> aioredis.Redis[str]:
    """Singleton lazy para consumo direto nos módulos."""
    return get_redis_client(get_settings().redis_url)


async def check_redis_health(client: aioredis.Redis[str] | None = None) -> bool:
    """Verifica conectividade com `PING` (timeout de 1,5s)."""
    redis_client = client or get_redis()
    try:
        pong = await asyncio.wait_for(redis_client.ping(), timeout=1.5)
    except Exception:
        return False
    return pong is True
