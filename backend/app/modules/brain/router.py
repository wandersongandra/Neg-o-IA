"""Router do módulo brain — porta pública de exposição ao cérebro.

Contrato: em v1+ este router expõe o RPC interno do Brain
(process_input e afins) para a camada de interfaces (API, Voice, Vision)
e será a única porta de entrada do ciclo request→response. Na v0.x
permanece como esqueleto de contrato — implementação nas versões v1+.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/brain", tags=["brain"])
