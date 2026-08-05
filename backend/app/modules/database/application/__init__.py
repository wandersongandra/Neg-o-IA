"""Casos de uso do módulo Database — API de persistência da fundação."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ApiKeyRecord, AppConfigRecord, AuditEventRecord
from app.modules.database.infrastructure import ApiKeyORM, AppConfigORM, AuditEventORM
from app.modules.events.envelope import EventEnvelope


def hash_api_key(key: str) -> str:
    """Hash SHA-256 da chave em texto puro (nunca armazenar a chave)."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """Gera uma chave de API aleatória (URL-safe, 43 chars)."""
    return secrets.token_urlsafe(32)


async def create_api_key(
    session: AsyncSession, name: str, scopes: list[str] | None = None
) -> tuple[str, ApiKeyRecord]:
    """Cria uma API key; retorna (plain_key, record). A plain key só é mostrada uma vez."""
    plain_key = generate_api_key()
    record = ApiKeyORM(
        key_hash=hash_api_key(plain_key),
        name=name,
        scopes=scopes or [],
    )
    session.add(record)
    await session.flush()
    domain = ApiKeyRecord(
        id=str(record.id),
        key_hash=record.key_hash,
        name=record.name,
        scopes=list(record.scopes),
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
    )
    return plain_key, domain


async def verify_api_key(session: AsyncSession, key: str) -> ApiKeyRecord | None:
    """Valida uma chave: hash, existência e não revogação. Atualiza last_used_at."""
    result = await session.execute(
        select(ApiKeyORM).where(ApiKeyORM.key_hash == hash_api_key(key))
    )
    record = result.scalar_one_or_none()
    if record is None or record.revoked_at is not None:
        return None
    record.last_used_at = datetime.now(UTC)
    await session.flush()
    return ApiKeyRecord(
        id=str(record.id),
        key_hash=record.key_hash,
        name=record.name,
        scopes=list(record.scopes),
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
    )


async def register_audit_event(
    session: AsyncSession, envelope: EventEnvelope
) -> AuditEventRecord:
    """Persiste um evento no esquema `events` (base da auditoria completa)."""
    row = AuditEventORM(
        id=uuid.UUID(envelope.id),
        event_type=envelope.type,
        version=envelope.version,
        producer=envelope.producer,
        trace_id=uuid.UUID(envelope.trace_id) if envelope.trace_id else None,
        correlation_id=(
            uuid.UUID(envelope.correlation_id) if envelope.correlation_id else None
        ),
        parent_id=uuid.UUID(envelope.parent_id) if envelope.parent_id else None,
        user_id=uuid.UUID(envelope.user_id) if envelope.user_id else None,
        session_id=uuid.UUID(envelope.session_id) if envelope.session_id else None,
        occurred_at=datetime.fromisoformat(envelope.occurred_at),
        payload=envelope.payload,
    )
    session.add(row)
    await session.flush()
    return AuditEventRecord(
        id=str(row.id),
        event_type=row.event_type,
        version=row.version,
        producer=row.producer,
        payload=row.payload,
        trace_id=str(row.trace_id) if row.trace_id else None,
        correlation_id=str(row.correlation_id) if row.correlation_id else None,
        parent_id=str(row.parent_id) if row.parent_id else None,
        user_id=str(row.user_id) if row.user_id else None,
        session_id=str(row.session_id) if row.session_id else None,
        occurred_at=row.occurred_at,
    )


async def list_audit_events(session: AsyncSession, limit: int = 100) -> list[AuditEventRecord]:
    """Lista os eventos de auditoria mais recentes."""
    result = await session.execute(
        select(AuditEventORM).order_by(AuditEventORM.occurred_at.desc()).limit(limit)
    )
    return [
        AuditEventRecord(
            id=str(row.id),
            event_type=row.event_type,
            version=row.version,
            producer=row.producer,
            payload=row.payload,
            trace_id=str(row.trace_id) if row.trace_id else None,
            correlation_id=str(row.correlation_id) if row.correlation_id else None,
            parent_id=str(row.parent_id) if row.parent_id else None,
            user_id=str(row.user_id) if row.user_id else None,
            session_id=str(row.session_id) if row.session_id else None,
            occurred_at=row.occurred_at,
        )
        for row in result.scalars()
    ]


async def get_config(session: AsyncSession, key: str) -> AppConfigRecord | None:
    result = await session.execute(
        select(AppConfigORM).where(AppConfigORM.key == key)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return AppConfigRecord(key=row.key, value=row.value, updated_at=row.updated_at)


async def set_config(
    session: AsyncSession, key: str, value: dict[str, Any]
) -> AppConfigRecord:
    row = await session.get(AppConfigORM, key)
    if row is None:
        row = AppConfigORM(key=key, value=value)
        session.add(row)
    else:
        row.value = value
        row.updated_at = datetime.now(UTC)
    await session.flush()
    return AppConfigRecord(key=row.key, value=row.value, updated_at=row.updated_at)


async def count_audit_events(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(AuditEventORM))
    return int(result.scalar_one())
