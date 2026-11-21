from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.contracts import Source


class AskTextRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=300)


class AskResult(BaseModel):
    question: str = Field(description="인식된 질문 텍스트")
    route: Literal["faq", "studio", "none"]
    answer: str
    sources: list[Source]
