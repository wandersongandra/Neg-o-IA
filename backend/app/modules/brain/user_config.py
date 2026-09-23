"""Configuração efetiva do Brain por usuário, persistida no Redis."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

from app.modules.brain.identity import SYSTEM_PROMPT
from app.modules.configuration.settings import get_settings

_LOGGER = logging.getLogger("app.modules.brain.user_config")
_KEY_PREFIX = "brain:user-config"
_TTL_SECONDS = 30 * 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class UserBrainConfig:
    system_prompt: str
    temperature: float
    max_tokens: int


def default_user_config() -> UserBrainConfig:
    settings = get_settings()
    return UserBrainConfig(
        system_prompt=SYSTEM_PROMPT,
        temperature=settings.brain_temperature,
        max_tokens=settings.brain_max_tokens,
    )


def _key(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return f"{_KEY_PREFIX}:{digest}"


def _validate_payload(payload: object) -> UserBrainConfig:
    defaults = default_user_config()
    if not isinstance(payload, dict):
        return defaults

    prompt = payload.get("system_prompt")
    temperature = payload.get("temperature")
    max_tokens = payload.get("max_tokens")

    if not isinstance(prompt, str) or not 10 <= len(prompt) <= 8000:
        prompt = defaults.system_prompt
    if not isinstance(temperature, int | float) or not 0.0 <= float(temperature) <= 2.0:
        temperature = defaults.temperature
    if not isinstance(max_tokens, int) or not 1 <= max_tokens <= 8192:
        max_tokens = defaults.max_tokens

    return UserBrainConfig(
        system_prompt=prompt,
        temperature=float(temperature),
        max_tokens=max_tokens,
    )


async def load_user_config(user_id: str | None) -> UserBrainConfig:
    if not user_id:
        return default_user_config()
    try:
        from app.infrastructure.redis import get_redis

        raw = await get_redis().get(_key(user_id))
        if not raw:
            return default_user_config()
        return _validate_payload(json.loads(raw))
    except Exception:
        _LOGGER.warning("user_brain_config_read_failed", exc_info=True)
        return default_user_config()


async def save_user_config(user_id: str, config: UserBrainConfig) -> None:
    from app.infrastructure.redis import get_redis

    payload = json.dumps(
        {
            "system_prompt": config.system_prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        },
        ensure_ascii=False,
    )
    await get_redis().set(_key(user_id), payload, ex=_TTL_SECONDS)


__all__ = [
    "UserBrainConfig",
    "default_user_config",
    "load_user_config",
    "save_user_config",
]
