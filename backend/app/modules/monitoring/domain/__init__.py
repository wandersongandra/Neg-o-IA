"""Contratos do módulo monitoring — domain (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    """Instantâneo de uma métrica do NEGÃO AI."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)


class LogLevel(Enum):
    """Níveis de log estruturado (JSON)."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    AUDIT = "audit"
