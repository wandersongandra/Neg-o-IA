"""Contrato de eventos do módulo learning — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"learning.experience.recorded"})

CONSUMED: frozenset[str] = frozenset(
    {
        "reasoning.intent.resolved",
        "planner.plan.failed",
        "tool.execution.completed",
        "tool.execution.failed",
        "knowledge.lookup.completed",
        "memory.read.completed",
        "memory.written",
    }
)
