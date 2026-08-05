from __future__ import annotations

from typing import Final

SECURITY_API_KEY_VALIDATED: Final[str] = "security.api_key_validated"
SECURITY_API_KEY_REJECTED: Final[str] = "security.api_key_rejected"
SECURITY_AUTHORIZATION_LEVEL_CHANGED: Final[str] = (
    "security.authorization_level_changed"
)

EVENT_TYPES: Final[tuple[str, ...]] = (
    SECURITY_API_KEY_VALIDATED,
    SECURITY_API_KEY_REJECTED,
    SECURITY_AUTHORIZATION_LEVEL_CHANGED,
)

__all__ = [
    "SECURITY_API_KEY_VALIDATED",
    "SECURITY_API_KEY_REJECTED",
    "SECURITY_AUTHORIZATION_LEVEL_CHANGED",
    "EVENT_TYPES",
]
