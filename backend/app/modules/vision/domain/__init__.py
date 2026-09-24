"""Contratos do módulo Vision."""

from __future__ import annotations

from typing import Any, Protocol


class VisionPort(Protocol):
    async def analyze(
        self,
        image_bytes: bytes,
        *,
        media_type: str,
        prompt: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]: ...
