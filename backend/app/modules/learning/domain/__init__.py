"""Contratos do módulo learning — domain (framework-free).

Responsabilidade única: extrair lições das execuções — registrar
experiências, avaliar resultado × intenção, gerar resumos e propor
consolidação na memória. NÃO altera a memória sozinho: sempre via Memory.
"""

from __future__ import annotations

from typing import Any, Protocol


class LearningPort(Protocol):
    """Porta pública do Learning (pipeline de experiência assíncrono)."""

    async def record_experience(self, experience: dict[str, Any]) -> None: ...
