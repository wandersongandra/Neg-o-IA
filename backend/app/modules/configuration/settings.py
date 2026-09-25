from __future__ import annotations

import logging
import os
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_SECRETS = {"", "negao-dev-api-key", "negao-dev-secret-key"}
_MIN_PRODUCTION_SECRET_LENGTH = 32
_ALLOWED_SERVICE_SCOPES = frozenset({"database:admin", "metrics:read"})
_PLACEHOLDER_MARKERS = ("change_me", "changeme", "troque", "substitua", "example", "exemplo")


def _looks_like_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return any(marker in normalized for marker in _PLACEHOLDER_MARKERS)


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
    service_api_scopes: list[str] = ["database:admin", "metrics:read"]
    service_bootstrap_enabled: bool = False
    service_api_key_default_ttl_days: int = 90
    service_api_key_max_ttl_days: int = 365
    database_url: str = "postgresql+asyncpg://negao:negao@localhost:5432/negao"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "negao-dev-secret-key"
    audit_integrity_key: str = ""
    audit_integrity_previous_keys: list[str] = []
    cors_origins: list[str] = ["*"]
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    metrics_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 5
    ws_max_connections: int = 100
    auth_session_ttl_seconds: int = 8 * 60 * 60
    auth_session_idle_seconds: int = 30 * 60
    auth_max_active_sessions: int = 5
    trusted_hosts: list[str] = []
    registration_enabled: bool = False

    external_ai_enabled: bool = False
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    brain_chat_model: str = "deepseek-ai/deepseek-v4-flash"
    brain_fallback_model: str = "meta/llama-3.1-8b-instruct"
    brain_stt_model: str = "nvidia/parakeet-tdt-0.6b-v2"
    brain_vision_model: str = ""
    brain_temperature: float = 0.3
    brain_max_tokens: int = 1024
    brain_retry_attempts: int = 2
    brain_circuit_failures: int = 3
    brain_circuit_cooldown_seconds: int = 60
    brain_cache_ttl_seconds: int = 300

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

    vision_max_image_bytes: int = 8 * 1024 * 1024
    vision_timeout_seconds: float = 45.0
    vision_max_prompt_chars: int = 4000

    conversation_max_context_messages: int = 20
    memory_recall_limit: int = 5
    knowledge_recall_limit: int = 5
    retrieval_min_score: float = 0.12
    retrieval_context_max_chars: int = 6000

    planner_plan_ttl_seconds: int = 3600
    planner_max_steps: int = 5
    planner_max_replans: int = 2

    tool_max_concurrency: int = 8
    tool_timeout_seconds: float = 10.0
    tool_circuit_failures: int = 3
    tool_circuit_cooldown_seconds: float = 30.0

    @field_validator(
        "cors_origins",
        "service_api_scopes",
        "trusted_hosts",
        "audit_integrity_previous_keys",
        mode="before",
    )
    @classmethod
    def _split_csv_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _reject_insecure_production_config(self) -> Settings:
        if self.env != "production":
            return self
        problems: list[str] = []
        if self.service_bootstrap_enabled and (
            self.service_api_key in _INSECURE_DEFAULT_SECRETS
            or len(self.service_api_key) < _MIN_PRODUCTION_SECRET_LENGTH
            or _looks_like_placeholder(self.service_api_key)
        ):
            problems.append(
                "NEGAO_SERVICE_API_KEY deve ser definida com um valor forte "
                f"(>= {_MIN_PRODUCTION_SECRET_LENGTH} caracteres) quando "
                "NEGAO_SERVICE_BOOTSTRAP_ENABLED=true"
            )
        if (
            self.secret_key in _INSECURE_DEFAULT_SECRETS
            or len(self.secret_key) < _MIN_PRODUCTION_SECRET_LENGTH
            or _looks_like_placeholder(self.secret_key)
        ):
            problems.append(
                "NEGAO_SECRET_KEY deve ser definida com um valor forte "
                f"(>= {_MIN_PRODUCTION_SECRET_LENGTH} caracteres) em produção"
            )
        if self.audit_integrity_key and (
            len(self.audit_integrity_key) < _MIN_PRODUCTION_SECRET_LENGTH
            or _looks_like_placeholder(self.audit_integrity_key)
        ):
            problems.append(
                "NEGAO_AUDIT_INTEGRITY_KEY deve ter pelo menos "
                f"{_MIN_PRODUCTION_SECRET_LENGTH} caracteres quando definida"
            )
        invalid_previous_audit_keys = [
            key
            for key in self.audit_integrity_previous_keys
            if len(key) < _MIN_PRODUCTION_SECRET_LENGTH or _looks_like_placeholder(key)
        ]
        if invalid_previous_audit_keys:
            problems.append("NEGAO_AUDIT_INTEGRITY_PREVIOUS_KEYS contém chave inválida")
        if self.cors_origins == ["*"]:
            problems.append("NEGAO_CORS_ORIGINS não pode ser '*' em produção")
        invalid_origins = [
            origin
            for origin in self.cors_origins
            if urlparse(origin).scheme != "https" or not urlparse(origin).netloc
        ]
        if invalid_origins:
            problems.append("NEGAO_CORS_ORIGINS deve conter apenas origens HTTPS válidas")
        if self.registration_enabled:
            problems.append("NEGAO_REGISTRATION_ENABLED deve ser false em produção")
        if not 1 <= self.service_api_key_default_ttl_days <= self.service_api_key_max_ttl_days:
            problems.append(
                "NEGAO_SERVICE_API_KEY_DEFAULT_TTL_DAYS deve estar entre 1 e "
                "NEGAO_SERVICE_API_KEY_MAX_TTL_DAYS"
            )
        if not 1 <= self.service_api_key_max_ttl_days <= 3650:
            problems.append("NEGAO_SERVICE_API_KEY_MAX_TTL_DAYS deve estar entre 1 e 3650")
        if self.auth_session_idle_seconds <= 0:
            problems.append("NEGAO_AUTH_SESSION_IDLE_SECONDS deve ser maior que zero")
        if self.auth_session_idle_seconds > self.auth_session_ttl_seconds:
            problems.append(
                "NEGAO_AUTH_SESSION_IDLE_SECONDS não pode exceder NEGAO_AUTH_SESSION_TTL_SECONDS"
            )
        if not 1 <= self.auth_max_active_sessions <= 20:
            problems.append("NEGAO_AUTH_MAX_ACTIVE_SESSIONS deve estar entre 1 e 20")
        if "*" in self.trusted_hosts:
            problems.append("NEGAO_TRUSTED_HOSTS não pode conter '*' em produção")
        if self.debug:
            problems.append("NEGAO_DEBUG deve ser false em produção")
        if self.service_bootstrap_enabled and not self.service_api_scopes:
            problems.append(
                "NEGAO_SERVICE_API_SCOPES deve conter ao menos um escopo "
                "quando o bootstrap de serviço estiver habilitado"
            )
        unknown_scopes = sorted(set(self.service_api_scopes) - _ALLOWED_SERVICE_SCOPES)
        if unknown_scopes:
            problems.append(
                "NEGAO_SERVICE_API_SCOPES contém escopos desconhecidos: "
                + ", ".join(unknown_scopes)
            )
        database = urlparse(self.database_url)
        if (
            not database.username
            or not database.password
            or database.password == "negao"
            or len(database.password) < 16
            or _looks_like_placeholder(database.password)
        ):
            problems.append("NEGAO_DATABASE_URL deve usar credenciais fortes em produção")
        redis = urlparse(self.redis_url)
        if (
            not redis.password
            or len(redis.password) < 16
            or _looks_like_placeholder(redis.password)
        ):
            problems.append("NEGAO_REDIS_URL deve exigir autenticação forte em produção")
        if self.external_ai_enabled:
            if not self.nvidia_api_key or _looks_like_placeholder(self.nvidia_api_key):
                problems.append(
                    "NEGAO_NVIDIA_API_KEY deve ser definida quando IA externa estiver ativa"
                )
            provider = urlparse(self.nvidia_base_url)
            if provider.scheme != "https":
                problems.append(
                    "NEGAO_NVIDIA_BASE_URL deve usar HTTPS quando IA externa estiver ativa"
                )
        credential_values = [
            self.secret_key,
            database.password or "",
            redis.password or "",
        ]
        if self.service_bootstrap_enabled:
            credential_values.append(self.service_api_key)
        nonempty_credentials = [value for value in credential_values if value]
        if len(set(nonempty_credentials)) != len(nonempty_credentials):
            problems.append("credenciais críticas de produção devem usar valores distintos")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def effective_audit_integrity_keys(self) -> list[str]:
        primary = self.audit_integrity_key or self.secret_key
        return [primary, *self.audit_integrity_previous_keys]

    def effective_trusted_hosts(self) -> list[str]:
        if self.env != "production":
            return ["*"]
        if self.trusted_hosts:
            return self.trusted_hosts
        hosts: list[str] = ["localhost", "127.0.0.1", "backend"]
        for origin in self.cors_origins:
            hostname = urlparse(origin).hostname
            if hostname and hostname not in hosts:
                hosts.append(hostname)
        return hosts


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
