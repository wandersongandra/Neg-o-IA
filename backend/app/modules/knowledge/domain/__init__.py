"""Contratos do módulo knowledge — domain (framework-free).

Responsabilidade única: gerenciar a base de conhecimento estática/curada
(documentos, FAQs, manuais, projetos) consultável pelo Brain. Faz lookup,
chunking e indexação; NÃO faz memória pessoal do usuário (isso é da Memory).
"""

from __future__ import annotations

from typing import Any, Protocol


class KnowledgePort(Protocol):
    """Porta pública do Knowledge (consulta semântica do Vault)."""

    async def lookup(
        self,
        query: str,
        *,
        limit: int = 5,
        user_id: str | None = None,
    ) -> dict[str, Any]: ...
