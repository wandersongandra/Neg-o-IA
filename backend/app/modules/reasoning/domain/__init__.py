"""Contratos do módulo reasoning — domain (framework-free).

Responsabilidade única: interpretação — intenção, entidades, contexto
implícito e chamada ao modelo base (via Model Router). Faz inferência e
análise de ambiguidade; NÃO toma decisões de execução.
"""

from __future__ import annotations

from typing import Any, Protocol


class ReasoningPort(Protocol):
    """Porta pública do Reasoning (resolução de intenção)."""

    async def resolve_intent(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
