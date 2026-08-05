"""Router do módulo knowledge — porta pública de exposição ao Brain.

Contrato: em v2+ este router expõe o RPC interno do Knowledge
(lookup, ingestão e curadoria) para o Brain e rotas administrativas do
Vault. Na v0.x permanece como esqueleto de contrato — implementação
nas versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
