"""Learning V1 — feedback explícito sem auto-modificação da persona."""

from __future__ import annotations

import logging

from app.modules.events.envelope import build_envelope
from app.modules.learning.domain import LearningFeedback
from app.modules.memory.application.long_term import get_long_term_memory_service

_LOGGER = logging.getLogger("app.modules.learning.application")
_service: LearningService | None = None


class LearningService:
    async def record_feedback(
        self,
        user_id: str,
        content: str,
        *,
        rating: int,
    ) -> LearningFeedback:
        normalized = content.strip()
        if not normalized or len(normalized) > 2000:
            raise ValueError("feedback content must contain 1..2000 characters")
        if rating not in {-1, 1}:
            raise ValueError("rating must be -1 or 1")

        importance = 0.75 if rating > 0 else 0.6
        entry = await get_long_term_memory_service().remember(
            user_id,
            normalized,
            source="learning_feedback",
            importance=importance,
            metadata={
                "kind": "explicit_feedback",
                "rating": rating,
                "adaptive_prompt": False,
            },
        )
        await self._publish(
            user_id,
            {
                "memory_id": entry.id,
                "rating": rating,
            },
        )
        return LearningFeedback(
            memory_id=entry.id,
            user_id=user_id,
            content=entry.content,
            rating=rating,
            created_at=entry.created_at,
        )

    async def status(self) -> dict[str, object]:
        return {
            "mode": "explicit_feedback",
            "adaptive_prompt": False,
            "autonomous_training": False,
            "storage": "long_term_memory",
        }

    async def _publish(self, user_id: str, payload: dict[str, object]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    "learning.feedback.recorded",
                    "learning",
                    payload,
                    user_id=user_id,
                )
            )
        except Exception:
            _LOGGER.warning("learning_event_publish_failed", exc_info=True)


def get_learning_service() -> LearningService:
    global _service
    if _service is None:
        _service = LearningService()
    return _service
