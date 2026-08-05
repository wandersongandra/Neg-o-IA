"""Contrato de eventos do módulo scheduler — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"scheduler.tick"})

CONSUMED: frozenset[str] = frozenset(
    {"planner.plan.created", "automation.rule.triggered"}
)
