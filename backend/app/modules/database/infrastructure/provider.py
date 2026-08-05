"""Infraestrutura do módulo Database — provider do PostgreSQL."""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.db import create_engine
from app.modules.configuration.settings import Settings


class DatabaseProvider:
    """Fachada do banco: engine, ping e ciclo de vida."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def engine_url(self) -> str:
        return str(self._engine.url).split("@")[-1]

    async def connect(self) -> None:
        async with await asyncio.wait_for(self._engine.connect(), timeout=2) as conn:
            await conn.execute(text("SELECT 1"))

    async def ping(self) -> bool:
        try:
            await asyncio.wait_for(self.connect(), timeout=3)
        except Exception:
            return False
        return True

    async def close(self) -> None:
        await self._engine.dispose()


def create_provider(settings: Settings) -> DatabaseProvider:
    return DatabaseProvider(create_engine(settings.database_url))
