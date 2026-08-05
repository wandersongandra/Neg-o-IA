"""Router do módulo scheduler — porta pública de exposição ao Brain.

Contrato: em v2+ este router expõe o RPC interno do Scheduler
(schedule, cancel e listagem de jobs) para o Brain e a camada de
interfaces. Na v0.x permanece como esqueleto de contrato —
implementação nas versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
