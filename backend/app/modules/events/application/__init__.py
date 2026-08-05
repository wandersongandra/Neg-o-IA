"""Camada de aplicação do módulo events — EventBusService (facade).

Único ponto de acesso dos módulos ao barramento: publish/register/start/stop.
"""

from __future__ import annotations

from typing import Any

from app.modules.events.domain import EventCallback
from app.modules.events.envelope import EventEnvelope
from app.modules.events.infrastructure import EventBus

_event_bus_service: EventBusService | None = None


class EventBusService:
    """Facade pública do barramento de eventos."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def publish_event(self, envelope: EventEnvelope) -> None:
        await self._bus.publish(envelope)

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

        _event_bus_service = EventBusService(EventBus(redis_client=get_redis()))
    return _event_bus_service
