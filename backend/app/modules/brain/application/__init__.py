"""Casos de uso do módulo brain — BrainService (facade).

Publica os eventos de contrato (`brain.request.started` /
`brain.request.completed`) de forma best-effort e delega o roteamento
para o ModelRouter (infrastructure).
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.brain.domain import (
    BrainPort,
    ChatMessage,
    ModelRequest,
    ModelResponse,
    TaskType,
)
from app.modules.brain.events import (
    EVENT_BRAIN_REQUEST_COMPLETED,
    EVENT_BRAIN_REQUEST_STARTED,
)
from app.modules.brain.infrastructure import get_model_router
from app.modules.events.envelope import build_envelope

_LOGGER = logging.getLogger("app.modules.brain.application")

PRODUCER = "brain"

_brain_service: BrainService | None = None


class BrainService:
    """Facade pública do cérebro único do NEGÃO AI."""

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        task_type: TaskType = TaskType.CHAT,
        session_id: str | None = None,
        user_id: str | None = None,
        trace_id: str | None = None,
    ) -> ModelResponse:
        await self._publish(
            EVENT_BRAIN_REQUEST_STARTED,
            {
                "session_id": session_id,
                "user_id": user_id,
                "task_type": task_type.value,
                "messages": len(messages),
            },
        )
        try:
            response = await get_model_router().complete(
                ModelRequest(
                    messages=messages,
                    task_type=task_type,
                    temperature=None,
                    max_tokens=None,
                )
            )
        except Exception as exc:
            _LOGGER.exception("brain_request_failed", extra={"error": str(exc)})
            raise
        await self._publish(
            EVENT_BRAIN_REQUEST_COMPLETED,
            {
                "session_id": session_id,
                "model": response.model,
                "latency_ms": response.latency_ms,
                "cached": response.cached,
                "fallback_used": response.fallback_used,
            },
        )
        return response

    async def process_input(
        self,
        text: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Ponto de entrada legado (BrainPort): texto simples → dict."""
        response = await self.complete(
            [ChatMessage(role="user", content=text)],
            task_type=TaskType.CHAT,
            session_id=session_id,
            user_id=user_id,
            trace_id=trace_id,
        )
        return {
            "text": response.text,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "cached": response.cached,
            "fallback_used": response.fallback_used,
        }

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            service = get_event_bus_service()
            await service.publish_event(build_envelope(event_type, PRODUCER, payload))
        except Exception as exc:
            _LOGGER.warning(
                "falha ao publicar evento do brain",
                extra={"event_type": event_type, "error": str(exc)},
            )


def get_brain_service() -> BrainService:
    """Singleton do BrainService."""
    global _brain_service
    if _brain_service is None:
        _brain_service = BrainService()
    return _brain_service


def reset_brain_service() -> None:
    """Reset do singleton (uso em testes)."""
    global _brain_service
    _brain_service = None


__all__ = [
    "BrainPort",
    "BrainService",
    "get_brain_service",
    "reset_brain_service",
]
