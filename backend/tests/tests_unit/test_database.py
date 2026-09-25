"""Testes unitários do módulo Database (sessão mockada)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.configuration.settings import Settings
from app.modules.database.application import (
    create_api_key,
    generate_api_key,
    hash_api_key,
    register_audit_event,
    verify_api_key,
    verify_audit_event_integrity,
)
from app.modules.database.infrastructure import ApiKeyORM
from app.modules.events.envelope import build_envelope


def _execute_returning(row: ApiKeyORM | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    return result


def test_hash_api_key_is_deterministic() -> None:
    key = "chave-exemplo-123"
    assert hash_api_key(key) == hash_api_key(key)
    assert len(hash_api_key(key)) == 64


def test_generate_api_key_is_unique_and_safe() -> None:
    k1 = generate_api_key()
    k2 = generate_api_key()
    assert k1 != k2
    assert k1.startswith("sophie_sk_")
    assert k2.startswith("sophie_sk_")
    assert len(k1) > 43


@pytest.mark.asyncio
async def test_create_api_key_returns_plain_key_and_record(fake_session: AsyncMock) -> None:
    fake_session.flush = AsyncMock()
    plain_key, record = await create_api_key(fake_session, "teste", ["read"])
    assert plain_key
    assert record.name == "teste"
    assert record.key_hash == hash_api_key(plain_key)
    assert record.scopes == ["read"]
    assert record.expires_at is not None
    assert record.expires_at > datetime.now(UTC)
    added = fake_session.add.call_args.args[0]
    assert isinstance(added, ApiKeyORM)


@pytest.mark.asyncio
async def test_verify_api_key_revoked_returns_none(fake_session: AsyncMock) -> None:
    row = ApiKeyORM(
        key_hash=hash_api_key("chave"),
        name="x",
        scopes=[],
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=datetime.now(UTC),
    )
    fake_session.execute.return_value = _execute_returning(row)

    record = await verify_api_key(fake_session, "chave")
    assert record is None


@pytest.mark.asyncio
async def test_verify_api_key_expired_returns_none(fake_session: AsyncMock) -> None:
    row = ApiKeyORM(
        key_hash=hash_api_key("chave"),
        name="x",
        scopes=[],
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    fake_session.execute.return_value = _execute_returning(row)

    record = await verify_api_key(fake_session, "chave")
    assert record is None
    assert row.last_used_at is None


@pytest.mark.asyncio
async def test_verify_api_key_valid_updates_last_used(fake_session: AsyncMock) -> None:
    row = ApiKeyORM(
        key_hash=hash_api_key("chave"),
        name="x",
        scopes=["read"],
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    fake_session.execute.return_value = _execute_returning(row)

    record = await verify_api_key(fake_session, "chave")
    assert record is not None
    assert record.revoked_at is None
    assert row.last_used_at is not None


@pytest.mark.asyncio
async def test_register_audit_event_maps_envelope(fake_session: AsyncMock) -> None:
    envelope = build_envelope(
        "brain.input.received",
        "brain",
        {"text": "oi"},
        trace_id=str(uuid.uuid4()),
        correlation_id=str(uuid.uuid4()),
    )
    record = await register_audit_event(fake_session, envelope)
    assert record.event_type == "brain.input.received"
    assert record.producer == "brain"
    assert record.trace_id == envelope.trace_id
    assert record.payload == {"text": "oi"}
    added = fake_session.add.call_args.args[0]
    assert added.event_type == envelope.type
    assert isinstance(added.integrity_hash, str)
    assert len(added.integrity_hash) == 64
    assert verify_audit_event_integrity(added) is True

    added.payload = {"text": "conteúdo adulterado"}
    assert verify_audit_event_integrity(added) is False


@pytest.mark.asyncio
async def test_audit_integrity_accepts_previous_key_during_rotation(
    fake_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_key = "a" * 40
    new_key = "b" * 40
    monkeypatch.setattr(
        "app.modules.database.application.get_settings",
        lambda: Settings(audit_integrity_key=old_key),
    )
    envelope = build_envelope("security.rotation.test", "tests", {"ok": True})
    await register_audit_event(fake_session, envelope)
    added = fake_session.add.call_args.args[0]

    monkeypatch.setattr(
        "app.modules.database.application.get_settings",
        lambda: Settings(
            audit_integrity_key=new_key,
            audit_integrity_previous_keys=[old_key],
        ),
    )
    assert verify_audit_event_integrity(added) is True
