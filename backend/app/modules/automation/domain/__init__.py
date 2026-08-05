"""Contratos do módulo automation — domain (framework-free).

Responsabilidade única: executar rotinas automáticas "se-então" disparadas
por eventos/scheduler. Avalia regras e dispara pedidos no Brain;
NÃO cria regras sozinho.
"""

from __future__ import annotations

from typing import Any, Protocol


class AutomationPort(Protocol):
    """Porta pública do Automation (avaliação de regras)."""

    async def evaluate_rules(
        self, event_type: str, payload: dict[str, Any]
    ) -> list[str]: ...
