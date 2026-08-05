"""Contratos do módulo brain — domain (framework-free).

Responsabilidade única: orquestrar o ciclo completo de um pedido
(entrada → contexto → raciocínio → plano → execução → aprendizado →
resposta) e manter o estado mental do cérebro único. O Brain não faz
raciocínio de domínio nem I/O externa; invoca módulos via router.py.
"""

from __future__ import annotations

from typing import Any, Protocol


class BrainPort(Protocol):
    """Porta pública do Brain (consumida pela API/Voice/Vision via router)."""

    async def process_input(
        self,
        text: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]: ...
