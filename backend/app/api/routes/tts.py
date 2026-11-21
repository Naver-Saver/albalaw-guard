"""음성 합성(TTS) 라우터 (API-09, FS-01·FS-03)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Body, Response
from pydantic import BaseModel, Field, field_validator

from app.services import clova_voice

router = APIRouter(tags=["media"])

Lang = Literal["ko", "en", "vi", "zh-CN"]


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=clova_voice.MAX_TEXT_CHARS)
    lang: Lang = "ko"

    @field_validator("text")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("읽을 텍스트를 입력해 주세요.")
        return stripped


@router.post("/tts", responses={200: {"content": {"audio/mpeg": {}}, "description": "mp3 음성"}})
async def text_to_speech(req: Annotated[TtsRequest, Body()]) -> Response:
    """텍스트를 CLOVA Voice MP3 오디오로 변환한다."""
    audio = await clova_voice.synthesize(req.text, req.lang)
    return Response(content=audio, media_type="audio/mpeg")
