"""Rotas autenticadas do Vision V1."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.interfaces.deps import CurrentAuth
from app.modules.vision.application import VisionUnavailableError, get_vision_service
from app.modules.vision.infrastructure import VisionProviderError

router = APIRouter(prefix="/vision", tags=["vision"])


class AnalyzeImageRequest(BaseModel):
    image_base64: str = Field(min_length=4, max_length=8_000_000)
    media_type: str = Field(min_length=1, max_length=64)
    prompt: str | None = Field(default=None, max_length=2000)


def _user_id(auth: CurrentAuth) -> str:
    user_id = auth.effective_user_id
    if not user_id:
        raise HTTPException(status_code=403, detail="user identity required")
    return user_id


@router.get("/status")
async def vision_status(auth: CurrentAuth) -> dict[str, Any]:
    _user_id(auth)
    return await get_vision_service().status()


@router.post("/analyze")
async def analyze_image(
    body: AnalyzeImageRequest,
    auth: CurrentAuth,
) -> dict[str, Any]:
    try:
        image_bytes = base64.b64decode(body.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="invalid base64 image") from exc

    try:
        return await get_vision_service().analyze(
            image_bytes,
            media_type=body.media_type,
            prompt=body.prompt,
            user_id=_user_id(auth),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=503, detail="vision unavailable") from exc
    except VisionProviderError as exc:
        raise HTTPException(status_code=502, detail="vision provider failed") from exc
