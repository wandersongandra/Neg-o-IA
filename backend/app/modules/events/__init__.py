"""Módulo events — barramento de eventos (v0): envelope, EventBus e facade."""

from app.modules.events.envelope import EventEnvelope, build_envelope

__all__ = ["EventEnvelope", "build_envelope"]
