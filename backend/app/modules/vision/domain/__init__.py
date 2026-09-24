"""Contratos do módulo Vision."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VisionAnalysis:
    text: str
    model: str
    latency_ms: int
    mime_type: str
    bytes_processed: int


class VisionPort(Protocol):
    async def analyze(
        self,
        image_bytes: bytes,
        *,
        mime_type: str,
        prompt: str | None = None,
    ) -> VisionAnalysis: ...
