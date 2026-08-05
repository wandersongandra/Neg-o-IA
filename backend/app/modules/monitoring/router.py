"""Rotas internas de observabilidade — métricas e logs do dashboard (v0)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from app.modules.monitoring.application import get_monitoring_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _is_debug() -> bool:
    try:
        from app.modules.configuration.settings import get_settings

        return bool(getattr(get_settings(), "debug", False))
    except Exception:
        return os.getenv("NEGAO_DEBUG", "").lower() in {"1", "true", "yes"}


def _log_file_path() -> Path | None:
    try:
        from app.modules.configuration.settings import get_settings

        path = getattr(get_settings(), "log_file", None)
        if path:
            return Path(path)
    except Exception:
        pass
    for candidate in ("logs/app.log", "backend/logs/app.log", "app.log"):
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def _tail(path: Path, max_lines: int) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return []
    return [line.rstrip("\n") for line in lines[-max_lines:]]


@router.get("/metrics")
async def monitoring_metrics() -> Response:
    """Re-exporta as métricas Prometheus para o dashboard interno."""
    service = get_monitoring_service()
    return Response(
        content=service.get_snapshot(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/logs")
async def monitoring_logs() -> dict[str, Any]:
    """Últimas 100 linhas do arquivo de log — apenas em ambiente debug."""
    if not _is_debug():
        raise HTTPException(status_code=403, detail="logs disponíveis apenas em debug")
    path = _log_file_path()
    lines = _tail(path, 100) if path is not None else []
    return {"file": str(path) if path is not None else None, "lines": lines}
