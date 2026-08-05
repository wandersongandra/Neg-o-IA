"""Contratos de domínio do módulo Database (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseStatus:
    connected: bool
    engine_url: str
    active_connections: int
    detail: str = ""
