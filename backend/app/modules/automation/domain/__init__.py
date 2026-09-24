"""Contratos do módulo Automation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AutomationRule:
    id: str
    user_id: str
    name: str
    event_type: str
    action_tool: str
    action_args: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AutomationExecution:
    rule_id: str
    tool_name: str
    output: dict[str, Any]


class AutomationPort(Protocol):
    async def evaluate_rules(
        self,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[AutomationExecution]: ...
