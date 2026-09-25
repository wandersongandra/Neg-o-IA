"""Adaptadores do módulo Vision."""

from __future__ import annotations

import base64
import time
from typing import Any

from app.infrastructure.provider_http import (
    ProviderInvalidResponseError,
    ProviderResponseTooLargeError,
    new_provider_http_client,
    post_json_limited,
)
from app.modules.configuration.settings import get_settings
from app.modules.vision.domain import VisionAnalysis

_ALLOWED_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


class VisionProviderError(RuntimeError):
    pass


def detect_image_mime(image_bytes: bytes, declared: str | None = None) -> str:
    detected: str | None = None
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image/png"
    elif image_bytes[:3] == b"\xff\xd8\xff":
        detected = "image/jpeg"
    elif len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        detected = "image/webp"

    if detected is None:
        raise ValueError("unsupported or invalid image format")
    if declared is not None and declared not in _ALLOWED_MIME_TYPES:
        raise ValueError("unsupported declared mime type")
    if declared is not None and declared != detected:
        raise ValueError("declared mime type does not match image content")
    return detected


def _extract_text(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise VisionProviderError("invalid vision provider payload") from exc
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                text = item["text"].strip()
                if text:
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    raise VisionProviderError("vision provider returned empty content")


class NvidiaVisionAdapter:
    """Adapter OpenAI-compatible para modelos multimodais da NVIDIA."""

    async def analyze(
        self,
        image_bytes: bytes,
        *,
        mime_type: str,
        prompt: str | None = None,
    ) -> VisionAnalysis:
        settings = get_settings()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        user_prompt = (
            prompt.strip()
            if prompt and prompt.strip()
            else (
                "Descreva esta imagem com precisão. Identifique objetos, texto visível, "
                "contexto e detalhes relevantes. Não invente informações que não estejam "
                "visíveis."
            )
        )
        payload = {
            "model": settings.brain_vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded}",
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": settings.brain_max_tokens,
        }
        started = time.perf_counter()
        try:
            async with new_provider_http_client(settings.vision_timeout_seconds) as client:
                response = await post_json_limited(
                    client,
                    f"{settings.nvidia_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                    payload=payload,
                    max_response_bytes=settings.provider_max_response_bytes,
                )
        except ProviderResponseTooLargeError as exc:
            raise VisionProviderError("vision provider response too large") from exc
        except ProviderInvalidResponseError as exc:
            raise VisionProviderError("vision provider returned invalid JSON") from exc
        except Exception as exc:
            raise VisionProviderError("vision provider network error") from exc
        if response.status_code >= 400 or response.payload is None:
            raise VisionProviderError(f"vision provider HTTP {response.status_code}")
        body = response.payload
        return VisionAnalysis(
            text=_extract_text(body),
            model=settings.brain_vision_model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            mime_type=mime_type,
            bytes_processed=len(image_bytes),
        )
