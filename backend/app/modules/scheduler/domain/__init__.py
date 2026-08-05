"""Contratos do módulo scheduler — domain (framework-free).

Responsabilidade única: agendar tarefas temporais (cron-like) e acordar
o Brain via `scheduler.tick`. Faz agendamento, cron e lembretes;
NÃO decide o conteúdo das tarefas.
"""

from __future__ import annotations

from typing import Any, Protocol


class SchedulerPort(Protocol):
    """Porta pública do Scheduler (agendamento temporal)."""

    async def schedule(
        self, *, name: str, cron: str, action: dict[str, Any]
    ) -> str: ...

    async def cancel(self, job_id: str) -> bool: ...
