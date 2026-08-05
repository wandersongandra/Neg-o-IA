"""Testes unitários do módulo conversation — store, service e WebSocket."""

from __future__ import annotations

from typing import Any

import pytest
from fakeredis import FakeAsyncRedis
from starlette.testclient import TestClient

from app.modules.conversation.application import (
    ConversationService,
)
from app.modules.conversation.domain import ConversationMessage
from app.modules.conversation.infrastructure import ConversationStore

SESSION_ID = "abcdef1234567890"


@pytest.fixture
def fake_redis(monkeypatch: Any) -> FakeAsyncRedis:
    client = FakeAsyncRedis()

    async def _get_redis() -> FakeAsyncRedis:
        return client

    monkeypatch.setattr(
        "app.infrastructure.redis.get_redis", _get_redis
    )
    return client


@pytest.fixture
def store(fake_redis: FakeAsyncRedis) -> ConversationStore:
    return ConversationStore(redis_client=fake_redis)


async def test_store_start_session_creates_empty_session(store: ConversationStore) -> None:
    session = await store.start_session(user_id=None)
    assert session.session_id
    assert session.message_count == 0
    assert await store.get_messages(session.session_id) == []


async def test_store_append_and_read_messages(store: ConversationStore) -> None:
    session = await store.start_session(user_id="wanderson")
    await store.append_message(session.session_id, "user", "olá")
    await store.append_message(session.session_id, "assistant", "e aí, chefe!")
    messages = await store.get_messages(session.session_id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "olá"
    assert messages[1].role == "assistant"


async def test_store_limits_history_to_max(store: ConversationStore, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "app.modules.conversation.infrastructure.MAX_MESSAGES", 5
    )
    session = await store.start_session(user_id=None)
    for i in range(8):
        await store.append_message(session.session_id, "user", f"msg {i}")
    messages = await store.get_messages(session.session_id)
    assert len(messages) == 5
    assert messages[-1].content == "msg 7"


async def test_store_rename_session(store: ConversationStore) -> None:
    session = await store.start_session(user_id="wanderson")
    ok = await store.rename_session(session.session_id, "Minha Sessão")
    assert ok is True
    sessions = await store.list_sessions()
    s = next(s for s in sessions if s.session_id == session.session_id)
    assert s.name == "Minha Sessão"

    ok = await store.rename_session(session.session_id, None)
    assert ok is True
    sessions = await store.list_sessions()
    s = next(s for s in sessions if s.session_id == session.session_id)
    assert s.name is None


async def test_store_rename_nonexistent_returns_false(store: ConversationStore) -> None:
    ok = await store.rename_session("nao-existe", "x")
    assert ok is False


async def test_store_delete_session(store: ConversationStore) -> None:
    session = await store.start_session(user_id="wanderson")
    await store.append_message(session.session_id, "user", "oi")
    ok = await store.delete_session(session.session_id)
    assert ok is True
    sessions = await store.list_sessions()
    assert all(s.session_id != session.session_id for s in sessions)
    messages = await store.get_messages(session.session_id)
    assert messages == []


async def test_store_delete_nonexistent_returns_false(store: ConversationStore) -> None:
    ok = await store.delete_session("nao-existe")
    assert ok is False


async def test_store_list_sessions(store: ConversationStore) -> None:
    s1 = await store.start_session(user_id="a")
    s2 = await store.start_session(user_id="b")
    await store.append_message(s1.session_id, "user", "oi")
    sessions = await store.list_sessions()
    ids = {s.session_id for s in sessions}
    assert s1.session_id in ids
    assert s2.session_id in ids


class FakeBrain:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def complete(self, messages: Any, **kwargs: Any) -> Any:
        self.calls.append((messages, kwargs))
        return type(
            "Resp",
            (),
            {
                "text": "Resposta do NEGÃO",
                "model": "nvidia/gpt-oss-120b",
                "latency_ms": 120,
                "fallback_used": False,
                "cached": False,
            },
        )()


class FakeBus:
    def __init__(self) -> None:
        self.published: list[Any] = []

    async def publish_event(self, envelope: Any) -> None:
        self.published.append(envelope)


async def test_service_chat_persists_and_publishes(
    store: ConversationStore, monkeypatch: Any
) -> None:
    brain = FakeBrain()
    bus = FakeBus()
    monkeypatch.setattr(
        "app.modules.brain.application.get_brain_service", lambda: brain
    )
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service", lambda: bus
    )
    service = ConversationService(store=store)
    session = await service.start_session(user_id="wanderson")
    result = await service.chat(session.session_id, "bom dia")
    assert result.text == "Resposta do NEGÃO"
    messages = await store.get_messages(session.session_id)
    assert [m.role for m in messages] == ["user", "assistant"]
    types = {e.type for e in bus.published}
    assert "conversation.started" in types
    assert "conversation.message.stored" in types
    assert "conversation.message.responded" in types
    context = await service.get_context(session.session_id)
    assert context[0].role == "system"


async def test_service_chat_graceful_on_brain_error(
    store: ConversationStore, monkeypatch: Any
) -> None:
    class BrokenBrain:
        async def complete(self, messages: Any, **kwargs: Any) -> Any:
            raise RuntimeError("LLM fora")

    monkeypatch.setattr(
        "app.modules.brain.application.get_brain_service", lambda: BrokenBrain()
    )
    service = ConversationService(store=store)
    session = await service.start_session(user_id=None)
    result = await service.chat(session.session_id, "oi")
    assert result.model == "error"
    assert "engasgada" in result.text
    messages = await store.get_messages(session.session_id)
    assert [m.role for m in messages] == ["user"]


async def test_ws_conversation_flow(store: ConversationStore, monkeypatch: Any) -> None:
    from app.main import create_app

    class FakeService:
        async def start_session(self, user_id: str | None = None) -> Any:
            return type(
                "Session",
                (),
                {
                    "session_id": SESSION_ID,
                    "user_id": user_id,
                    "created_at": "",
                    "message_count": 0,
                },
            )()

        async def chat(self, session_id: str, text: str, **kwargs: Any) -> Any:
            return type(
                "ChatResult",
                (),
                {
                    "text": "Olá, chefe! Tudo pronto por aqui.",
                    "model": "test-model",
                    "latency_ms": 10,
                    "fallback_used": False,
                    "cached": False,
                },
            )()

        async def reset_session(self, session_id: str) -> None:
            return None

    monkeypatch.setattr(
        "app.modules.conversation.router.get_conversation_service",
        lambda: FakeService(),
    )
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/conversation?api_key=negao-dev-api-key"
        ) as ws:
            ws.send_json({"type": "chat", "text": "e aí?"})
            received = []
            while True:
                msg = ws.receive_json()
                received.append(msg)
                if msg.get("type") == "done":
                    break
            types = [m["type"] for m in received]
            assert "tokens" in types
            done = received[-1]
            assert done["type"] == "done"
            assert done["session_id"] == SESSION_ID
            assert "Olá" in done["text"]


async def test_ws_conversation_rejects_missing_key() -> None:
    from starlette.websockets import WebSocketDisconnect

    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws/conversation") as ws:
                ws.receive_json()
        assert exc.value.code == 1008


def test_domain_message_validation() -> None:
    with pytest.raises(ValueError):
        ConversationMessage(role="foo", content="x", created_at="")
    with pytest.raises(ValueError):
        ConversationMessage(role="user", content="   ", created_at="")
