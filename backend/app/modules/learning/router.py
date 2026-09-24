"""Rotas autenticadas do Learning V1."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.learning.application import get_learning_service

router = APIRouter(prefix="/learning", tags=["learning"])


class FeedbackRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    rating: int = Field(ge=-1, le=1)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


@router.get("/status")
async def learning_status(auth: CurrentAuth) -> dict[str, object]:
    _user_id(auth)
    return await get_learning_service().status()


@router.post("/feedback")
async def record_feedback(
    body: FeedbackRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        feedback = await get_learning_service().record_feedback(
            _user_id(auth),
            body.content,
            rating=body.rating,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "memory_id": feedback.memory_id,
        "content": feedback.content,
        "rating": feedback.rating,
        "created_at": feedback.created_at.isoformat(),
    }
