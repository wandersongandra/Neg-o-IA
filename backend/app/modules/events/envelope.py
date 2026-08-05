"""Contrato global do barramento de eventos — EventEnvelope (v1).

Todo evento do NEGÃO AI trafega neste envelope. O `type` é estável
(não carrega versão); `version` versiona o contrato do `payload`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EventEnvelope(BaseModel):
    """Envelope canônico de um evento do NEGÃO AI."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    version: int = 1
    producer: str
    trace_id: str | None = None
    correlation_id: str | None = None
    parent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    occurred_at: str = Field(default_factory=_utc_now_iso)
    payload: dict[str, Any] = Field(default_factory=dict)


def build_envelope(
    event_type: str,
    producer: str,
    payload: dict[str, Any] | None = None,
    *,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    parent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    version: int = 1,
) -> EventEnvelope:
    """Constrói um EventEnvelope preenchendo `id` e `occurred_at` automaticamente."""
    return EventEnvelope(
        type=event_type,
        version=version,
        producer=producer,
        trace_id=trace_id,
        correlation_id=correlation_id,
        parent_id=parent_id,
        user_id=user_id,
        session_id=session_id,
        payload=payload or {},
    )
