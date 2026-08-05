"""Contrato de eventos do módulo brain — catálogo v1 (Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

PUBLISHED: frozenset[str] = frozenset(
    {
        "brain.input.received",
        "brain.planning.started",
        "brain.response.ready",
        "voice.tts.requested",
        "tool.execution.requested",
    }
)

CONSUMED: frozenset[str] = frozenset(
    {
        "voice.asr.completed",
        "vision.analysis.completed",
        "reasoning.intent.resolved",
        "planner.plan.created",
        "planner.plan.failed",
        "tool.execution.completed",
        "tool.execution.failed",
        "memory.read.completed",
        "knowledge.lookup.completed",
        "automation.rule.triggered",
    }
)
