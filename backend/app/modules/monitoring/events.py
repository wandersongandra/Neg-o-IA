"""Contrato de eventos do módulo monitoring (consumidos via Event Bus)."""

from __future__ import annotations

EVENT_VERSION = 1

EVENT_METRIC_PUBLISHED = "monitoring.metric.published"

PUBLISHED: frozenset[str] = frozenset({EVENT_METRIC_PUBLISHED})

CONSUMED: frozenset[str] = frozenset(
    {
        "events.published",
        "events.dlq.received",
        "brain.input.received",
        "brain.planning.started",
        "brain.response.ready",
        "voice.asr.completed",
        "vision.analysis.completed",
        "reasoning.intent.resolved",
        "planner.plan.created",
        "planner.plan.failed",
        "tool.execution.completed",
        "tool.execution.failed",
        "knowledge.lookup.completed",
        "memory.read.completed",
        "memory.written",
        "learning.experience.recorded",
        "automation.rule.triggered",
        "scheduler.tick",
    }
)
