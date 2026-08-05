"""Router do módulo reasoning — porta pública de exposição ao Brain.

Contrato: em v1+ este router expõe o RPC interno do Reasoning
(resolve_intent) para o Brain, que delega a interpretação da entrada.
Na v0.x permanece como esqueleto de contrato — implementação nas
versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reasoning", tags=["reasoning"])
