"""Camada de aplicação do módulo events — EventBusService (facade).

Único ponto de acesso dos módulos ao barramento: publish/register/start/stop.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.modules.events.domain import EventCallback
from app.modules.events.envelope import EventEnvelope
from app.modules.events.infrastructure import EventBus

_LOGGER = logging.getLogger("app.modules.events.application")
_event_bus_service: EventBusService | None = None


AuditPersister = Callable[[EventEnvelope], Awaitable[None]]


async def _persist_audit_event(envelope: EventEnvelope) -> None:
    from app.infrastructure.db import create_engine, create_session_factory
    from app.modules.configuration.settings import get_settings
    from app.modules.database.application import register_audit_event

    factory = create_session_factory(create_engine(get_settings().database_url))
    async with factory() as session:
        await register_audit_event(session, envelope)
        await session.commit()


class EventBusService:
    """Facade pública do barramento de eventos."""

    def __init__(
        self,
        bus: EventBus,
        audit_persister: AuditPersister | None = None,
    ) -> None:
        self._bus = bus
        self._audit_persister = audit_persister

    async def publish_event(self, envelope: EventEnvelope) -> None:
        """Publica no stream e persiste auditoria; uma dependência não mascara a outra."""
        persisted = False
        streamed = False
        try:
            if self._audit_persister is not None:
                await self._audit_persister(envelope)
                persisted = True
        except Exception:
            _LOGGER.warning(
                "audit_event_persistence_failed",
                extra={"event_type": envelope.type, "event_id": envelope.id},
                exc_info=True,
            )
        try:
            await self._bus.publish(envelope)
            streamed = True
        except Exception:
            _LOGGER.warning(
                "event_stream_publish_failed",
                extra={"event_type": envelope.type, "event_id": envelope.id},
                exc_info=True,
            )
        if not persisted and not streamed:
            raise RuntimeError("event could not be persisted or published")

    def register_handler(self, event_type: str, handler: EventCallback) -> None:
        self._bus.subscribe(event_type, handler)

    async def start(self) -> None:
        self._bus.start_consumer_loop()

    async def stop(self) -> None:
        await self._bus.stop()

    @property
    def status(self) -> dict[str, Any]:
        return self._bus.status

    @property
    def is_available(self) -> bool:
        return self._bus.is_available


def get_event_bus_service() -> EventBusService:
    """Singleton do EventBusService (redis obtido via app.infrastructure.redis)."""
    global _event_bus_service
    if _event_bus_service is None:
        from app.infrastructure.redis import get_redis

        from app.modules.configuration.settings import get_settings

        audit_persister = None if get_settings().env == "test" else _persist_audit_event
        _event_bus_service = EventBusService(
            EventBus(redis_client=get_redis()), audit_persister=audit_persister
        )
    return _event_bus_service
