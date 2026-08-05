"""Contrato de eventos do módulo conversation — catálogo v1 (Event Bus).

Producer deste módulo: "conversation".
"""

from __future__ import annotations

from typing import Final

EVENT_VERSION = 1

EVENT_CONVERSATION_STARTED: Final[str] = "conversation.started"
EVENT_CONVERSATION_MESSAGE_STORED: Final[str] = "conversation.message.stored"
EVENT_CONVERSATION_MESSAGE_RESPONDED: Final[str] = "conversation.message.responded"

EVENT_CATALOG: Final[dict[str, str]] = {
    EVENT_CONVERSATION_STARTED: (
        "Nova sessão de conversa criada (retomável pelo session_id)"
    ),
    EVENT_CONVERSATION_MESSAGE_STORED: (
        "Mensagem do usuário persistida no histórico da sessão"
    ),
    EVENT_CONVERSATION_MESSAGE_RESPONDED: (
        "Resposta do NEGÃO persistida no histórico da sessão"
    ),
}

PUBLISHED: Final[frozenset[str]] = frozenset(
    {
        EVENT_CONVERSATION_STARTED,
        EVENT_CONVERSATION_MESSAGE_STORED,
        EVENT_CONVERSATION_MESSAGE_RESPONDED,
    }
)

CONSUMED: Final[frozenset[str]] = frozenset(
    {
        "brain.request.completed",
        "voice.transcription.completed",
    }
)

PRODUCER: Final[str] = "conversation"
