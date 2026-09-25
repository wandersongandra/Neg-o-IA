"""Interface HTTP do módulo Database — endpoints de infraestrutura.

Nota: em produção, estes endpoints serão protegidos pelo módulo Security
(integração na v1). Por ora servem para operação e debugging.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_db_session
from app.modules.configuration.settings import get_settings
from app.modules.database import get_database_provider
from app.modules.database.application import (
    audit_integrity_summary,
    count_audit_events,
    create_api_key,
    get_config,
    list_api_keys,
    list_audit_events,
    register_audit_event,
    revoke_api_key,
    set_config,
)
from app.modules.database.domain import DatabaseStatus
from app.modules.events.envelope import build_envelope

router = APIRouter(prefix="/database", tags=["database"])

_SENSITIVE_CONFIG_FRAGMENTS = ("secret", "password", "token", "api_key", "credential")
_ALLOWED_API_KEY_SCOPES = frozenset({"database:admin", "metrics:read"})


def _validate_config_payload(key: str, value: dict[str, Any]) -> None:
    normalized = key.lower().replace("-", "_")
    if not key or len(key) > 128:
        raise HTTPException(status_code=422, detail="invalid config key")
    if any(fragment in normalized for fragment in _SENSITIVE_CONFIG_FRAGMENTS):
        raise HTTPException(status_code=422, detail="secrets are not allowed in app_config")
    if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > 65_536:
        raise HTTPException(status_code=413, detail="config payload too large")


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=list, max_length=16)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, scopes: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(scope.strip() for scope in scopes if scope.strip()))
        unknown = sorted(set(normalized) - _ALLOWED_API_KEY_SCOPES)
        if unknown:
            raise ValueError(f"unknown service scopes: {', '.join(unknown)}")
        return normalized


class ApiKeyCreateResponse(BaseModel):
    key_id: str
    api_key: str
    name: str
    scopes: list[str]
    expires_at: datetime
    note: str = "Guarde esta chave agora; ela não será exibida novamente."


class ApiKeyMetadataResponse(BaseModel):
    key_id: str
    name: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime
    revoked_at: datetime | None = None


class ConfigItemResponse(BaseModel):
    key: str
    value: dict[str, Any]
    updated_at: str


@router.get("/status", response_model=DatabaseStatus, tags=["internal"])
async def database_status(session: SessionDep) -> DatabaseStatus:
    provider = get_database_provider(get_settings())
    connected = await provider.ping()
    events = 0
    if connected:
        events = await count_audit_events(session)
    return DatabaseStatus(
        connected=connected,
        engine_url=provider.engine_url,
        active_connections=0,
        detail=f"audit_events={events}",
    )


@router.get("/api-keys", response_model=list[ApiKeyMetadataResponse])
async def list_api_keys_endpoint(session: SessionDep) -> list[ApiKeyMetadataResponse]:
    records = await list_api_keys(session)
    return [
        ApiKeyMetadataResponse(
            key_id=record.id,
            name=record.name,
            scopes=record.scopes,
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
        )
        for record in records
    ]


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key_endpoint(
    request: ApiKeyCreateRequest,
    http_request: Request,
    session: SessionDep,
) -> ApiKeyCreateResponse:
    try:
        plain_key, record = await create_api_key(
            session,
            request.name,
            request.scopes,
            ttl_days=request.expires_in_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    auth = getattr(http_request.state, "auth_result", None)
    await register_audit_event(
        session,
        build_envelope(
            "security.service_key.created",
            "database",
            {
                "key_id": record.id,
                "name": record.name,
                "scopes": record.scopes,
                "expires_at": record.expires_at.isoformat(),
            },
            user_id=getattr(auth, "effective_user_id", None),
        ),
    )
    return ApiKeyCreateResponse(
        key_id=record.id,
        api_key=plain_key,
        name=record.name,
        scopes=record.scopes,
        expires_at=record.expires_at,
    )


@router.delete("/api-keys/{key_id}", status_code=204, response_model=None)
async def revoke_api_key_endpoint(
    key_id: str,
    http_request: Request,
    session: SessionDep,
) -> None:
    record = await revoke_api_key(session, key_id)
    if record is None:
        raise HTTPException(status_code=404, detail="api key not found")
    auth = getattr(http_request.state, "auth_result", None)
    await register_audit_event(
        session,
        build_envelope(
            "security.service_key.revoked",
            "database",
            {
                "key_id": record.id,
                "name": record.name,
                "scopes": record.scopes,
            },
            user_id=getattr(auth, "effective_user_id", None),
        ),
    )


@router.get("/audit/integrity", tags=["internal"])
async def audit_integrity(
    session: SessionDep,
    limit: int = Query(default=1000, ge=1, le=5000),
) -> dict[str, int]:
    return await audit_integrity_summary(session, limit=limit)


@router.get("/audit", tags=["internal"])
async def audit_events(
    session: SessionDep,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    records = await list_audit_events(session, limit=limit)
    return [record.__dict__ for record in records]


@router.get("/config/{key}")
async def config_get(key: str, session: SessionDep) -> ConfigItemResponse:
    record = await get_config(session, key)
    if record is None:
        raise HTTPException(status_code=404, detail="config key not found")
    return ConfigItemResponse(
        key=record.key, value=record.value, updated_at=record.updated_at.isoformat()
    )


@router.put("/config/{key}", response_model=ConfigItemResponse)
async def config_put(
    key: str,
    value: dict[str, Any],
    session: SessionDep,
) -> ConfigItemResponse:
    _validate_config_payload(key, value)
    record = await set_config(session, key, value)
    return ConfigItemResponse(
        key=record.key, value=record.value, updated_at=record.updated_at.isoformat()
    )
