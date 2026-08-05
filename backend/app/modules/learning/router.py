"""Router do módulo learning — porta pública de exposição ao Brain.

Contrato: em v2+ este router expõe o RPC interno do Learning
(registro de experiência, consolidação e feedback) para o Brain.
Na v0.x permanece como esqueleto de contrato — implementação nas
versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/learning", tags=["learning"])
