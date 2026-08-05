"""Testes unitários do módulo security (InMemorySecurityService)."""

from __future__ import annotations

from app.modules.configuration.settings import Settings
from app.modules.security.domain import AuthorizationLevel
from app.modules.security.infrastructure import (
    InMemorySecurityService,
    create_security_service,
    get_security_service,
)


def test_authenticate_api_key_valida() -> None:
    service = InMemorySecurityService(expected_api_key="test-key")
    result = service.authenticate_api_key("test-key")
    assert result.authenticated is True
    assert result.authorization_level is AuthorizationLevel.READ_ONLY
    assert result.principal == "api_key"


def test_authenticate_api_key_errada() -> None:
    service = InMemorySecurityService(expected_api_key="test-key")
    result = service.authenticate_api_key("chave-errada")
    assert result.authenticated is False
    assert result.reason == "invalid_api_key"


def test_authenticate_api_key_vazia() -> None:
    service = InMemorySecurityService(expected_api_key="test-key")
    result = service.authenticate_api_key("")
    assert result.authenticated is False
    assert result.reason == "missing_api_key"


def test_create_security_service_funcional() -> None:
    service = create_security_service(Settings(api_key="test-key"))
    assert service.authenticate_api_key("test-key").authenticated is True
    assert service.authenticate_api_key("outra").authenticated is False


def test_get_security_service_retorna_mesma_instancia(monkeypatch_env: None) -> None:
    first = get_security_service()
    second = get_security_service()
    assert first is second
