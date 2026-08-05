"""Módulo conversation — sessões de conversa retomáveis do NEGÃO AI."""

from app.modules.conversation.application import (
    ChatResult,
    ConversationService,
    get_conversation_service,
)
from app.modules.conversation.domain import ConversationMessage, ConversationSession
from app.modules.conversation.infrastructure import (
    ConversationStore,
    get_conversation_store,
)

__all__ = [
    "ChatResult",
    "ConversationMessage",
    "ConversationService",
    "ConversationSession",
    "ConversationStore",
    "get_conversation_service",
    "get_conversation_store",
]
