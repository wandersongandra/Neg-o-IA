"""Prova E2E da Foundation contra FastAPI, PostgreSQL e Redis reais.

Execute com a API em processo separado e:
`SOPHIE_RUNTIME_BASE_URL`, `NEGAO_TEST_DATABASE_URL` e
`NEGAO_TEST_REDIS_URL` definidos.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("SOPHIE_RUNTIME_BASE_URL")
DATABASE_URL = os.environ.get("NEGAO_TEST_DATABASE_URL")
REDIS_URL = os.environ.get("NEGAO_TEST_REDIS_URL")


def _require_runtime() -> tuple[str, str, str]:
    if not BASE_URL or not DATABASE_URL or not REDIS_URL:
        pytest.skip(
            "runtime E2E requer SOPHIE_RUNTIME_BASE_URL, "
            "NEGAO_TEST_DATABASE_URL e NEGAO_TEST_REDIS_URL"
        )
    return BASE_URL, DATABASE_URL, REDIS_URL


async def _read_db_session(session_id: str) -> dict[str, Any]:
    _, database_url, _ = _require_runtime()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT user_id, revoked_at, expires_at "
                    "FROM identity.sessions WHERE id = :session_id"
                ),
                {"session_id": session_id},
            )
            row = result.mappings().one()
            return dict(row)
    finally:
        await engine.dispose()


async def _expire_db_session(session_id: str) -> None:
    _, database_url, _ = _require_runtime()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE identity.sessions "
                    "SET expires_at = now() - interval '1 minute' "
                    "WHERE id = :session_id"
                ),
                {"session_id": session_id},
            )
    finally:
        await engine.dispose()


async def _read_redis_conversation(session_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _, _, redis_url = _require_runtime()
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        meta_raw = await redis.get(f"conv:{session_id}:meta")
        messages_raw = await redis.get(f"conv:{session_id}:messages")
        assert meta_raw is not None
        assert messages_raw is not None
        return json.loads(meta_raw), json.loads(messages_raw)
    finally:
        close = cast(Callable[[], Awaitable[None]], redis.aclose)  # type: ignore[attr-defined]
        await close()


@pytest.mark.asyncio
async def test_foundation_runtime_auth_ownership_and_revocation() -> None:
    base_url, _, _ = _require_runtime()
    suffix = uuid.uuid4().hex[:10]
    password_a = "A-runtime-password-2026!"
    password_b = "B-runtime-password-2026!"
    username_a = f"foundation-a-{suffix}"
    username_b = f"foundation-b-{suffix}"

    async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
        no_session = await client.get("/security/status")
        assert no_session.status_code == 401
        assert "traceback" not in no_session.text.lower()

        register_a = await client.post(
            "/security/register",
            json={
                "username": username_a,
                "password": password_a,
                "display_name": "Foundation A",
            },
        )
        register_b = await client.post(
            "/security/register",
            json={
                "username": username_b,
                "password": password_b,
                "display_name": "Foundation B",
            },
        )
        assert register_a.status_code == 201, register_a.text
        assert register_b.status_code == 201, register_b.text
        user_a = register_a.json()["user_id"]
        user_b = register_b.json()["user_id"]

        login_a = await client.post(
            "/security/login",
            json={
                "username": username_a,
                "password": password_a,
                "device_name": "Foundation Browser A",
                "device_type": "web",
            },
        )
        login_b = await client.post(
            "/security/login",
            json={
                "username": username_b,
                "password": password_b,
                "device_name": "Foundation Browser B",
                "device_type": "web",
            },
        )
        assert login_a.status_code == 200, login_a.text
        assert login_b.status_code == 200, login_b.text
        cookie = login_a.headers["set-cookie"].lower()
        assert "sophie_session=" in cookie
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        token_a = login_a.json()["access_token"]
        token_b = login_b.json()["access_token"]

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        async with httpx.AsyncClient(
            base_url=base_url,
            cookies={"sophie_session": token_a},
            timeout=15.0,
        ) as cookie_client:
            cookie_status = await cookie_client.get("/security/status")
        assert cookie_status.status_code == 200, cookie_status.text
        assert cookie_status.json()["user_id"] == user_a
        status_a = await client.get("/security/status", headers=headers_a)
        status_b = await client.get("/security/status", headers=headers_b)
        assert status_a.status_code == 200
        assert status_b.status_code == 200
        assert status_a.json()["user_id"] == user_a
        assert status_b.json()["user_id"] == user_b
        session_id_a = status_a.json()["session_id"]
        session_id_b = status_b.json()["session_id"]
        db_session_a = await _read_db_session(session_id_a)
        assert str(db_session_a["user_id"]) == user_a
        assert db_session_a["revoked_at"] is None

        created = await client.post(
            "/conversation/sessions",
            headers=headers_a,
            json={"user_id": user_b},
        )
        assert created.status_code == 200, created.text
        conversation_id = created.json()["session_id"]
        assert created.json()["user_id"] == user_a

        sent = await client.post(
            f"/conversation/sessions/{conversation_id}/messages",
            headers=headers_a,
            json={"text": "foundation-runtime-persistence-marker"},
        )
        assert sent.status_code == 200, sent.text
        assert sent.headers.get("x-request-id")
        history = await client.get(
            f"/conversation/sessions/{conversation_id}/messages",
            headers=headers_a,
        )
        assert history.status_code == 200
        assert any(
            item["content"] == "foundation-runtime-persistence-marker"
            for item in history.json()["messages"]
        )

        meta, redis_messages = await _read_redis_conversation(conversation_id)
        assert meta["user_id"] == user_a
        assert any(
            item["content"] == "foundation-runtime-persistence-marker" for item in redis_messages
        )

        cross_read = await client.get(
            f"/conversation/sessions/{conversation_id}/messages",
            headers=headers_b,
        )
        cross_write = await client.patch(
            f"/conversation/sessions/{conversation_id}",
            headers=headers_b,
            json={"name": "cross-user-write"},
        )
        cross_delete = await client.delete(
            f"/conversation/sessions/{conversation_id}",
            headers=headers_b,
        )
        assert cross_read.status_code == 404
        assert cross_write.status_code == 404
        assert cross_delete.status_code == 404

        own_b = await client.post(
            "/conversation/sessions",
            headers=headers_b,
            json={"user_id": user_a},
        )
        assert own_b.status_code == 200
        assert own_b.json()["user_id"] == user_b

        await _expire_db_session(session_id_a)
        expired = await client.get("/security/status", headers=headers_a)
        assert expired.status_code == 401

        logout_b = await client.post("/security/logout", headers=headers_b)
        assert logout_b.status_code == 204
        revoked_row = await _read_db_session(session_id_b)
        assert revoked_row["revoked_at"] is not None
        replay_b = await client.get("/security/status", headers=headers_b)
        assert replay_b.status_code == 401
