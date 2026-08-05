"""Interface HTTP do módulo Database — endpoints de infraestrutura.

Nota: em produção, estes endpoints serão protegidos pelo módulo Security
(integração na v1). Por ora servem para operação e debugging.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_db_session
from app.modules.configuration.settings import get_settings
from app.modules.database import get_database_provider
from app.modules.database.application import (
    count_audit_events,
    create_api_key,
    get_config,
    list_audit_events,
    set_config,
)
from app.modules.database.domain import DatabaseStatus

router = APIRouter(prefix="/database", tags=["database"])

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=list)


class ApiKeyCreateResponse(BaseModel):
    api_key: str
    name: str
    scopes: list[str]
    note: str = "Guarde esta chave agora; ela não será exibida novamente."


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


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key_endpoint(
    request: ApiKeyCreateRequest,
    session: SessionDep,
) -> ApiKeyCreateResponse:
    plain_key, _ = await create_api_key(session, request.name, request.scopes)
    return ApiKeyCreateResponse(
        api_key=plain_key, name=request.name, scopes=request.scopes
    )


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
    record = await set_config(session, key, value)
    return ConfigItemResponse(
        key=record.key, value=record.value, updated_at=record.updated_at.isoformat()
    )
