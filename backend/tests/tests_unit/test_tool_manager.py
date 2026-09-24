"""Testes de governança do Tool Manager."""

from __future__ import annotations

import pytest

from app.modules.tool_manager.application import (
    ToolConfirmationRequiredError,
    ToolManagerService,
)


def test_catalog_is_closed_and_marks_write_tool_unsafe_for_automation() -> None:
    service = ToolManagerService()
    specs = {spec.name: spec for spec in service.catalog()}

    assert set(specs) == {
        "knowledge.list_documents",
        "knowledge.search",
        "memory.remember",
        "memory.search",
        "system.health",
    }
    assert specs["memory.remember"].requires_confirmation is True
    assert specs["memory.remember"].automation_safe is False
    assert specs["system.health"].automation_safe is True


@pytest.mark.asyncio
async def test_write_tool_cannot_execute_without_confirmation() -> None:
    service = ToolManagerService()

    with pytest.raises(ToolConfirmationRequiredError):
        await service.execute_tool(
            "memory.remember",
            {"content": "segredo que não deve ser salvo sem confirmação"},
            user_id="00000000-0000-0000-0000-000000000001",
            confirmed=False,
        )
