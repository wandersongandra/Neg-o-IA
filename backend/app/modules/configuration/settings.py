from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_SECRETS = {"", "negao-dev-api-key", "negao-dev-secret-key"}
_MIN_PRODUCTION_SECRET_LENGTH = 32

_LEGACY_ENV_PREFIX = "NEGAO_"
_NEW_ENV_PREFIX = "SOPHIE_"
_config_logger = logging.getLogger("sophie.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NEGAO_",
        extra="ignore",
    )

    app_name: str = "Sophie AI"
    env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    # API keys legadas (`NEGAO_API_KEY`) não fazem parte da autoridade de
    # autenticação. Credenciais de serviço precisam ser explícitas.
    service_api_key: str = ""
    database_url: str = "postgresql+asyncpg://negao:negao@localhost:5432/negao"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "negao-dev-secret-key"
    cors_origins: list[str] = ["*"]
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    metrics_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 5
    ws_max_connections: int = 100
    auth_session_ttl_seconds: int = 8 * 60 * 60
    registration_enabled: bool = False

    # --- Brain (Model Router / LLM) -------------------------------------------------
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    brain_chat_model: str = "deepseek-ai/deepseek-v4-flash"
    brain_fallback_model: str = "meta/llama-3.1-8b-instruct"
    brain_stt_model: str = "nvidia/parakeet-tdt-0.6b-v2"
    brain_temperature: float = 0.3
    brain_max_tokens: int = 1024
    brain_retry_attempts: int = 2
    brain_circuit_failures: int = 3
    brain_circuit_cooldown_seconds: int = 60
    brain_cache_ttl_seconds: int = 300

    # --- Voice (STT/TTS) -------------------------------------------------------------
    tts_voice: str = "pt-BR-FranciscaNeural"
    tts_rate: str = "+0%"
    voice_max_chunk_bytes: int = 256 * 1024
    voice_max_turn_bytes: int = 10 * 1024 * 1024
    voice_max_turn_seconds: float = 30.0
    voice_idle_timeout_seconds: float = 60.0
    voice_session_max_seconds: float = 1800.0
    voice_max_concurrent_sessions: int = 20
    voice_stt_timeout_seconds: float = 30.0
    voice_tts_timeout_seconds: float = 30.0
    voice_conversation_timeout_seconds: float = 60.0

    # --- Conversation -----------------------------------------------------------------
    conversation_max_context_messages: int = 20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _reject_insecure_production_config(self) -> Settings:
        if self.env != "production":
            return self
        problems: list[str] = []
        if (
            self.service_api_key in _INSECURE_DEFAULT_SECRETS
            or len(self.service_api_key) < _MIN_PRODUCTION_SECRET_LENGTH
        ):
            problems.append(
                "NEGAO_SERVICE_API_KEY deve ser definida com um valor forte "
                f"(>= {_MIN_PRODUCTION_SECRET_LENGTH} caracteres) em produção"
            )
        if (
            self.secret_key in _INSECURE_DEFAULT_SECRETS
            or len(self.secret_key) < _MIN_PRODUCTION_SECRET_LENGTH
        ):
            problems.append(
                "NEGAO_SECRET_KEY deve ser definida com um valor forte "
                f"(>= {_MIN_PRODUCTION_SECRET_LENGTH} caracteres) em produção"
            )
        if self.cors_origins == ["*"]:
            problems.append("NEGAO_CORS_ORIGINS não pode ser '*' em produção")
        if self.registration_enabled:
            problems.append("NEGAO_REGISTRATION_ENABLED deve ser false em produção")
        if problems:
            raise ValueError("; ".join(problems))
        return self


def _apply_legacy_env_aliases() -> None:
    """Migração NEGAO_* → SOPHIE_*: SOPHIE_<CAMPO> tem precedência; se ausente,
    o valor de NEGAO_<CAMPO> (comportamento atual) é preservado sem mudanças.
    Nunca loga valores — só os nomes das variáveis, e só fora de produção."""
    legacy_in_use: list[str] = []
    for field_name in Settings.model_fields:
        suffix = field_name.upper()
        new_var = f"{_NEW_ENV_PREFIX}{suffix}"
        legacy_var = f"{_LEGACY_ENV_PREFIX}{suffix}"
        if new_var in os.environ:
            # SOPHIE_* sempre vence — sobrescreve mesmo se NEGAO_* também
            # estiver definida, para que a precedência declarada seja real.
            os.environ[legacy_var] = os.environ[new_var]
        elif legacy_var in os.environ:
            legacy_in_use.append(legacy_var)
    is_production = (
        os.environ.get(f"{_NEW_ENV_PREFIX}ENV")
        or os.environ.get(f"{_LEGACY_ENV_PREFIX}ENV")
        or "development"
    ) == "production"
    if legacy_in_use and not is_production:
        _config_logger.warning(
            "Variáveis de ambiente legadas em uso (%s); considere migrar para "
            "os equivalentes SOPHIE_*.",
            ", ".join(sorted(legacy_in_use)),
        )


@lru_cache
def get_settings() -> Settings:
    _apply_legacy_env_aliases()
    return Settings()
