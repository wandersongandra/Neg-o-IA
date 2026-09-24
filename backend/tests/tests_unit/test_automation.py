"""Testes de segurança do Automation V1."""

from __future__ import annotations

import pytest

from app.modules.automation.application import (
    AUTOMATION_TRIGGER_EVENTS,
    AutomationService,
    resolve_action_args,
)


def test_event_templates_only_resolve_explicit_paths() -> None:
    payload = {
        "session": {"id": "s-1"},
        "query": "status",
    }
    resolved = resolve_action_args(
        {
            "query": "$event.query",
            "nested": ["$event.session.id", "literal"],
        },
        payload,
    )

    assert resolved == {
        "query": "status",
        "nested": ["s-1", "literal"],
    }


def test_automation_trigger_allowlist_excludes_tool_events() -> None:
    assert "conversation.message.responded" in AUTOMATION_TRIGGER_EVENTS
    assert "tool.execution.completed" not in AUTOMATION_TRIGGER_EVENTS
    assert "automation.rule.triggered" not in AUTOMATION_TRIGGER_EVENTS


@pytest.mark.asyncio
async def test_automation_rejects_tool_that_requires_confirmation() -> None:
    service = AutomationService()

    with pytest.raises(ValueError, match="not safe"):
        await service.create_rule(
            "00000000-0000-0000-0000-000000000001",
            name="não salvar sozinho",
            event_type="conversation.message.responded",
            action_tool="memory.remember",
            action_args={"content": "não pode"},
        )
