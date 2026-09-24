"""Contratos do Tool Manager — catálogo fechado e execução governada."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: str
    requires_confirmation: bool
    automation_safe: bool


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    tool_name: str
    output: dict[str, Any]
    cached: bool = False


class ToolManagerPort(Protocol):
    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        user_id: str,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> ToolExecutionResult: ...
