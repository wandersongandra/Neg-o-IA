"""Acesso a dados — PostgreSQL (SQLAlchemy async + asyncpg)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.modules.configuration.settings import get_settings


@lru_cache
def create_engine(database_url: str) -> AsyncEngine:
    """Cria (e cacheia por URL) o engine async do PostgreSQL."""
    settings = get_settings()
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.debug,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependência FastAPI: sessão async com commit/rollback automáticos."""
    factory = create_session_factory(create_engine(get_settings().database_url))
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> bool:
    """Verifica conectividade com `SELECT 1` (timeout de 1,5s)."""
    engine = create_engine(get_settings().database_url)
    try:
        async with await asyncio.wait_for(engine.connect(), timeout=1.5) as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
