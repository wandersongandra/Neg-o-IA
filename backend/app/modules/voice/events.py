"""Contrato de eventos do módulo voice — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset({"voice.asr.completed"})

CONSUMED: frozenset[str] = frozenset(
    {"brain.response.ready", "voice.tts.requested"}
)
