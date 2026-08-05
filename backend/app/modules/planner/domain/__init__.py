"""Contratos do módulo planner — domain (framework-free).

Responsabilidade única: transformar intenção em plano de passos
executáveis e replanejar em falha (decomposição, ordenação, replan com
limite de tentativas). NÃO executa ferramentas.
"""

from __future__ import annotations

from typing import Any, Protocol


class PlannerPort(Protocol):
    """Porta pública do Planner (decomposição de intenção em passos)."""

    async def create_plan(
        self, intent: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    async def replan(self, plan_id: str, failure: dict[str, Any]) -> dict[str, Any]: ...
