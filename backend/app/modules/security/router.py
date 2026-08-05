"""Roteador de segurança — autenticação por API key e auditoria de acesso.

A auditoria de acessos (sucesso/falha) é publicada como eventos best-effort
no barramento (`security.auth.completed` / `security.auth.failed`); não há
storage local de tentativas, então a trilha de auditoria fica nos consumers.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.modules.security.application import SecurityService
from app.modules.security.domain import AuthResult
from app.modules.security.infrastructure import get_security_service

router = APIRouter(prefix="/security", tags=["security"])

_logger = structlog.get_logger("negao.security")

_AUTH_EVENT_PUBLISH_TIMEOUT = 2.0


async def _publish_auth_event(event_type: str, result: AuthResult) -> None:
    from app.modules.events.application import get_event_bus_service
    from app.modules.events.envelope import build_envelope

    envelope = build_envelope(
        event_type,
        producer="security",
        payload={
            "principal": result.principal,
            "authorization_level": result.authorization_level.name,
            "reason": result.reason,
        },
    )
    await asyncio.wait_for(
        get_event_bus_service().publish_event(envelope),
        timeout=_AUTH_EVENT_PUBLISH_TIMEOUT,
    )


async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    service: Annotated[SecurityService, Depends(get_security_service)] = None,  # type: ignore[assignment]
) -> AuthResult:
    result = service.authenticate_api_key(x_api_key or "")
    if not result.authenticated:
        try:
            await _publish_auth_event("security.auth.failed", result)
        except Exception:
            _logger.warning("auth_failed_event_publish_error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.reason or "invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    request.state.auth_result = result
    try:
        await _publish_auth_event("security.auth.completed", result)
    except Exception:
        _logger.warning("auth_completed_event_publish_error", exc_info=True)
    return result


@router.get("/status")
async def security_status(
    auth: Annotated[AuthResult, Depends(require_api_key)],
) -> dict[str, object]:
    return {
        "status": "ok",
        "authenticated": True,
        "authorization_level": auth.authorization_level.name,
        "authorization_level_id": auth.authorization_level.value,
        "principal": auth.principal,
    }
