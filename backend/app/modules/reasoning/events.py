"""Contrato de eventos do módulo reasoning — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"reasoning.intent.resolved"})

CONSUMED: frozenset[str] = frozenset()
