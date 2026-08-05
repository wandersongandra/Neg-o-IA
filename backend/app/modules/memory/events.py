"""Contrato de eventos do módulo memory (publicados via Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

EVENT_MEMORY_WRITTEN = "memory.written"
EVENT_MEMORY_READ_COMPLETED = "memory.read.completed"

PUBLISHED: frozenset[str] = frozenset(
    {EVENT_MEMORY_WRITTEN, EVENT_MEMORY_READ_COMPLETED}
)

CONSUMED: frozenset[str] = frozenset(
    {
        "learning.experience.recorded",
        "tool.execution.completed",
    }
)
