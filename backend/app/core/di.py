from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from app.modules.configuration.settings import Settings, get_settings


@dataclass(slots=True)
class AppServices:
    settings: Settings = field(default_factory=get_settings)


_services: AppServices | None = None
_lock = Lock()


def build_services() -> AppServices:
    global _services
    if _services is not None:
        return _services
    with _lock:
        if _services is None:
            _services = AppServices()
    return _services


def get_services() -> AppServices:
    return build_services()
