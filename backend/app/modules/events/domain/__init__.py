"""Contratos do módulo events — domain (framework-free).

Ports e tipos do barramento: registro de handlers e status de entrega.
O envelope global (EventEnvelope/build_envelope) vive em
`app.modules.events.envelope` e é o contrato único do sistema.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum

from app.modules.events.envelope import EventEnvelope

EventCallback = Callable[[EventEnvelope], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class EventHandler:
    """Registro de um consumidor: tipo de evento e callback assíncrono."""

    event_type: str
    callback: EventCallback


class EventDeliveryStatus(Enum):
    """Resultado da entrega de um evento a um handler."""

    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    DEAD_LETTERED = "dead_lettered"
