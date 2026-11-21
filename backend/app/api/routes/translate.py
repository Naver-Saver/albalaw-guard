from typing import Annotated, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from app.core.response import ApiResponse, ok
from app.services.translate import translate_texts

router = APIRouter(tags=["media"])

Lang = Literal["ko", "en", "vi", "zh-CN"]


class TranslateRequest(BaseModel):
    texts: list[str] = Field(..., max_length=30)
    target: Lang


class TranslateResponse(BaseModel):
    texts: list[str]
    target: Lang


@router.post("/translate", response_model=ApiResponse[TranslateResponse])
async def translate(req: Annotated[TranslateRequest, Body()]) -> ApiResponse[TranslateResponse]:
    """Papago 번역 (API-10). 실패하면 원문을 돌려주지 않고 502(AI_UNAVAILABLE)를 낸다."""
    texts = await translate_texts(req.texts, req.target, strict=True)
    return ok(TranslateResponse(texts=texts, target=req.target))
