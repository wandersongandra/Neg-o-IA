"""Contratos do Reasoning — interpretação determinística e segura."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class IntentResolution:
    intent: str
    confidence: float
    entities: dict[str, Any]
    requires_plan: bool
    suggested_tool: str | None = None
    explicit_action: bool = False


class ReasoningPort(Protocol):
    async def resolve_intent(
        self,
        text: str,
        *,
        user_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> IntentResolution: ...
