"""Contratos de liveness/readiness sem depender de serviços externos."""

from __future__ import annotations

from typing import Any

from app.modules.api import router as api_router_module
from app.modules.api.router import readyz


async def test_readiness_returns_200_only_when_critical_dependencies_are_ready(
    monkeypatch: Any,
) -> None:
    async def healthy() -> bool:
        return True

    monkeypatch.setattr(api_router_module, "check_database_health", healthy)
    monkeypatch.setattr(api_router_module, "check_redis_health", healthy)

    response = await readyz()

    assert response.status_code == 200
    assert response.body == b'{"status":"ready","checks":{"database":"ok","redis":"ok"}}'


async def test_readiness_returns_503_when_a_critical_dependency_is_down(
    monkeypatch: Any,
) -> None:
    async def unavailable() -> bool:
        return False

    monkeypatch.setattr(api_router_module, "check_database_health", unavailable)
    monkeypatch.setattr(api_router_module, "check_redis_health", unavailable)

    response = await readyz()

    assert response.status_code == 503
    assert response.body == (
        b'{"status":"not_ready","checks":{"database":"degraded","redis":"degraded"}}'
    )
