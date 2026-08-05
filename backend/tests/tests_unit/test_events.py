"""Testes unitários do módulo events (envelope + barramento sobre fakeredis)."""

from __future__ import annotations

import pytest
from fakeredis import FakeAsyncRedis
from pydantic import ValidationError

from app.modules.events.application import EventBusService
from app.modules.events.envelope import EventEnvelope, build_envelope
from app.modules.events.infrastructure import EventBus

EVENT_TYPE = "test.unit.event"


@pytest.fixture
def redis_client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


def test_build_envelope_preenche_id_occurred_at_e_version() -> None:
    envelope = build_envelope(EVENT_TYPE, "tests", {"ok": True})
    assert envelope.id
    assert envelope.occurred_at
    assert envelope.version == 1
    assert envelope.type == EVENT_TYPE
    assert envelope.producer == "tests"
    assert envelope.payload == {"ok": True}


def test_envelope_rejeita_campos_extra() -> None:
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(
            {"type": EVENT_TYPE, "producer": "tests", "campo_inesperado": True}
        )


def test_envelope_roundtrip_json() -> None:
    envelope = build_envelope(
        EVENT_TYPE,
        "tests",
        {"n": 1},
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    restored = EventEnvelope.model_validate_json(envelope.model_dump_json())
    assert restored == envelope


@pytest.mark.asyncio
async def test_publish_grava_no_stream(redis_client: FakeAsyncRedis) -> None:
    bus = EventBus(redis_client=redis_client)
    await bus.publish(build_envelope(EVENT_TYPE, "tests"))
    length = await redis_client.xlen(f"events:{EVENT_TYPE}")
    assert length > 0


@pytest.mark.asyncio
async def test_subscribe_e_publish_entrega_envelope(
    redis_client: FakeAsyncRedis,
) -> None:
    bus = EventBus(redis_client=redis_client)
    service = EventBusService(bus)
    received: list[EventEnvelope] = []

    async def handler(envelope: EventEnvelope) -> None:
        received.append(envelope)

    service.register_handler(EVENT_TYPE, handler)
    envelope = build_envelope(EVENT_TYPE, "tests", {"msg": "oi"})
    stream = bus._stream_name(EVENT_TYPE)
    await bus._ensure_group(stream)
    await service.publish_event(envelope)

    delivered = await bus._consume_once(EVENT_TYPE, stream, ">")
    assert delivered is True
    assert received == [envelope]


@pytest.mark.asyncio
async def test_dedup_entrega_mesmo_envelope_apenas_uma_vez(
    redis_client: FakeAsyncRedis,
) -> None:
    bus = EventBus(redis_client=redis_client)
    service = EventBusService(bus)
    calls = 0

    async def handler(envelope: EventEnvelope) -> None:
        nonlocal calls
        calls += 1

    service.register_handler(EVENT_TYPE, handler)
    envelope = build_envelope(EVENT_TYPE, "tests", {"dup": True})
    stream = bus._stream_name(EVENT_TYPE)
    await bus._ensure_group(stream)
    await service.publish_event(envelope)
    await service.publish_event(envelope)

    await bus._consume_once(EVENT_TYPE, stream, ">")
    await bus._consume_once(EVENT_TYPE, stream, "0")
    assert calls == 1
