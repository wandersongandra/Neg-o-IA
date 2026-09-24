"""Testes dos limites de planejamento."""

from __future__ import annotations

from app.modules.planner.application import PlannerService


def test_memory_write_step_requires_confirmation() -> None:
    steps = PlannerService._steps_for_resolution(
        "Lembre que gosto de Python",
        "memory.remember",
        {"content": "gosto de Python"},
    )

    assert steps[0].tool_name == "memory.remember"
    assert steps[0].requires_confirmation is True
    assert steps[0].arguments["content"] == "gosto de Python"


def test_read_only_search_does_not_require_confirmation() -> None:
    steps = PlannerService._steps_for_resolution(
        "Procure na memória meu projeto",
        "memory.search",
        {"query": "meu projeto"},
    )

    assert steps[0].tool_name == "memory.search"
    assert steps[0].requires_confirmation is False
    assert steps[0].arguments["limit"] == 5
