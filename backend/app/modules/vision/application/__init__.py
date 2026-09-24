"""Vision V1 — análise explícita de imagens enviadas pelo usuário."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.modules.configuration.settings import get_settings
from app.modules.events.envelope import build_envelope
from app.modules.vision.infrastructure import (
    OpenAICompatibleVisionAdapter,
    VisionUnavailableError,
)

_LOGGER = logging.getLogger("app.modules.vision.application")
_ALLOWED_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
_service: VisionService | None = None


class VisionService:
    def __init__(self, adapter: OpenAICompatibleVisionAdapter | None = None) -> None:
        self._adapter = adapter or OpenAICompatibleVisionAdapter()

    async def analyze(
        self,
        image_bytes: bytes,
        *,
        media_type: str,
        prompt: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        if media_type not in _ALLOWED_MEDIA_TYPES:
            raise ValueError("unsupported image media type")
        if not image_bytes:
            raise ValueError("image is empty")
        if len(image_bytes) > settings.vision_max_image_bytes:
            raise ValueError("image exceeds configured size limit")

        effective_prompt = (
            prompt or ""
        ).strip() or "Descreva objetivamente a imagem e destaque os elementos relevantes."
        if len(effective_prompt) > settings.vision_max_prompt_chars:
            raise ValueError("vision prompt exceeds configured size limit")

        result = await self._adapter.analyze(
            image_bytes,
            media_type=media_type,
            prompt=effective_prompt,
        )
        await self._publish(
            user_id,
            {
                "media_type": media_type,
                "bytes": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                "model": result.get("model"),
                "latency_ms": result.get("latency_ms"),
            },
        )
        return result

    async def status(self) -> dict[str, Any]:
        settings = get_settings()
        configured = bool(
            settings.vision_enabled
            and settings.external_ai_enabled
            and settings.nvidia_api_key
            and settings.vision_model.strip()
        )
        return {
            "enabled": settings.vision_enabled,
            "configured": configured,
            "model": settings.vision_model if configured else None,
            "allowed_media_types": sorted(_ALLOWED_MEDIA_TYPES),
            "max_image_bytes": settings.vision_max_image_bytes,
        }

    async def _publish(self, user_id: str | None, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    "vision.analysis.completed",
                    "vision",
                    payload,
                    user_id=user_id,
                )
            )
        except Exception:
            _LOGGER.warning("vision_event_publish_failed", exc_info=True)


def get_vision_service() -> VisionService:
    global _service
    if _service is None:
        _service = VisionService()
    return _service


__all__ = ["VisionService", "VisionUnavailableError", "get_vision_service"]
