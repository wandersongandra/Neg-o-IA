"""Contratos do módulo vision — domain (framework-free).

Responsabilidade única: análise de imagens (captura, OCR e descrição/
Q&A sobre imagens). Faz captura e análise; NÃO decide ação sobre a
imagem (isso é do Brain).
"""

from __future__ import annotations

from typing import Any, Protocol


class VisionPort(Protocol):
    """Porta pública do Vision (análise de imagens)."""

    async def analyze(
        self, image_bytes: bytes, *, prompt: str | None = None
    ) -> dict[str, Any]: ...
