"""Casos de uso do módulo conversation — ConversationService (facade).

Monta o contexto (persona + histórico), chama o Brain e persiste o
diálogo. Falhas do Brain viram resposta graciosa em PT-BR sem quebrar
a sessão.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.modules.brain.domain import ChatMessage, TaskType
from app.modules.configuration.settings import get_settings
from app.modules.conversation.domain import ConversationMessage
from app.modules.conversation.events import (
    EVENT_CONVERSATION_MESSAGE_RESPONDED,
    EVENT_CONVERSATION_MESSAGE_STORED,
    EVENT_CONVERSATION_STARTED,
)
from app.modules.conversation.infrastructure import get_conversation_store
from app.modules.events.envelope import build_envelope

_LOGGER = logging.getLogger("app.modules.conversation.application")

PRODUCER = "conversation"

SYSTEM_PROMPT = (
    "Você é o NEGÃO, assistente pessoal de inteligência artificial do Wanderson. "
    "Fala sempre em português brasileiro, com tom profissional, elegante e direto, "
    "inspirado no JARVIS: nunca invente fatos, admita quando não souber, e use humor "
    "sutil quando apropriado. Trate o usuário como 'chefe'. Seja conciso: prefira "
    "respostas curtas e úteis, em vez de longas explicações. Nunca repita o que o "
    "usuário acabou de dizer."
)

FALLBACK_REPLY = (
    "Opa, chefe! Meu cérebro deu uma engasgada agora — não consegui processar isso. "
    "Tenta de novo em instantes."
)


@dataclass(frozen=True)
class ChatResult:
    """Resultado de um turno de conversa."""

    text: str
    model: str
    latency_ms: int
    fallback_used: bool
    cached: bool


class ConversationService:
    """Facade pública das conversas do NEGÃO AI."""

    def __init__(self, store: Any | None = None) -> None:
        self._store = store if store is not None else get_conversation_store()

    async def start_session(self, user_id: str | None = None) -> Any:
        session = await self._store.start_session(user_id)
        await self._publish(
            EVENT_CONVERSATION_STARTED,
            {"session_id": session.session_id, "user_id": user_id},
        )
        return session

    async def get_messages(self, session_id: str) -> list[ConversationMessage]:
        return await self._store.get_messages(session_id)

    async def list_sessions(self) -> list[Any]:
        return await self._store.list_sessions()

    async def append_message(
        self, session_id: str, role: str, content: str
    ) -> ConversationMessage:
        message = await self._store.append_message(session_id, role, content)
        await self._publish(
            EVENT_CONVERSATION_MESSAGE_STORED,
            {"session_id": session_id, "role": role},
        )
        return message

    async def get_context(self, session_id: str) -> list[ChatMessage]:
        settings = get_settings()
        messages = await self._store.get_messages(session_id)
        window = messages[-settings.conversation_max_context_messages :]
        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            *[
                ChatMessage(role=m.role, content=m.content)
                for m in window
                if m.role in {"user", "assistant"}
            ],
        ]

    async def chat(
        self, session_id: str, text: str, *, user_id: str | None = None
    ) -> ChatResult:
        await self.append_message(session_id, "user", text)
        context = await self.get_context(session_id)
        try:
            from app.modules.brain.application import get_brain_service

            response = await get_brain_service().complete(
                context,
                task_type=TaskType.CHAT,
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as exc:
            _LOGGER.exception(
                "conversation_brain_failed", extra={"error": str(exc)}
            )
            return ChatResult(
                text=FALLBACK_REPLY,
                model="error",
                latency_ms=0,
                fallback_used=False,
                cached=False,
            )
        await self.append_message(session_id, "assistant", response.text)
        await self._publish(
            EVENT_CONVERSATION_MESSAGE_RESPONDED,
            {
                "session_id": session_id,
                "model": response.model,
                "latency_ms": response.latency_ms,
            },
        )
        return ChatResult(
            text=response.text,
            model=response.model,
            latency_ms=response.latency_ms,
            fallback_used=response.fallback_used,
            cached=response.cached,
        )

    async def reset_session(self, session_id: str) -> None:
        from app.infrastructure.redis import get_redis

        client = get_redis()
        try:
            await client.delete(f"conv:{session_id}:messages")
            await client.srem("conversation:sessions", session_id)
        except Exception:
            _LOGGER.debug("conversation_reset_failed", exc_info=True)

    async def rename_session(self, session_id: str, name: str | None) -> bool:
        return await self._store.rename_session(session_id, name)

    async def delete_session(self, session_id: str) -> bool:
        return await self._store.delete_session(session_id)

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            service = get_event_bus_service()
            await service.publish_event(build_envelope(event_type, PRODUCER, payload))
        except Exception as exc:
            _LOGGER.warning(
                "falha ao publicar evento de conversa",
                extra={"event_type": event_type, "error": str(exc)},
            )


_service: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    """Singleton do ConversationService."""
    global _service
    if _service is None:
        _service = ConversationService()
    return _service


def reset_conversation_service() -> None:
    """Reset do singleton (uso em testes)."""
    global _service
    _service = None


__all__ = [
    "ChatResult",
    "ConversationService",
    "SYSTEM_PROMPT",
    "get_conversation_service",
    "reset_conversation_service",
]
