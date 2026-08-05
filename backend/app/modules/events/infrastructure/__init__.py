"""Implementação do Event Bus sobre Redis Streams (v0).

Garantias: entrega at-least-once com deduplicação por `id` (efetivamente
once), retry com backoff (máx. N tentativas) e dead-letter em `events:dlq`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.modules.events.domain import EventCallback, EventDeliveryStatus, EventHandler
from app.modules.events.envelope import EventEnvelope, build_envelope
from app.modules.events.events import EVENT_DLQ_RECEIVED, EVENT_PUBLISHED

_LOGGER = logging.getLogger("app.modules.events")

DLQ_STREAM = "events:dlq"
DEFAULT_GROUP = "negao-consumers"
META_EVENT_TYPES = frozenset({EVENT_PUBLISHED, EVENT_DLQ_RECEIVED})


class EventBus:
    """Barramento de eventos baseado em Redis Streams + consumer groups."""

    def __init__(
        self,
        redis_client: aioredis.Redis[str],
        *,
        group_name: str = DEFAULT_GROUP,
        consumer_name: str | None = None,
        max_delivery_attempts: int = 3,
        retry_backoff_seconds: float = 1.0,
        dedup_ttl_seconds: int = 86_400,
        poll_block_ms: int = 5_000,
        batch_size: int = 32,
    ) -> None:
        self._redis = redis_client
        self._group_name = group_name
        self._consumer_name = consumer_name or f"consumer-{uuid.uuid4().hex[:8]}"
        self._max_delivery_attempts = max_delivery_attempts
        self._retry_backoff_seconds = retry_backoff_seconds
        self._dedup_ttl_seconds = dedup_ttl_seconds
        self._poll_block_ms = poll_block_ms
        self._batch_size = batch_size
        self._handlers: dict[str, list[EventHandler]] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._active_streams: set[str] = set()
        self._stopped = False
        self._delivery_counts: dict[str, int] = {}

    @staticmethod
    def _stream_name(event_type: str) -> str:
        return f"events:{event_type}"

    def subscribe(self, event_type: str, handler: EventCallback) -> None:
        self._handlers.setdefault(event_type, []).append(
            EventHandler(event_type=event_type, callback=handler)
        )

    async def publish(self, envelope: EventEnvelope) -> None:
        stream = self._stream_name(envelope.type)
        await self._redis.xadd(stream, {"data": envelope.model_dump_json()})
        if envelope.type not in META_EVENT_TYPES:
            await self._publish_meta(envelope)
        self._count_delivery("published")

    async def _publish_meta(self, envelope: EventEnvelope) -> None:
        meta = build_envelope(
            EVENT_PUBLISHED,
            producer="events",
            payload={
                "event_id": envelope.id,
                "event_type": envelope.type,
                "producer": envelope.producer,
            },
            trace_id=envelope.trace_id,
            correlation_id=envelope.correlation_id,
            parent_id=envelope.id,
        )
        try:
            await self._xadd(meta)
        except Exception as exc:
            _LOGGER.warning(
                "falha ao publicar meta-evento",
                extra={"event_type": envelope.type, "error": str(exc)},
            )

    async def _xadd(self, envelope: EventEnvelope) -> None:
        await self._redis.xadd(
            self._stream_name(envelope.type), {"data": envelope.model_dump_json()}
        )

    def start_consumer_loop(self) -> None:
        if self._tasks:
            raise RuntimeError("EventBus: loop de consumo já iniciado")
        self._stopped = False
        for event_type in self._handlers:
            task = asyncio.create_task(
                self._consume_stream(event_type), name=f"events-consumer:{event_type}"
            )
            self._tasks.append(task)

    async def stop(self) -> None:
        self._stopped = True
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _consume_stream(self, event_type: str) -> None:
        stream = self._stream_name(event_type)
        await self._ensure_group(stream)
        _LOGGER.info(
            "consumidor iniciado",
            extra={
                "stream": stream,
                "group": self._group_name,
                "consumer": self._consumer_name,
            },
        )
        while not self._stopped:
            try:
                if await self._consume_once(event_type, stream, "0"):
                    continue
                await self._consume_once(event_type, stream, ">")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _LOGGER.warning(
                    "erro no loop de consumo",
                    extra={"stream": stream, "error": str(exc)},
                )
                await asyncio.sleep(self._retry_backoff_seconds)

    async def _ensure_group(self, stream: str) -> None:
        try:
            await self._redis.xgroup_create(
                stream, self._group_name, id="$", mkstream=True
            )
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._active_streams.add(stream)

    async def _consume_once(self, event_type: str, stream: str, message_id: str) -> bool:
        result = await self._redis.xreadgroup(
            self._group_name,
            self._consumer_name,
            streams={stream: message_id},
            count=self._batch_size,
            block=self._poll_block_ms,
        )
        if not result:
            return False
        for _stream_name, entries in result:
            for entry in entries:
                await self._dispatch(event_type, stream, entry)
        return True

    async def _dispatch(
        self,
        event_type: str,
        stream: str,
        entry: tuple[Any, dict[Any, Any]],
    ) -> None:
        message_id, fields = entry
        envelope: EventEnvelope | None = None
        try:
            raw = fields.get(b"data") or fields.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if raw is None:
                raise ValueError("campo `data` ausente no evento")
            envelope = EventEnvelope.model_validate_json(raw)
        except Exception as exc:
            _LOGGER.error(
                "evento inválido no stream",
                extra={"stream": stream, "message_id": str(message_id), "error": str(exc)},
            )
            await self._redis.xack(stream, self._group_name, message_id)  # type: ignore[no-untyped-call]
            await self._dead_letter(
                envelope,
                reason="envelope inválido",
                stream=stream,
                message_id=str(message_id),
            )
            return
        if not await self._claim_dedup(envelope.id):
            await self._redis.xack(stream, self._group_name, message_id)  # type: ignore[no-untyped-call]
            self._count_delivery(EventDeliveryStatus.SKIPPED_DUPLICATE.value)
            return
        for attempt in range(1, self._max_delivery_attempts + 1):
            try:
                for handler in self._handlers.get(event_type, ()):
                    await handler.callback(envelope)
                await self._redis.xack(stream, self._group_name, message_id)  # type: ignore[no-untyped-call]
                self._count_delivery(EventDeliveryStatus.DELIVERED.value)
                return
            except Exception as exc:
                _LOGGER.warning(
                    "falha no handler do evento",
                    extra={
                        "event_type": envelope.type,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                if attempt < self._max_delivery_attempts:
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)
        await self._redis.xack(stream, self._group_name, message_id)  # type: ignore[no-untyped-call]
        await self._dead_letter(
            envelope,
            reason="handler falhou após tentativas",
            stream=stream,
            message_id=str(message_id),
        )
        self._count_delivery(EventDeliveryStatus.DEAD_LETTERED.value)

    async def _claim_dedup(self, event_id: str) -> bool:
        key = f"event:dedup:{event_id}"
        return await self._redis.set(key, "1", ex=self._dedup_ttl_seconds, nx=True) is not None

    async def _dead_letter(
        self,
        envelope: EventEnvelope | None,
        *,
        reason: str,
        stream: str,
        message_id: str,
    ) -> None:
        payload: dict[str, Any] = {
            "original_stream": stream,
            "original_message_id": message_id,
            "reason": reason,
        }
        if envelope is not None:
            payload.update(
                {
                    "event_id": envelope.id,
                    "event_type": envelope.type,
                    "producer": envelope.producer,
                }
            )
        await self._redis.xadd(DLQ_STREAM, {"data": json.dumps(payload, ensure_ascii=False)})
        notice = build_envelope(
            EVENT_DLQ_RECEIVED,
            producer="events",
            payload=payload,
            trace_id=envelope.trace_id if envelope else None,
            correlation_id=envelope.correlation_id if envelope else None,
            parent_id=envelope.id if envelope else None,
        )
        try:
            await self._xadd(notice)
        except Exception as exc:
            _LOGGER.warning(
                "falha ao notificar evento na DLQ",
                extra={"error": str(exc)},
            )

    def _count_delivery(self, status: str) -> None:
        self._delivery_counts[status] = self._delivery_counts.get(status, 0) + 1

    @property
    def is_available(self) -> bool:
        return not self._stopped

    @property
    def status(self) -> dict[str, Any]:
        return {
            "consumer_group": self._group_name,
            "consumer_name": self._consumer_name,
            "active_streams": sorted(self._active_streams),
            "handlers": {
                event_type: len(handlers) for event_type, handlers in self._handlers.items()
            },
            "deliveries": dict(sorted(self._delivery_counts.items())),
            "max_delivery_attempts": self._max_delivery_attempts,
        }
