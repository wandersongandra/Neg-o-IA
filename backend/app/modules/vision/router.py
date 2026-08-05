"""Router do módulo vision — porta pública de exposição ao Brain.

Contrato: em v4+ este router expõe o RPC interno do Vision (analyze) e
os endpoints de upload de imagem para a camada de interfaces. Na v0.x
permanece como esqueleto de contrato — implementação nas versões
seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/vision", tags=["vision"])
