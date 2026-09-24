"""Testes do módulo Vision."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.vision.application import VisionService, VisionUnavailableError
from app.modules.vision.domain import VisionAnalysis
from app.modules.vision.infrastructure import detect_image_mime


class _FakeVisionAdapter:
    async def analyze(
        self,
        image_bytes: bytes,
        *,
        mime_type: str,
        prompt: str | None = None,
    ) -> VisionAnalysis:
        del prompt
        return VisionAnalysis(
            text="imagem analisada",
            model="vision-test",
            latency_ms=12,
            mime_type=mime_type,
            bytes_processed=len(image_bytes),
        )


class _NoopEventBus:
    async def publish_event(self, envelope: Any) -> None:
        del envelope


def test_detect_image_mime_rejects_spoofed_declared_type() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    with pytest.raises(ValueError, match="does not match"):
        detect_image_mime(png, "image/jpeg")


@pytest.mark.asyncio
async def test_vision_requires_explicit_external_ai_enablement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.vision.application.get_settings",
        lambda: SimpleNamespace(
            external_ai_enabled=False,
            nvidia_api_key="",
            brain_vision_model="",
            vision_max_image_bytes=1024,
            vision_max_prompt_chars=100,
        ),
    )
    service = VisionService(_FakeVisionAdapter())
    with pytest.raises(VisionUnavailableError):
        await service.analyze(
            b"\x89PNG\r\n\x1a\n" + b"x" * 20,
            user_id="user-1",
            mime_type="image/png",
        )


@pytest.mark.asyncio
async def test_vision_analyzes_valid_image_without_persisting_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.vision.application.get_settings",
        lambda: SimpleNamespace(
            external_ai_enabled=True,
            nvidia_api_key="secret",
            brain_vision_model="vision-test",
            vision_max_image_bytes=1024,
            vision_max_prompt_chars=100,
        ),
    )
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: _NoopEventBus(),
    )
    image = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    result = await VisionService(_FakeVisionAdapter()).analyze(
        image,
        user_id="user-1",
        mime_type="image/png",
        prompt="descreva",
    )
    assert result.text == "imagem analisada"
    assert result.bytes_processed == len(image)
