"""Testes unitários da memória isolada por usuário e sessão."""

from __future__ import annotations

import pytest
from fakeredis import FakeAsyncRedis

from app.modules.events.envelope import EventEnvelope
from app.modules.memory.application import MemoryService
from app.modules.memory.infrastructure import RedisShortTermMemory


class _NoopEventBusService:
    async def publish_event(self, envelope: EventEnvelope) -> None:
        return None


@pytest.fixture
def redis_client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_set_e_get_roundtrip(redis_client: FakeAsyncRedis) -> None:
    store = RedisShortTermMemory(redis_client)
    await store.set("user-1", "sess-1", "ctx", {"perfil": "analista"}, ttl=60)

    entry = await store.get("user-1", "sess-1", "ctx")
    assert entry is not None
    assert entry.user_id == "user-1"
    assert entry.value == {"perfil": "analista"}
    assert entry.expires_at > entry.created_at


@pytest.mark.asyncio
async def test_memoria_isolada_por_usuario(redis_client: FakeAsyncRedis) -> None:
    store = RedisShortTermMemory(redis_client)
    await store.set("user-a", "sess-1", "secret", "A")
    await store.set("user-b", "sess-1", "secret", "B")

    assert (await store.get("user-a", "sess-1", "secret")).value == "A"  # type: ignore[union-attr]
    assert (await store.get("user-b", "sess-1", "secret")).value == "B"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_get_chave_inexistente_retorna_none(redis_client: FakeAsyncRedis) -> None:
    store = RedisShortTermMemory(redis_client)
    assert await store.get("user-1", "sess-1", "ausente") is None


@pytest.mark.asyncio
async def test_delete_remove_e_retorna_true(redis_client: FakeAsyncRedis) -> None:
    store = RedisShortTermMemory(redis_client)
    await store.set("user-1", "sess-1", "k", "v")

    assert await store.delete("user-1", "sess-1", "k") is True
    assert await store.get("user-1", "sess-1", "k") is None
    assert await store.delete("user-1", "sess-1", "k") is False


@pytest.mark.asyncio
async def test_list_keys_retorna_apenas_sufixos_da_sessao(
    redis_client: FakeAsyncRedis,
) -> None:
    store = RedisShortTermMemory(redis_client)
    await store.set("user-1", "sess-a", "alpha", 1)
    await store.set("user-1", "sess-a", "beta", 2)
    await store.set("user-1", "sess-b", "gama", 3)

    assert sorted(await store.list_keys("user-1", "sess-a")) == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_flush_session_nao_afeta_outra_sessao_ou_usuario(
    redis_client: FakeAsyncRedis,
) -> None:
    store = RedisShortTermMemory(redis_client)
    await store.set("user-1", "sess-a", "x", 1)
    await store.set("user-1", "sess-a", "y", 2)
    await store.set("user-1", "sess-b", "z", 3)
    await store.set("user-2", "sess-a", "z", 4)

    removed = await store.flush_session("user-1", "sess-a")
    assert removed == 2
    assert await store.list_keys("user-1", "sess-a") == []
    assert await store.list_keys("user-1", "sess-b") == ["z"]
    assert await store.list_keys("user-2", "sess-a") == ["z"]


@pytest.mark.asyncio
async def test_set_aplica_ttl(redis_client: FakeAsyncRedis) -> None:
    store = RedisShortTermMemory(redis_client)
    await store.set("user-1", "sess-1", "k", "v", ttl=60)

    ttl = await redis_client.ttl("stm:user-1:sess-1:k")
    assert ttl > 0


@pytest.mark.asyncio
async def test_memory_service_record_e_recall(
    redis_client: FakeAsyncRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MemoryService(RedisShortTermMemory(redis_client))
    monkeypatch.setattr(
        "app.modules.events.application.get_event_bus_service",
        lambda: _NoopEventBusService(),
    )

    await service.record_session_data("user-1", "srv-1", "cargo", {"funcao": "analista"})
    await service.record_session_data("user-1", "srv-1", "nome", "Ada")

    assert await service.recall_session("user-1", "srv-1") == {
        "cargo": {"funcao": "analista"},
        "nome": "Ada",
    }
