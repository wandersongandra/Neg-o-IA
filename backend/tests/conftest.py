"""Fixtures compartilhadas dos testes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def fake_session() -> AsyncMock:
    """Sessão async mockada com execute/flush/commit/rollback AsyncMock."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
async def app_client() -> AsyncIterator[AsyncClient]:
    """App FastAPI mínimo para testes de contrato dos routers."""

    application = FastAPI()

    @application.get("/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def monkeypatch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEGAO_ENV", "test")
    monkeypatch.setenv("NEGAO_API_KEY", "test-api-key")
