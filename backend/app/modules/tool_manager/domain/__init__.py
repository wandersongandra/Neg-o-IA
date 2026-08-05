"""Contratos do módulo tool_manager — domain (framework-free).

Responsabilidade única: catalogar, resolver e executar ferramentas;
encapsular efeitos externos com timeout, retry e sanitização de
resultado. NÃO decide o plano (isso é do Planner).
"""

from __future__ import annotations

from typing import Any, Protocol


class ToolManagerPort(Protocol):
    """Porta pública do Tool Manager (execução de ferramentas)."""

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]: ...
