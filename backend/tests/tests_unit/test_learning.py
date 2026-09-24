"""Testes do Learning V1."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.modules.learning.application import LearningService


class FakeMemory:
    async def remember(self, user_id: str, content: str, **kwargs: Any) -> Any:
        return type(
            "Entry",
            (),
            {
                "id": "memory-1",
                "user_id": user_id,
                "content": content,
                "created_at": datetime.now(UTC),
            },
        )()


class FakeBus:
    async def publish_event(self, envelope: Any) -> None:
        del envelope


@pytest.mark.asyncio
async def test_learning_records_only_explicit_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.learning.application.get_long_term_memory_service",
        lambda: FakeMemory(),
    )
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: FakeBus(),
    )
    result = await LearningService().record_feedback(
        "00000000-0000-0000-0000-000000000001",
        "Prefiro respostas curtas",
        rating=1,
    )
    assert result.rating == 1
    status = await LearningService().status()
    assert status["adaptive_prompt"] is False
    assert status["autonomous_training"] is False


@pytest.mark.asyncio
async def test_learning_rejects_neutral_or_invalid_rating() -> None:
    with pytest.raises(ValueError, match="rating"):
        await LearningService().record_feedback(
            "00000000-0000-0000-0000-000000000001",
            "feedback",
            rating=0,
        )
