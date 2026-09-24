"""Casos de uso do módulo Vision."""

from __future__ import annotations

import logging
from typing import Any

from app.modules.configuration.settings import get_settings
from app.modules.events.envelope import build_envelope
from app.modules.vision.domain import VisionAnalysis, VisionPort
from app.modules.vision.infrastructure import NvidiaVisionAdapter, detect_image_mime

_LOGGER = logging.getLogger("app.modules.vision.application")
PRODUCER = "vision"
_service: VisionService | None = None


class VisionUnavailableError(RuntimeError):
    pass


class VisionService:
    def __init__(self, adapter: VisionPort | None = None) -> None:
        self._adapter = adapter or NvidiaVisionAdapter()

    def status(self) -> dict[str, Any]:
        settings = get_settings()
        available = bool(
            settings.external_ai_enabled
            and settings.nvidia_api_key
            and settings.brain_vision_model
        )
        return {
            "available": available,
            "model": settings.brain_vision_model or None,
            "max_image_bytes": settings.vision_max_image_bytes,
            "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
            "external_processing": available,
        }

    async def analyze(
        self,
        image_bytes: bytes,
        *,
        user_id: str,
        mime_type: str | None = None,
        prompt: str | None = None,
    ) -> VisionAnalysis:
        settings = get_settings()
        if not (
            settings.external_ai_enabled
            and settings.nvidia_api_key
            and settings.brain_vision_model
        ):
            raise VisionUnavailableError("vision provider is not configured")
        if not image_bytes:
            raise ValueError("image is empty")
        if len(image_bytes) > settings.vision_max_image_bytes:
            raise ValueError("image exceeds configured size limit")
        if prompt is not None and len(prompt) > settings.vision_max_prompt_chars:
            raise ValueError("vision prompt exceeds configured size limit")

        detected_mime = detect_image_mime(image_bytes, mime_type)
        result = await self._adapter.analyze(
            image_bytes,
            mime_type=detected_mime,
            prompt=prompt,
        )
        await self._publish(
            "vision.analysis.completed",
            {
                "user_id": user_id,
                "model": result.model,
                "mime_type": result.mime_type,
                "bytes_processed": result.bytes_processed,
                "latency_ms": result.latency_ms,
            },
        )
        return result

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    {
                        "model": payload["model"],
                        "mime_type": payload["mime_type"],
                        "bytes_processed": payload["bytes_processed"],
                        "latency_ms": payload["latency_ms"],
                    },
                    user_id=payload.get("user_id"),
                )
            )
        except Exception:
            _LOGGER.warning("vision_event_publish_failed", exc_info=True)


def get_vision_service() -> VisionService:
    global _service
    if _service is None:
        _service = VisionService()
    return _service
