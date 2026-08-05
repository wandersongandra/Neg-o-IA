"""Rotas HTTP do módulo events — status do barramento e publicação de debug."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.events.application import get_event_bus_service
from app.modules.events.envelope import build_envelope

router = APIRouter(prefix="/events", tags=["events"])


class EventPublishRequest(BaseModel):
    """Payload de debug para publicar um evento manualmente (apenas dev)."""

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None
    parent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None


def _is_production() -> bool:
    try:
        from app.modules.configuration.settings import get_settings

        settings = get_settings()
        if getattr(settings, "env", None):
            return settings.env == "production"
    except Exception:
        pass
    return os.getenv("NEGAO_ENV", "development") == "production"


@router.get("/status")
async def events_status() -> dict[str, Any]:
    """Estado do barramento: streams ativos, handlers registrados e entregas."""
    service = get_event_bus_service()
    return service.status


@router.post("/_publish")
async def publish_event_debug(request: EventPublishRequest) -> dict[str, Any]:
    """Publica um evento manualmente — disponível apenas fora de produção."""
    if _is_production():
        raise HTTPException(
            status_code=403, detail="publicação de debug desativada em produção"
        )
    service = get_event_bus_service()
    envelope = build_envelope(
        request.type,
        producer="events.debug",
        payload=request.payload,
        trace_id=request.trace_id,
        correlation_id=request.correlation_id,
        parent_id=request.parent_id,
        user_id=request.user_id,
        session_id=request.session_id,
    )
    await service.publish_event(envelope)
    return {"published": True, "envelope": envelope.model_dump()}
