"""Explicit feedback based personalization; no silent cross-user training."""

from __future__ import annotations

from typing import Any

from app.core.sensitive_content import likely_secret_kind
from app.modules.events.envelope import build_envelope
from app.modules.learning.infrastructure import PostgresLearningStore

PRODUCER = "learning"
_service: LearningService | None = None


class LearningService:
    def __init__(self, store: PostgresLearningStore | None = None) -> None:
        self._store = store or PostgresLearningStore()

    async def record_feedback(
        self,
        user_id: str,
        *,
        session_id: str,
        message_ref: str,
        rating: int,
        lesson: str | None = None,
    ) -> dict[str, Any]:
        if rating not in {-1, 1}:
            raise ValueError("rating must be -1 or 1")
        normalized = " ".join((lesson or "").split()) or None
        if normalized and len(normalized) > 2000:
            raise ValueError("lesson must contain at most 2000 characters")
        if normalized and likely_secret_kind(normalized):
            raise ValueError("lesson appears to contain a credential and was not saved")
        record = await self._store.record(
            user_id,
            session_id=session_id,
            message_ref=message_ref,
            rating=rating,
            lesson=normalized,
        )
        await self._publish(
            "learning.experience.recorded",
            {
                "user_id": user_id,
                "session_id": session_id,
                "rating": rating,
                "has_lesson": normalized is not None,
            },
        )
        return record

    async def relevant_lessons(
        self, user_id: str, query: str, *, min_score: float
    ) -> list[dict[str, Any]]:
        hits = await self._store.search(user_id, query)
        return [hit for hit in hits if hit.get("lesson") and hit["score"] >= min_score]

    async def list_recent(self, user_id: str) -> list[dict[str, Any]]:
        return await self._store.list_recent(user_id)

    async def delete(self, user_id: str, experience_id: str) -> bool:
        return await self._store.delete(user_id, experience_id)

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from app.modules.events.application import get_event_bus_service

            await get_event_bus_service().publish_event(
                build_envelope(
                    event_type,
                    PRODUCER,
                    payload,
                    user_id=payload.get("user_id"),
                    session_id=payload.get("session_id"),
                )
            )
        except Exception:
            # Learning is a non-critical side effect; the persisted feedback remains valid.
            return


def get_learning_service() -> LearningService:
    global _service
    if _service is None:
        _service = LearningService()
    return _service


__all__ = ["LearningService", "get_learning_service"]
