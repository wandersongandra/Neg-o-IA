"""Reasoning V1 — resolução de intenção sem efeitos colaterais."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.modules.events.envelope import build_envelope
from app.modules.reasoning.domain import IntentResolution

_LOGGER = logging.getLogger("app.modules.reasoning.application")
_service: ReasoningService | None = None
PRODUCER = "reasoning"

_REMEMBER_RE = re.compile(
    r"^\s*(?:lembre|memorize|guarde)(?:-se)?(?:\s+que|\s+disso|\s*:)?\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_MEMORY_SEARCH_MARKERS = (
    "o que você lembra",
    "o que voce lembra",
    "procure na memória",
    "procure na memoria",
    "buscar na memória",
    "buscar na memoria",
    "minhas memórias",
    "minhas memorias",
)
_KNOWLEDGE_MARKERS = (
    "base de conhecimento",
    "nos documentos",
    "na documentação",
    "na documentacao",
    "knowledge",
    "documentos salvos",
)
_HEALTH_MARKERS = (
    "status do sistema",
    "estado do sistema",
    "saúde do sistema",
    "saude do sistema",
    "health check",
    "healthcheck",
)
_PLAN_MARKERS = (
    "crie um plano",
    "criar um plano",
    "monte um plano",
    "planeje",
    "passo a passo",
)


class ReasoningService:
    async def resolve_intent(
        self,
        text: str,
        *,
        user_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> IntentResolution:
        normalized = " ".join(text.casefold().split())
        entities: dict[str, Any] = {}
        match = _REMEMBER_RE.match(text)

        if match:
            entities["content"] = match.group(1).strip()
            resolution = IntentResolution(
                intent="memory.remember",
                confidence=0.98,
                entities=entities,
                requires_plan=True,
                suggested_tool="memory.remember",
                explicit_action=True,
            )
        elif any(marker in normalized for marker in _MEMORY_SEARCH_MARKERS):
            entities["query"] = text.strip()
            resolution = IntentResolution(
                intent="memory.search",
                confidence=0.94,
                entities=entities,
                requires_plan=True,
                suggested_tool="memory.search",
            )
        elif any(marker in normalized for marker in _KNOWLEDGE_MARKERS):
            entities["query"] = text.strip()
            resolution = IntentResolution(
                intent="knowledge.search",
                confidence=0.9,
                entities=entities,
                requires_plan=True,
                suggested_tool="knowledge.search",
            )
        elif any(marker in normalized for marker in _HEALTH_MARKERS):
            resolution = IntentResolution(
                intent="system.health",
                confidence=0.95,
                entities={},
                requires_plan=True,
                suggested_tool="system.health",
            )
        elif any(marker in normalized for marker in _PLAN_MARKERS):
            resolution = IntentResolution(
                intent="planning",
                confidence=0.86,
                entities={"goal": text.strip()},
                requires_plan=True,
            )
        else:
            resolution = IntentResolution(
                intent="chat",
                confidence=0.55,
                entities={},
                requires_plan=False,
            )

        await self._publish(resolution, user_id=user_id)
        return resolution

    async def _publish(self, resolution: IntentResolution, *, user_id: str | None) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    "reasoning.intent.resolved",
                    PRODUCER,
                    {
                        "intent": resolution.intent,
                        "confidence": resolution.confidence,
                        "suggested_tool": resolution.suggested_tool,
                    },
                    user_id=user_id,
                )
            )
        except Exception:
            _LOGGER.warning("reasoning_event_publish_failed", exc_info=True)


def get_reasoning_service() -> ReasoningService:
    global _service
    if _service is None:
        _service = ReasoningService()
    return _service
