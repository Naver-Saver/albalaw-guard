from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

DocType = Literal["contract", "payslip"]
Confidence = Literal["high", "low"]


class ExtractedField(BaseModel):
    value: Any | None = None
    confidence: Confidence = "low"
    source_text: str | None = None


class ExtractedFields(BaseModel):
    hourly_wage: ExtractedField = Field(default_factory=ExtractedField)
    weekly_hours: ExtractedField = Field(default_factory=ExtractedField)
    work_days: ExtractedField = Field(default_factory=ExtractedField)
    break_minutes: ExtractedField = Field(default_factory=ExtractedField)


class OcrResult(BaseModel):
    doc_type: DocType
    raw_text: str
    extracted: ExtractedFields


Lang = Literal["ko", "en", "vi", "zh-CN"]
Weekday = Literal["월", "화", "수", "목", "금", "토", "일"]


class ReviewRequest(BaseModel):
    hourly_wage: int = Field(..., ge=0, description="확정된 시급(원)")
    weekly_hours: float = Field(..., ge=0, le=168, description="1주 소정근로시간")
    work_days: list[Weekday] | None = None
    break_minutes: int | None = Field(None, ge=0, le=24 * 60)
    year: int = Field(default_factory=lambda: date.today().year, description="적용 연도 (BR-03)")
    lang: Lang = "ko"


class CheckItem(BaseModel):
    level: Literal["ok", "check"]
    title: str
    description: str


class Source(BaseModel):
    id: str
    title: str
    snippet: str | None = None
    url: str | None = None


class ReviewResult(BaseModel):
    calculation: "WageCheckResponse"
    items: list[CheckItem]
    explanation: str | None
    sources: list[Source]
    disclaimer: str


from app.schemas.wage import WageCheckResponse  # noqa: E402

ReviewResult.model_rebuild()
