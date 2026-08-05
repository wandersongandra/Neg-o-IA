from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.infrastructure.db import check_database_health
from app.infrastructure.redis import check_redis_health
from app.modules.configuration.settings import get_settings

router = APIRouter(tags=["infra"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/readyz")
async def readyz() -> dict[str, Any]:
    checks: dict[str, str] = {}
    checks["database"] = "ok" if await check_database_health() else "degraded"
    checks["redis"] = "ok" if await check_redis_health() else "degraded"
    ready = all(check_status == "ok" for check_status in checks.values())
    return {"status": "ok" if ready else "degraded", "checks": checks}


@router.get("/metrics")
async def metrics() -> Response:
    if not get_settings().metrics_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metrics disabled",
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/events/health")
async def events_health() -> dict[str, Any]:
    bus_available = False
    try:
        from app.modules.events.application import get_event_bus_service

        service = get_event_bus_service()
        bus_available = bool(service) and service.is_available
    except Exception:
        bus_available = False
    return {"status": "ok" if bus_available else "degraded", "bus_available": bus_available}
