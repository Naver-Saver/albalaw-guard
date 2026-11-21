from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.contracts import Source
from app.schemas.recordings import TimelineCategory

Lang = Literal["ko", "en", "vi", "zh-CN"]


class TimelineInput(BaseModel):
    """타임라인 항목 중 근거를 찾을 발언. 화자 이름은 화면에서만 바꾸므로 사장님 발언만 보내도 된다."""

    start_ms: int = Field(..., ge=0)
    speaker: str = Field(..., max_length=30)
    text: str = Field(..., min_length=1, max_length=500)
    category: TimelineCategory


class TimelineEvidenceRequest(BaseModel):
    entries: list[TimelineInput] = Field(..., min_length=1, max_length=50)
    lang: Lang = "ko"


class EntryEvidence(BaseModel):
    index: int = Field(description="요청 entries 의 순서 (0부터)")
    start_ms: int
    sources: list[Source]
    verbal_promise: bool = Field(description="말로만 한 조건·약속으로 보이면 true")
    advice: str | None = Field(None, description="verbal_promise 일 때 안내 문장")


class TimelineEvidenceResult(BaseModel):
    entries: list[EntryEvidence]
    checklist_for_next_time: list[str]
    disclaimer: str
