"""Adaptador multimodal OpenAI-compatible para Vision V1."""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from app.modules.configuration.settings import Settings, get_settings


class VisionError(RuntimeError):
    """Erro base do módulo de visão."""


class VisionUnavailableError(VisionError):
    """Visão desativada ou sem provider configurado."""


class VisionProviderError(VisionError):
    """Falha do provider multimodal."""


class OpenAICompatibleVisionAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._settings.vision_timeout_seconds)
        return self._client

    async def analyze(
        self,
        image_bytes: bytes,
        *,
        media_type: str,
        prompt: str,
    ) -> dict[str, Any]:
        settings = self._settings
        if (
            not settings.vision_enabled
            or not settings.external_ai_enabled
            or not settings.nvidia_api_key
            or not settings.vision_model.strip()
        ):
            raise VisionUnavailableError("vision provider is not configured")

        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{media_type};base64,{encoded}"
        payload = {
            "model": settings.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": min(settings.brain_max_tokens, 2048),
        }
        started = time.perf_counter()
        try:
            response = await self._http().post(
                f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
            )
        except httpx.HTTPError as exc:
            raise VisionProviderError("vision provider network error") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code != 200:
            raise VisionProviderError(f"vision provider returned HTTP {response.status_code}")
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise VisionProviderError("vision provider returned an invalid payload") from exc

        return {
            "text": str(text),
            "model": settings.vision_model,
            "latency_ms": latency_ms,
        }
