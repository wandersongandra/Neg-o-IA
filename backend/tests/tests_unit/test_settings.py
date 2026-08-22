"""Testes unitários da validação de Settings em produção."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.configuration.settings import Settings


def test_default_settings_ok_fora_de_producao() -> None:
    settings = Settings(env="development")
    assert settings.service_api_key == ""
    assert not hasattr(settings, "api_key")


def test_producao_rejeita_service_key_ausente() -> None:
    with pytest.raises(ValidationError, match="NEGAO_SERVICE_API_KEY"):
        Settings(
            env="production",
            secret_key="s" * 32,
            cors_origins=["https://sophie.example.com"],
        )


def test_producao_rejeita_secret_key_padrao() -> None:
    with pytest.raises(ValidationError, match="NEGAO_SECRET_KEY"):
        Settings(
            env="production",
            service_api_key="k" * 32,
            cors_origins=["https://sophie.example.com"],
        )


def test_producao_rejeita_service_key_curta() -> None:
    with pytest.raises(ValidationError, match="NEGAO_SERVICE_API_KEY"):
        Settings(
            env="production",
            service_api_key="curta",
            secret_key="s" * 32,
            cors_origins=["https://sophie.example.com"],
        )


def test_producao_rejeita_cors_wildcard() -> None:
    with pytest.raises(ValidationError, match="NEGAO_CORS_ORIGINS"):
        Settings(
            env="production",
            service_api_key="k" * 32,
            secret_key="s" * 32,
            cors_origins=["*"],
        )


def test_producao_aceita_configuracao_forte() -> None:
    settings = Settings(
        env="production",
        service_api_key="k" * 32,
        secret_key="s" * 32,
        cors_origins=["https://sophie.example.com"],
    )
    assert settings.env == "production"
