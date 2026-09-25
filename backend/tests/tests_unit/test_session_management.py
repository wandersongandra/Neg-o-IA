"""Testes dos controles operacionais de sessão."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.modules.security.domain import AuthorizationLevel, AuthResult
from app.modules.security.router import (
    active_sessions,
    revoke_named_session,
    revoke_other_sessions_endpoint,
)


def _auth() -> AuthResult:
    return AuthResult(
        authenticated=True,
        principal="11111111-1111-1111-1111-111111111111",
        user_id="11111111-1111-1111-1111-111111111111",
        session_id="22222222-2222-2222-2222-222222222222",
        authorization_level=AuthorizationLevel.READ_ONLY,
        auth_method="session",
    )


@pytest.mark.asyncio
async def test_active_sessions_marks_current_session(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    record_type = type(
        "Record",
        (),
        {
            "session_id": "22222222-2222-2222-2222-222222222222",
            "device_id": "33333333-3333-3333-3333-333333333333",
            "device_name": "Notebook",
            "device_type": "web",
            "created_at": now - timedelta(minutes=10),
            "last_seen_at": now,
            "expires_at": now + timedelta(hours=1),
        },
    )

    async def fake_list(user_id: str):
        assert user_id == _auth().user_id
        return [record_type()]

    monkeypatch.setattr(
        "app.modules.security.router.list_bearer_sessions",
        fake_list,
    )
    result = await active_sessions(_auth())
    assert len(result) == 1
    assert result[0].current is True
    assert result[0].device_name == "Notebook"


@pytest.mark.asyncio
async def test_named_session_rejects_current_session() -> None:
    auth = _auth()
    with pytest.raises(HTTPException) as exc_info:
        await revoke_named_session(auth.session_id or "", auth)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_revoke_other_sessions_returns_count(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_revoke(user_id: str, session_id: str) -> int:
        assert user_id == _auth().user_id
        assert session_id == _auth().session_id
        return 3

    monkeypatch.setattr(
        "app.modules.security.router.revoke_other_bearer_sessions",
        fake_revoke,
    )
    result = await revoke_other_sessions_endpoint(_auth())
    assert result == {"revoked": 3}
