"""Testes do Vision V1."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.vision.application import VisionService


class FakeVisionAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def analyze(
        self,
        image_bytes: bytes,
        *,
        media_type: str,
        prompt: str,
    ) -> dict[str, Any]:
        self.calls.append({"image_bytes": image_bytes, "media_type": media_type, "prompt": prompt})
        return {"text": "imagem analisada", "model": "vision-test", "latency_ms": 1}


@pytest.mark.asyncio
async def test_vision_rejects_unsupported_media_type() -> None:
    service = VisionService(adapter=FakeVisionAdapter())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="unsupported"):
        await service.analyze(b"abc", media_type="image/gif")


@pytest.mark.asyncio
async def test_vision_analyzes_allowed_image(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = FakeVisionAdapter()
    service = VisionService(adapter=adapter)  # type: ignore[arg-type]

    class FakeBus:
        async def publish_event(self, envelope: Any) -> None:
            del envelope

    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: FakeBus(),
    )

    result = await service.analyze(
        b"fake-png",
        media_type="image/png",
        prompt="descreva",
        user_id="00000000-0000-0000-0000-000000000001",
    )

    assert result["text"] == "imagem analisada"
    assert adapter.calls[0]["prompt"] == "descreva"
