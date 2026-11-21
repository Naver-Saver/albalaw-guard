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
