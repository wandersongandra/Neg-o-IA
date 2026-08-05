"""Contrato de eventos do módulo knowledge — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"knowledge.lookup.completed"})

CONSUMED: frozenset[str] = frozenset()
