"""Casos de uso do módulo Database — API de persistência da fundação."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ApiKeyRecord, AppConfigRecord, AuditEventRecord
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import ApiKeyORM, AppConfigORM, AuditEventORM
from app.modules.events.envelope import EventEnvelope

PERSISTED_API_KEY_PREFIX = "sophie_sk_"
_AUDIT_KEY_CONTEXT = b"sophie:audit-integrity:v1"


def _audit_integrity_key(secret_key: str) -> bytes:
    return hmac.new(
        secret_key.encode("utf-8"),
        _AUDIT_KEY_CONTEXT,
        hashlib.sha256,
    ).digest()


def _audit_integrity_material(
    *,
    event_id: str,
    event_type: str,
    version: int,
    producer: str,
    trace_id: str | None,
    correlation_id: str | None,
    parent_id: str | None,
    user_id: str | None,
    session_id: str | None,
    occurred_at: datetime,
    payload: dict[str, Any],
) -> bytes:
    material = {
        "id": event_id,
        "event_type": event_type,
        "version": version,
        "producer": producer,
        "trace_id": trace_id,
        "correlation_id": correlation_id,
        "parent_id": parent_id,
        "user_id": user_id,
        "session_id": session_id,
        "occurred_at": occurred_at.isoformat(),
        "payload": payload,
    }
    return json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _compute_audit_integrity_hash(
    *,
    secret_key: str | None = None,
    event_id: str,
    event_type: str,
    version: int,
    producer: str,
    trace_id: str | None,
    correlation_id: str | None,
    parent_id: str | None,
    user_id: str | None,
    session_id: str | None,
    occurred_at: datetime,
    payload: dict[str, Any],
) -> str:
    return hmac.new(
        _audit_integrity_key(secret_key or get_settings().effective_audit_integrity_keys()[0]),
        _audit_integrity_material(
            event_id=event_id,
            event_type=event_type,
            version=version,
            producer=producer,
            trace_id=trace_id,
            correlation_id=correlation_id,
            parent_id=parent_id,
            user_id=user_id,
            session_id=session_id,
            occurred_at=occurred_at,
            payload=payload,
        ),
        hashlib.sha256,
    ).hexdigest()


def verify_audit_event_integrity(row: AuditEventORM) -> bool | None:
    if not row.integrity_hash:
        return None
    for secret_key in get_settings().effective_audit_integrity_keys():
        expected = _compute_audit_integrity_hash(
            secret_key=secret_key,
            event_id=str(row.id),
            event_type=row.event_type,
            version=row.version,
            producer=row.producer,
            trace_id=row.trace_id,
            correlation_id=row.correlation_id,
            parent_id=row.parent_id,
            user_id=row.user_id,
            session_id=row.session_id,
            occurred_at=row.occurred_at,
            payload=row.payload,
        )
        if hmac.compare_digest(row.integrity_hash, expected):
            return True
    return False


def hash_api_key(key: str) -> str:
    """Hash SHA-256 da chave em texto puro (nunca armazenar a chave)."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """Gera uma chave de API aleatória (URL-safe, 43 chars)."""
    return PERSISTED_API_KEY_PREFIX + secrets.token_urlsafe(32)


async def create_api_key(
    session: AsyncSession,
    name: str,
    scopes: list[str] | None = None,
    *,
    ttl_days: int | None = None,
) -> tuple[str, ApiKeyRecord]:
    """Cria uma API key expiráveI; a plain key só é mostrada uma vez."""
    settings = get_settings()
    effective_ttl = ttl_days or settings.service_api_key_default_ttl_days
    if not 1 <= effective_ttl <= settings.service_api_key_max_ttl_days:
        raise ValueError("service api key ttl outside allowed range")
    plain_key = generate_api_key()
    expires_at = datetime.now(UTC) + timedelta(days=effective_ttl)
    record = ApiKeyORM(
        key_hash=hash_api_key(plain_key),
        name=name,
        scopes=scopes or [],
        expires_at=expires_at,
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
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )
    return plain_key, domain


async def revoke_api_key(session: AsyncSession, key_id: str) -> ApiKeyRecord | None:
    """Revoga uma chave persistida e retorna somente seus metadados."""
    try:
        parsed_id = uuid.UUID(key_id)
    except ValueError:
        return None
    record = await session.get(ApiKeyORM, parsed_id)
    if record is None or record.revoked_at is not None:
        return None
    record.revoked_at = datetime.now(UTC)
    await session.flush()
    return ApiKeyRecord(
        id=str(record.id),
        key_hash=record.key_hash,
        name=record.name,
        scopes=list(record.scopes),
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )


async def verify_api_key(session: AsyncSession, key: str) -> ApiKeyRecord | None:
    """Valida hash, revogação e expiração; atualiza last_used_at somente se válida."""
    result = await session.execute(select(ApiKeyORM).where(ApiKeyORM.key_hash == hash_api_key(key)))
    record = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if record is None or record.revoked_at is not None or record.expires_at <= now:
        return None
    record.last_used_at = now
    await session.flush()
    return ApiKeyRecord(
        id=str(record.id),
        key_hash=record.key_hash,
        name=record.name,
        scopes=list(record.scopes),
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )


async def list_api_keys(session: AsyncSession) -> list[ApiKeyRecord]:
    result = await session.execute(
        select(ApiKeyORM).order_by(ApiKeyORM.created_at.desc(), ApiKeyORM.id.desc())
    )
    return [
        ApiKeyRecord(
            id=str(record.id),
            key_hash=record.key_hash,
            name=record.name,
            scopes=list(record.scopes),
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
        )
        for record in result.scalars()
    ]


async def register_audit_event(session: AsyncSession, envelope: EventEnvelope) -> AuditEventRecord:
    """Persiste evento de auditoria com HMAC para detectar adulteração no banco."""
    occurred_at = datetime.fromisoformat(envelope.occurred_at)
    integrity_hash = _compute_audit_integrity_hash(
        event_id=envelope.id,
        event_type=envelope.type,
        version=envelope.version,
        producer=envelope.producer,
        trace_id=envelope.trace_id,
        correlation_id=envelope.correlation_id,
        parent_id=envelope.parent_id,
        user_id=envelope.user_id,
        session_id=envelope.session_id,
        occurred_at=occurred_at,
        payload=envelope.payload,
    )
    row = AuditEventORM(
        id=uuid.UUID(envelope.id),
        event_type=envelope.type,
        version=envelope.version,
        producer=envelope.producer,
        trace_id=envelope.trace_id,
        correlation_id=envelope.correlation_id,
        parent_id=envelope.parent_id,
        user_id=envelope.user_id,
        session_id=envelope.session_id,
        occurred_at=occurred_at,
        payload=envelope.payload,
        integrity_hash=integrity_hash,
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
        integrity_hash=row.integrity_hash,
        integrity_valid=True,
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
            integrity_hash=row.integrity_hash,
            integrity_valid=verify_audit_event_integrity(row),
            occurred_at=row.occurred_at,
        )
        for row in result.scalars()
    ]


async def audit_integrity_summary(session: AsyncSession, limit: int = 1000) -> dict[str, int]:
    result = await session.execute(
        select(AuditEventORM).order_by(AuditEventORM.occurred_at.desc()).limit(limit)
    )
    summary = {"verified": 0, "invalid": 0, "unsigned_legacy": 0}
    for row in result.scalars():
        valid = verify_audit_event_integrity(row)
        if valid is True:
            summary["verified"] += 1
        elif valid is False:
            summary["invalid"] += 1
        else:
            summary["unsigned_legacy"] += 1
    return summary


async def get_config(session: AsyncSession, key: str) -> AppConfigRecord | None:
    result = await session.execute(select(AppConfigORM).where(AppConfigORM.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return AppConfigRecord(key=row.key, value=row.value, updated_at=row.updated_at)


async def set_config(session: AsyncSession, key: str, value: dict[str, Any]) -> AppConfigRecord:
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
