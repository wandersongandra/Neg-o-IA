"""Testes do Reasoning V1."""

from __future__ import annotations

import pytest

from app.modules.events.envelope import EventEnvelope
from app.modules.reasoning.application import ReasoningService


class _NoopEventBus:
    async def publish_event(self, envelope: EventEnvelope) -> None:
        del envelope


@pytest.mark.asyncio
async def test_explicit_remember_intent_requires_write_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: _NoopEventBus(),
    )
    result = await ReasoningService().resolve_intent(
        "Lembre que eu prefiro respostas curtas",
        user_id="user-1",
    )

    assert result.intent == "memory.remember"
    assert result.suggested_tool == "memory.remember"
    assert result.explicit_action is True
    assert result.entities["content"] == "eu prefiro respostas curtas"


@pytest.mark.asyncio
async def test_regular_chat_does_not_invent_tool_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: _NoopEventBus(),
    )
    result = await ReasoningService().resolve_intent(
        "Explique recursão de forma simples",
        user_id="user-1",
    )

    assert result.intent == "chat"
    assert result.requires_plan is False
    assert result.suggested_tool is None
