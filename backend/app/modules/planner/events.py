"""Contrato de eventos do módulo planner — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset(
    {"planner.plan.created", "planner.plan.failed"}
)

CONSUMED: frozenset[str] = frozenset()
