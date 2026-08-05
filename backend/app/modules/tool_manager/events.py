"""Contrato de eventos do módulo tool_manager — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset(
    {"tool.execution.completed", "tool.execution.failed"}
)

CONSUMED: frozenset[str] = frozenset({"tool.execution.requested"})
