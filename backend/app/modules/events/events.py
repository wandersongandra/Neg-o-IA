"""Contrato de eventos do próprio barramento (módulo events)."""

from __future__ import annotations

EVENT_VERSION = 1

EVENT_PUBLISHED = "events.published"
EVENT_DLQ_RECEIVED = "events.dlq.received"

PUBLISHED: frozenset[str] = frozenset({EVENT_PUBLISHED})

CONSUMED: frozenset[str] = frozenset({EVENT_DLQ_RECEIVED})
