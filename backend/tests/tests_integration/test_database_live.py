"""Testes de integração do módulo Database (PostgreSQL real).

Pulados automaticamente se NEGAO_TEST_DATABASE_URL não estiver definido:
    $env:NEGAO_TEST_DATABASE_URL="postgresql+asyncpg://negao:negao@localhost:5432/negao_test"
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.modules.database.application import (
    create_api_key,
    list_audit_events,
    register_audit_event,
    verify_api_key,
)
from app.modules.events.envelope import build_envelope

pytestmark = pytest.mark.integration

TEST_URL = os.environ.get("NEGAO_TEST_DATABASE_URL")


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine]:
    if not TEST_URL:
        pytest.skip("NEGAO_TEST_DATABASE_URL não definido; pulando integração")
    engine = create_async_engine(TEST_URL)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_roundtrip_api_key_and_audit(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: sync_conn.execute(
                    __import__("sqlalchemy").text(
                        "SELECT 1 FROM events.audit_events LIMIT 1"
                    )
                )
            )

        plain_key, record = await create_api_key(session, "integration-test", ["read"])
        assert plain_key and record.name == "integration-test"

        verified = await verify_api_key(session, plain_key)
        assert verified is not None and verified.revoked_at is None

        envelope = build_envelope("integration.test.event", "tests", {"ok": True})
        saved = await register_audit_event(session, envelope)
        assert saved.event_type == "integration.test.event"

        events = await list_audit_events(session, limit=5)
        assert any(event.event_type == "integration.test.event" for event in events)
