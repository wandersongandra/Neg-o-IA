"""Contrato de eventos do módulo automation."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"automation.rule.triggered"})

CONSUMED: frozenset[str] = frozenset(
    {
        "conversation.message.responded",
        "memory.long_term.written",
        "knowledge.document.ingested",
    }
)
