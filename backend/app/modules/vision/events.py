"""Contrato de eventos do módulo vision — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"vision.analysis.completed"})

CONSUMED: frozenset[str] = frozenset()
