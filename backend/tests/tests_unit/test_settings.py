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
            database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
            redis_url="redis://:strong-redis-password@redis:6379/0",
        )


def test_producao_rejeita_secret_key_padrao() -> None:
    with pytest.raises(ValidationError, match="NEGAO_SECRET_KEY"):
        Settings(
            env="production",
            service_api_key="k" * 32,
            cors_origins=["https://sophie.example.com"],
            database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
            redis_url="redis://:strong-redis-password@redis:6379/0",
        )


def test_producao_rejeita_service_key_curta() -> None:
    with pytest.raises(ValidationError, match="NEGAO_SERVICE_API_KEY"):
        Settings(
            env="production",
            service_api_key="curta",
            secret_key="s" * 32,
            cors_origins=["https://sophie.example.com"],
            database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
            redis_url="redis://:strong-redis-password@redis:6379/0",
        )


def test_producao_rejeita_cors_wildcard() -> None:
    with pytest.raises(ValidationError, match="NEGAO_CORS_ORIGINS"):
        Settings(
            env="production",
            service_api_key="k" * 32,
            secret_key="s" * 32,
            cors_origins=["*"],
        )


def test_producao_rejeita_debug_ativo() -> None:
    with pytest.raises(ValidationError, match="NEGAO_DEBUG"):
        Settings(
            env="production",
            debug=True,
            service_api_key="k" * 32,
            secret_key="s" * 32,
            cors_origins=["https://sophie.example.com"],
            database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
            redis_url="redis://:strong-redis-password@redis:6379/0",
        )


def _strong_production_kwargs() -> dict[str, object]:
    return {
        "env": "production",
        "service_api_key": "k" * 32,
        "secret_key": "s" * 32,
        "cors_origins": ["https://sophie.example.com"],
        "database_url": "postgresql+asyncpg://sophie:database-password-strong@db:5432/sophie",
        "redis_url": "redis://:redis-password-strong@redis:6379/0",
    }


def test_producao_rejeita_placeholder_de_secret() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["secret_key"] = "substitua-por-chave-aleatoria-de-32-bytes"
    with pytest.raises(ValidationError, match="NEGAO_SECRET_KEY"):
        Settings(**kwargs)


def test_producao_rejeita_senha_curta_do_banco() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["database_url"] = "postgresql+asyncpg://sophie:curta@db:5432/sophie"
    with pytest.raises(ValidationError, match="NEGAO_DATABASE_URL"):
        Settings(**kwargs)


def test_producao_rejeita_senha_curta_do_redis() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["redis_url"] = "redis://:curta@redis:6379/0"
    with pytest.raises(ValidationError, match="NEGAO_REDIS_URL"):
        Settings(**kwargs)


def test_producao_rejeita_cors_http() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["cors_origins"] = ["http://sophie.example.com"]
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(**kwargs)


def test_producao_rejeita_reuso_de_credencial() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["secret_key"] = kwargs["service_api_key"]
    with pytest.raises(ValidationError, match="valores distintos"):
        Settings(**kwargs)


def test_ia_externa_exige_chave_do_provedor() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["external_ai_enabled"] = True
    kwargs["nvidia_api_key"] = ""
    with pytest.raises(ValidationError, match="NEGAO_NVIDIA_API_KEY"):
        Settings(**kwargs)


def test_producao_aceita_configuracao_forte() -> None:
    settings = Settings(
        env="production",
        service_api_key="k" * 32,
        secret_key="s" * 32,
        cors_origins=["https://sophie.example.com"],
        database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
        redis_url="redis://:strong-redis-password@redis:6379/0",
    )
    assert settings.env == "production"
