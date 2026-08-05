"""Contrato de eventos do módulo brain — catálogo v1 (Event Bus).

Producer deste módulo: "brain".
"""

from __future__ import annotations

from typing import Final

EVENT_VERSION = 1

EVENT_BRAIN_REQUEST_STARTED: Final[str] = "brain.request.started"
EVENT_BRAIN_REQUEST_COMPLETED: Final[str] = "brain.request.completed"
EVENT_BRAIN_MODEL_FALLBACK: Final[str] = "brain.model.fallback"
EVENT_BRAIN_MODEL_ERROR: Final[str] = "brain.model.error"

EVENT_CATALOG: Final[dict[str, str]] = {
    EVENT_BRAIN_REQUEST_STARTED: (
        "Pedido recebido pelo Brain (modelo, tamanho do contexto, sessão)"
    ),
    EVENT_BRAIN_REQUEST_COMPLETED: (
        "Resposta concluída pelo Brain com modelo, latência e uso de fallback/cache"
    ),
    EVENT_BRAIN_MODEL_FALLBACK: (
        "O modelo primário falhou e a resposta veio do modelo de fallback"
    ),
    EVENT_BRAIN_MODEL_ERROR: (
        "Todos os provedores de modelo falharam para este pedido"
    ),
}

PUBLISHED: Final[frozenset[str]] = frozenset(
    {
        EVENT_BRAIN_REQUEST_STARTED,
        EVENT_BRAIN_REQUEST_COMPLETED,
        EVENT_BRAIN_MODEL_FALLBACK,
        EVENT_BRAIN_MODEL_ERROR,
    }
)

CONSUMED: Final[frozenset[str]] = frozenset(
    {
        "voice.asr.completed",
        "conversation.message.stored",
        "memory.read.completed",
    }
)

PRODUCER: Final[str] = "brain"
