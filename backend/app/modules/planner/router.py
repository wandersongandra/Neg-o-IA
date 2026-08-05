"""Router do módulo planner — porta pública de exposição ao Brain.

Contrato: em v1+ este router expõe o RPC interno do Planner
(create_plan, replan) para o Brain, que delega a decomposição de
intenções em passos executáveis. Na v0.x permanece como esqueleto de
contrato — implementação nas versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/planner", tags=["planner"])
