"""Router do módulo voice — porta pública de exposição ao Brain.

Contrato: em v4+ este router expõe o RPC interno do Voice (transcrever,
sintetizar) e as sessões de voz via WebSocket para a camada de
interfaces. Na v0.x permanece como esqueleto de contrato —
implementação nas versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/voice", tags=["voice"])
