"""Módulo Database — gestão do PostgreSQL (engine, sessões, migrações).

Responsabilidade única: infraestrutura de banco. Não modela memória nem
conhecimento (isso é da Memory/Knowledge); fornece o provider usado por todos.
"""

from __future__ import annotations

from app.modules.configuration.settings import Settings
from app.modules.database.infrastructure import DatabaseProvider, create_provider

__all__ = ["DatabaseProvider", "create_provider", "get_database_provider"]

_providers: dict[str, DatabaseProvider] = {}


def get_database_provider(settings: Settings) -> DatabaseProvider:
    """Singleton do provider de banco (um por URL de conexão)."""
    provider = _providers.get(settings.database_url)
    if provider is None:
        provider = create_provider(settings)
        _providers[settings.database_url] = provider
    return provider
