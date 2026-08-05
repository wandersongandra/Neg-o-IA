"""Contrato de eventos do módulo automation — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"automation.rule.triggered"})

CONSUMED: frozenset[str] = frozenset({"scheduler.tick"})
