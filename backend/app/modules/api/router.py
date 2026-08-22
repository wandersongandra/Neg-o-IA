from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.infrastructure.db import check_database_health
from app.infrastructure.redis import check_redis_health
from app.modules.configuration.settings import get_settings

router = APIRouter(tags=["infra"])


@router.get("/health/live")
@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
@router.get("/readyz")
async def readyz() -> Response:
    checks: dict[str, str] = {}
    checks["database"] = "ok" if await check_database_health() else "degraded"
    checks["redis"] = "ok" if await check_redis_health() else "degraded"
    ready = all(check_status == "ok" for check_status in checks.values())
    payload: dict[str, Any] = {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )


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
    redis_available = False
    try:
        redis_available = await check_redis_health()
    except Exception:
        redis_available = False
    payload = {"status": "ok" if redis_available else "degraded", "bus_available": redis_available}
    return payload
