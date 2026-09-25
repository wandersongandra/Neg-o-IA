"""Testes unitários da seleção de chave do rate limiter (main._rate_limit_key)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from starlette.requests import Request

from app.main import _rate_limit_key
from app.modules.api.rate_limit import RateLimiter, trusted_client_ip
from app.modules.security.domain import AuthResult

API_KEY = "test-rate-limit-key"


def _make_request(headers: dict[str, str], client_host: str = "1.2.3.4") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope: dict[str, Any] = {
        "type": "http",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _configured_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("NEGAO_API_KEY", API_KEY)
    from app.modules.configuration.settings import get_settings
    from app.modules.security.infrastructure import get_security_service

    get_settings.cache_clear()
    get_security_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_security_service.cache_clear()


def test_chave_nao_autenticada_ainda_usa_ip() -> None:
    """O middleware roda antes do dependency injection de autenticação."""
    request = _make_request({"x-api-key": API_KEY})
    assert _rate_limit_key(request) == "1.2.3.4"


def test_identidade_autenticada_usa_bucket_do_usuario() -> None:
    request = _make_request({})
    request.state.auth_result = AuthResult(
        authenticated=True,
        principal="user-123",
        user_id="user-123",
        auth_method="session",
    )
    assert _rate_limit_key(request) == "principal:user-123"


def test_chave_invalida_nao_ganha_bucket_proprio() -> None:
    """Uma X-API-Key forjada/aleatória não deve gerar uma chave nova por
    requisição — deve cair no mesmo fallback de IP que uma requisição sem
    nenhuma chave, senão um atacante ganharia um bucket infinito girando
    o header."""
    request = _make_request({"x-api-key": "chave-forjada-aleatoria"})
    assert _rate_limit_key(request) == "1.2.3.4"


def test_sem_chave_cai_para_ip() -> None:
    request = _make_request({})
    assert _rate_limit_key(request) == "1.2.3.4"


def test_chave_invalida_e_sem_chave_colidem_no_mesmo_bucket() -> None:
    forged = _make_request({"x-api-key": "outra-chave-forjada"})
    missing = _make_request({})
    assert _rate_limit_key(forged) == _rate_limit_key(missing)


class _BrokenRedis:
    async def ping(self) -> bool:
        raise ConnectionError("redis unavailable")


@pytest.mark.asyncio
async def test_rate_limiter_fail_closed_denies_when_redis_is_unavailable() -> None:
    limiter = RateLimiter(
        limit=5,
        redis_client=_BrokenRedis(),  # type: ignore[arg-type]
        fail_closed=True,
    )
    allowed, limit, remaining, retry_after = await limiter.allow("login:user")

    assert allowed is False
    assert limit == 5
    assert remaining == 0
    assert retry_after > 0


def test_forwarded_ip_requires_internal_proxy_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEGAO_INTERNAL_PROXY_KEY", "p" * 32)
    from app.modules.configuration.settings import get_settings

    get_settings.cache_clear()
    request = _make_request(
        {
            "x-real-ip": "203.0.113.25",
            "x-sophie-internal-proxy": "wrong-key",
        },
        client_host="10.0.0.5",
    )
    assert trusted_client_ip(request) == "10.0.0.5"
    get_settings.cache_clear()


def test_forwarded_ip_accepted_with_internal_proxy_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proxy_key = "p" * 32
    monkeypatch.setenv("NEGAO_INTERNAL_PROXY_KEY", proxy_key)
    from app.modules.configuration.settings import get_settings

    get_settings.cache_clear()
    request = _make_request(
        {
            "x-real-ip": "203.0.113.25",
            "x-sophie-internal-proxy": proxy_key,
        },
        client_host="10.0.0.5",
    )
    assert trusted_client_ip(request) == "203.0.113.25"
    get_settings.cache_clear()


def test_forwarded_ip_rejects_invalid_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    proxy_key = "p" * 32
    monkeypatch.setenv("NEGAO_INTERNAL_PROXY_KEY", proxy_key)
    from app.modules.configuration.settings import get_settings

    get_settings.cache_clear()
    request = _make_request(
        {
            "x-real-ip": "not-an-ip",
            "x-sophie-internal-proxy": proxy_key,
        },
        client_host="10.0.0.5",
    )
    assert trusted_client_ip(request) == "10.0.0.5"
    get_settings.cache_clear()
