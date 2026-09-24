"""Contratos do Learning V1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LearningFeedback:
    memory_id: str
    user_id: str
    content: str
    rating: int
    created_at: datetime


class LearningPort(Protocol):
    async def record_feedback(
        self,
        user_id: str,
        content: str,
        *,
        rating: int,
    ) -> LearningFeedback: ...
