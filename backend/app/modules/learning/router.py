"""User-authenticated feedback and inspectable personalized lessons."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.conversation.application import get_conversation_service
from app.modules.conversation.infrastructure import ConversationPersistenceError
from app.modules.learning.application import get_learning_service

router = APIRouter(prefix="/learning", tags=["learning"])


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message_ref: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")
    rating: int = Field(ge=-1, le=1)
    lesson: str | None = Field(default=None, max_length=2000)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


@router.post("/feedback")
async def record_feedback(body: FeedbackRequest, auth: CurrentAuth) -> dict[str, Any]:
    user_id = _user_id(auth)
    if body.rating not in {-1, 1}:
        raise HTTPException(status_code=422, detail="rating must be -1 or 1")
    try:
        if not await get_conversation_service().owns_session(body.session_id, user_id):
            raise HTTPException(status_code=404, detail="session not found")
    except ConversationPersistenceError as exc:
        raise HTTPException(status_code=503, detail="conversation storage unavailable") from exc
    try:
        record = await get_learning_service().record_feedback(
            user_id,
            session_id=body.session_id,
            message_ref=body.message_ref,
            rating=body.rating,
            lesson=body.lesson,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"experience": _public(record)}


@router.get("/experiences")
async def list_experiences(auth: CurrentAuth) -> dict[str, Any]:
    records = await get_learning_service().list_recent(_user_id(auth))
    return {"experiences": [_public(record) for record in records]}


@router.delete("/experiences/{experience_id}")
async def delete_experience(experience_id: str, auth: CurrentAuth) -> dict[str, bool]:
    deleted = await get_learning_service().delete(_user_id(auth), experience_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="experience not found")
    return {"deleted": True}


def _public(record: dict[str, Any]) -> dict[str, Any]:
    return {**record, "created_at": record["created_at"].isoformat()}
