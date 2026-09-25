"""Testes unitários da validação de Settings em produção."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.configuration.settings import Settings, _secret_file_overrides


def test_default_settings_ok_fora_de_producao() -> None:
    settings = Settings(env="development")
    assert settings.service_api_key == ""
    assert not hasattr(settings, "api_key")


def test_producao_aceita_bootstrap_desabilitado_sem_service_key() -> None:
    settings = Settings(
        env="production",
        secret_key="s" * 32,
        internal_proxy_key="p" * 32,
        cors_origins=["https://sophie.example.com"],
        database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
        redis_url="redis://:strong-redis-password@redis:6379/0",
    )
    assert settings.service_bootstrap_enabled is False


def test_producao_rejeita_service_key_ausente_quando_bootstrap_ativo() -> None:
    with pytest.raises(ValidationError, match="NEGAO_SERVICE_API_KEY"):
        Settings(
            env="production",
            service_bootstrap_enabled=True,
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
            service_bootstrap_enabled=True,
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
        "service_api_key": "",
        "service_bootstrap_enabled": False,
        "secret_key": "s" * 32,
        "internal_proxy_key": "p" * 32,
        "cors_origins": ["https://sophie.example.com"],
        "database_url": "postgresql+asyncpg://sophie:database-password-strong@db:5432/sophie",
        "redis_url": "redis://:redis-password-strong@redis:6379/0",
    }


def test_producao_rejeita_placeholder_de_secret() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["secret_key"] = "substitua-por-chave-aleatoria-de-32-bytes"
    with pytest.raises(ValidationError, match="NEGAO_SECRET_KEY"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_senha_curta_do_banco() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["database_url"] = "postgresql+asyncpg://sophie:curta@db:5432/sophie"
    with pytest.raises(ValidationError, match="NEGAO_DATABASE_URL"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_senha_curta_do_redis() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["redis_url"] = "redis://:curta@redis:6379/0"
    with pytest.raises(ValidationError, match="NEGAO_REDIS_URL"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_cors_http() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["cors_origins"] = ["http://sophie.example.com"]
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_reuso_de_credencial() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["service_bootstrap_enabled"] = True
    kwargs["service_api_key"] = "k" * 32
    kwargs["secret_key"] = kwargs["service_api_key"]
    with pytest.raises(ValidationError, match="valores distintos"):
        Settings.model_validate(kwargs)


def test_ia_externa_exige_chave_do_provedor() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["external_ai_enabled"] = True
    kwargs["nvidia_api_key"] = ""
    with pytest.raises(ValidationError, match="NEGAO_NVIDIA_API_KEY"):
        Settings.model_validate(kwargs)


def test_producao_aceita_configuracao_forte() -> None:
    settings = Settings(
        env="production",
        service_api_key="",
        service_bootstrap_enabled=False,
        secret_key="s" * 32,
        internal_proxy_key="p" * 32,
        cors_origins=["https://sophie.example.com"],
        database_url="postgresql+asyncpg://sophie:strong-db-password@db:5432/sophie",
        redis_url="redis://:strong-redis-password@redis:6379/0",
    )
    assert settings.env == "production"


def test_producao_rejeita_idle_timeout_maior_que_ttl() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["auth_session_ttl_seconds"] = 600
    kwargs["auth_session_idle_seconds"] = 601
    with pytest.raises(ValidationError, match="AUTH_SESSION_IDLE_SECONDS"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_limite_de_sessoes_invalido() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["auth_max_active_sessions"] = 0
    with pytest.raises(ValidationError, match="AUTH_MAX_ACTIVE_SESSIONS"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_trusted_hosts_wildcard() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["trusted_hosts"] = ["*"]
    with pytest.raises(ValidationError, match="TRUSTED_HOSTS"):
        Settings.model_validate(kwargs)


def test_trusted_hosts_derivados_de_cors_em_producao() -> None:
    settings = Settings.model_validate(_strong_production_kwargs())
    assert settings.effective_trusted_hosts() == [
        "localhost",
        "127.0.0.1",
        "backend",
        "sophie.example.com",
    ]


def test_producao_rejeita_audit_integrity_key_fraca() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["audit_integrity_key"] = "fraca"
    with pytest.raises(ValidationError, match="AUDIT_INTEGRITY_KEY"):
        Settings.model_validate(kwargs)


def test_audit_integrity_keyring_preserva_chaves_anteriores() -> None:
    settings = Settings(
        secret_key="s" * 40,
        audit_integrity_key="n" * 40,
        audit_integrity_previous_keys=["o" * 40],
    )
    assert settings.effective_audit_integrity_keys() == ["n" * 40, "o" * 40]


def test_producao_rejeita_internal_proxy_key_fraca() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["internal_proxy_key"] = "fraca"
    with pytest.raises(ValidationError, match="INTERNAL_PROXY_KEY"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_reuso_da_internal_proxy_key() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["internal_proxy_key"] = kwargs["secret_key"]
    with pytest.raises(ValidationError, match="valores distintos"):
        Settings.model_validate(kwargs)


def test_producao_rejeita_touch_interval_maior_que_idle() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["auth_session_idle_seconds"] = 120
    kwargs["auth_session_touch_interval_seconds"] = 121
    with pytest.raises(ValidationError, match="AUTH_SESSION_TOUCH_INTERVAL_SECONDS"):
        Settings.model_validate(kwargs)


def test_secret_file_override_reads_absolute_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "secret-key"
    secret_path.write_text("s" * 40 + "\n", encoding="utf-8")
    monkeypatch.setenv("SOPHIE_SECRET_KEY_FILE", str(secret_path))
    monkeypatch.delenv("SOPHIE_SECRET_KEY", raising=False)
    monkeypatch.delenv("NEGAO_SECRET_KEY", raising=False)

    overrides = _secret_file_overrides()

    assert overrides["secret_key"] == "s" * 40


def test_secret_file_override_rejects_direct_value_and_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "secret-key"
    secret_path.write_text("s" * 40, encoding="utf-8")
    monkeypatch.setenv("SOPHIE_SECRET_KEY_FILE", str(secret_path))
    monkeypatch.setenv("SOPHIE_SECRET_KEY", "x" * 40)

    with pytest.raises(RuntimeError, match="não defina valor direto"):
        _secret_file_overrides()


def test_secret_file_override_rejects_relative_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOPHIE_SECRET_KEY_FILE", "relative/secret")

    with pytest.raises(RuntimeError, match="caminho absoluto"):
        _secret_file_overrides()


def test_external_ai_rejects_provider_outside_allowlist() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["external_ai_enabled"] = True
    kwargs["nvidia_api_key"] = "n" * 40
    kwargs["nvidia_base_url"] = "https://evil.example.net/v1"

    with pytest.raises(ValidationError, match="EXTERNAL_AI_ALLOWED_HOSTS"):
        Settings.model_validate(kwargs)


def test_external_ai_accepts_explicit_allowlisted_provider() -> None:
    kwargs = _strong_production_kwargs()
    kwargs["external_ai_enabled"] = True
    kwargs["nvidia_api_key"] = "n" * 40
    kwargs["nvidia_base_url"] = "https://provider.example.net/v1"
    kwargs["external_ai_allowed_hosts"] = ["provider.example.net"]

    settings = Settings.model_validate(kwargs)

    assert settings.nvidia_base_url == "https://provider.example.net/v1"
