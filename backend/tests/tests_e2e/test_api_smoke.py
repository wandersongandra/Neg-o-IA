"""Smoke tests da aplicação real (ASGITransport + lifespan manual).

Não dependem de Postgres/Redis reais: apenas rotas que não tocam infra.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import create_app

API_KEY = "negao-dev-api-key"


@pytest.fixture
async def smoke_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("NEGAO_API_KEY", API_KEY)
    monkeypatch.setenv("NEGAO_OTEL_EXPORTER_OTLP_ENDPOINT", "")

    from app.modules.configuration.settings import get_settings
    from app.modules.security.infrastructure import get_security_service

    get_settings.cache_clear()
    get_security_service.cache_clear()

    application = create_app()
    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_root_retorna_nome(smoke_client: httpx.AsyncClient) -> None:
    response = await smoke_client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert body["name"]


@pytest.mark.asyncio
async def test_healthz_vivo(smoke_client: httpx.AsyncClient) -> None:
    response = await smoke_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_security_status_com_chave(smoke_client: httpx.AsyncClient) -> None:
    response = await smoke_client.get(
        "/security/status", headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is True


@pytest.mark.asyncio
async def test_security_status_sem_chave_retorna_401(
    smoke_client: httpx.AsyncClient,
) -> None:
    response = await smoke_client.get("/security/status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_openapi_disponivel(smoke_client: httpx.AsyncClient) -> None:
    response = await smoke_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
