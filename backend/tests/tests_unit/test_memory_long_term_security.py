"""Security tests for long-term memory retention and automatic capture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.core.sensitive_content import contains_likely_secret, likely_secret_kind
from app.modules.memory.application.long_term import LongTermMemoryService
from app.modules.memory.domain import LongTermMemoryEntry, MemoryPolicy


class _FakeLongTermStore:
    def __init__(self) -> None:
        self.purge_calls: list[str] = []
        self.remembered: list[str] = []
        self.policy = MemoryPolicy(
            user_id="user-1",
            auto_capture_enabled=True,
            retention_days=30,
        )

    async def purge_expired(self, user_id: str) -> int:
        self.purge_calls.append(user_id)
        return 2

    async def get_policy(self, user_id: str) -> MemoryPolicy:
        return MemoryPolicy(
            user_id=user_id,
            auto_capture_enabled=self.policy.auto_capture_enabled,
            retention_days=self.policy.retention_days,
        )

    async def remember(
        self,
        user_id: str,
        content: str,
        *,
        session_id: str | None,
        source: str,
        importance: float,
        retention_days: int | None,
        metadata: dict[str, Any],
    ) -> LongTermMemoryEntry:
        self.remembered.append(content)
        now = datetime.now(UTC)
        return LongTermMemoryEntry(
            id="memory-1",
            user_id=user_id,
            session_id=session_id,
            source=source,
            content=content,
            importance=importance,
            metadata=metadata,
            created_at=now,
            expires_at=None,
        )


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Authorization: Bearer " + ("a" * 32), "authorization_bearer"),
        ("eyJ" + ("a" * 12) + "." + ("b" * 16) + "." + ("c" * 16), "jwt"),
        ("github_pat_" + ("x" * 32), "known_token_prefix"),
        (
            "postgresql://admin:" + ("p" * 20) + "@db.invalid:5432/app",
            "credential_uri",
        ),
        ("api_" + "key=" + ("k" * 28), "credential_assignment"),
        ("-----BEGIN " + "PRIVATE KEY-----\nsynthetic", "private_key"),
    ],
)
def test_high_confidence_secret_patterns_are_detected(content: str, expected: str) -> None:
    assert likely_secret_kind(content) == expected
    assert contains_likely_secret(content) is True


def test_normal_conversation_is_not_flagged_as_secret() -> None:
    content = "Quero lembrar que minha comida favorita é pizza e minha senha deve ser forte."
    assert likely_secret_kind(content) is None
    assert contains_likely_secret(content) is False


@pytest.mark.asyncio
async def test_auto_capture_skips_secret_and_never_sends_it_to_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _FakeLongTermStore()
    service = LongTermMemoryService(store)  # type: ignore[arg-type]
    publish = AsyncMock()
    monkeypatch.setattr(service, "_publish", publish)
    secret = "Authorization: Bearer " + ("z" * 32)

    result = await service.maybe_capture_conversation("user-1", "session-1", secret)

    assert result is None
    assert store.remembered == []
    assert store.purge_calls == ["user-1"]
    event_call = next(
        call
        for call in publish.await_args_list
        if call.args[0] == "memory.long_term.auto_capture_skipped_sensitive"
    )
    assert event_call.args[1]["reason"] == "authorization_bearer"
    assert secret not in repr(event_call)


@pytest.mark.asyncio
async def test_auto_capture_stores_normal_content_after_purge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _FakeLongTermStore()
    service = LongTermMemoryService(store)  # type: ignore[arg-type]
    monkeypatch.setattr(service, "_publish", AsyncMock())
    content = "Meu editor preferido é o VS Code e eu uso tema escuro."

    result = await service.maybe_capture_conversation("user-1", "session-1", content)

    assert result is not None
    assert store.remembered == [content]
    assert store.purge_calls == ["user-1", "user-1"]


@pytest.mark.asyncio
async def test_manual_memory_remains_explicitly_allowed_for_user_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _FakeLongTermStore()
    service = LongTermMemoryService(store)  # type: ignore[arg-type]
    monkeypatch.setattr(service, "_publish", AsyncMock())
    explicit_content = "api_" + "key=" + ("q" * 28)

    result = await service.remember(
        "user-1",
        explicit_content,
        source="manual",
    )

    assert result.content == explicit_content
    assert store.remembered == [explicit_content]
    assert store.purge_calls == ["user-1"]
