"""Testes unitários do ticket de autenticação WebSocket (security.infrastructure)."""

from __future__ import annotations

from typing import Any

import pytest
from fakeredis import FakeAsyncRedis

from app.modules.security.domain import AuthorizationLevel
from app.modules.security.infrastructure import issue_ws_ticket, redeem_ws_ticket


@pytest.fixture
def fake_redis(monkeypatch: Any) -> FakeAsyncRedis:
    client = FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr("app.infrastructure.redis.get_redis", lambda: client)
    return client


async def test_ticket_roundtrip(fake_redis: FakeAsyncRedis) -> None:
    token = await issue_ws_ticket("api_key", AuthorizationLevel.READ_ONLY)
    result = await redeem_ws_ticket(token)
    assert result.authenticated is True
    assert result.principal == "api_key"
    assert result.authorization_level is AuthorizationLevel.READ_ONLY


async def test_voice_ticket_binds_purpose_and_session(fake_redis: FakeAsyncRedis) -> None:
    token = await issue_ws_ticket(
        "user-test",
        AuthorizationLevel.READ_ONLY,
        purpose="voice",
        session_id="session-1",
    )
    result = await redeem_ws_ticket(token, expected_purpose="voice")
    assert result.authenticated is True
    assert result.purpose == "voice"
    assert result.session_id == "session-1"


async def test_voice_ticket_requires_session(fake_redis: FakeAsyncRedis) -> None:
    with pytest.raises(ValueError, match="requires a session"):
        await issue_ws_ticket("user-test", AuthorizationLevel.READ_ONLY, purpose="voice")


async def test_ticket_purpose_mismatch_is_rejected(fake_redis: FakeAsyncRedis) -> None:
    token = await issue_ws_ticket("user-test", AuthorizationLevel.READ_ONLY)
    result = await redeem_ws_ticket(token, expected_purpose="voice")
    assert result.authenticated is False
    assert result.reason == "ticket_purpose_mismatch"


async def test_ticket_is_single_use(fake_redis: FakeAsyncRedis) -> None:
    token = await issue_ws_ticket("api_key", AuthorizationLevel.READ_ONLY)
    first = await redeem_ws_ticket(token)
    second = await redeem_ws_ticket(token)
    assert first.authenticated is True
    assert second.authenticated is False
    assert second.reason == "invalid_or_expired_ticket"


async def test_unknown_ticket_fails(fake_redis: FakeAsyncRedis) -> None:
    result = await redeem_ws_ticket("does-not-exist")
    assert result.authenticated is False
    assert result.reason == "invalid_or_expired_ticket"


async def test_malformed_ticket_fails_closed(fake_redis: FakeAsyncRedis) -> None:
    await fake_redis.set("ws_ticket:malformed", "not-json")
    result = await redeem_ws_ticket("malformed")
    assert result.authenticated is False
    assert result.reason == "invalid_ticket_payload"


async def test_missing_ticket_fails() -> None:
    result = await redeem_ws_ticket("")
    assert result.authenticated is False
    assert result.reason == "missing_ticket"
