from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NEGAO_",
        extra="ignore",
    )

    app_name: str = "NEGÃO AI"
    env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    api_key: str = "negao-dev-api-key"
    database_url: str = "postgresql+asyncpg://negao:negao@localhost:5432/negao"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "negao-dev-secret-key"
    cors_origins: list[str] = ["*"]
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    metrics_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 5
    ws_max_connections: int = 100

    # --- Brain (Model Router / LLM) -------------------------------------------------
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    brain_chat_model: str = "nvidia/gpt-oss-120b"
    brain_fallback_model: str = "nvidia/llama-3.1-8b-instruct"
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

    # --- Conversation -----------------------------------------------------------------
    conversation_max_context_messages: int = 20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
