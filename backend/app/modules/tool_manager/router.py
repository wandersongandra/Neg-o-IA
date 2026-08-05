"""Router do módulo tool_manager — porta pública de exposição ao Brain.

Contrato: em v3+ este router expõe o RPC interno do Tool Manager
(execute_tool, registro e catálogo de plugins) para o Brain, que delega
a execução de passos do plano. Na v0.x permanece como esqueleto de
contrato — implementação nas versões seguintes (v1+).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/tool-manager", tags=["tool_manager"])
