"""Módulo scheduler — agendamento temporal cron-like.

v0: esqueleto de contrato. Implementação efetiva em v2+ (Cérebro que Aprende).
"""

from __future__ import annotations

from app.modules.scheduler.domain import SchedulerPort

__all__ = ["SchedulerPort"]
