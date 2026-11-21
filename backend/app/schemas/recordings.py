"""녹음 정리 API 스키마 (API-05 · API-06, docs/spec/openapi.yaml)."""

from typing import Literal

from pydantic import BaseModel, Field

TimelineCategory = Literal["임금", "근무시간", "휴게·휴일", "약속·지시", "기타"]
RecordingStatus = Literal["queued", "processing", "done", "failed"]


class SpeechSegmentEntry(BaseModel):
    """화자 분리 음성 인식 개별 발화 구간."""

    start_ms: int
    end_ms: int
    speaker: str
    text: str


class TimelineEntry(BaseModel):
    """대화 중 임금·근무시간·약속 등 주요 발언 타임라인 항목."""

    start_ms: int
    speaker: str
    text: str
    category: TimelineCategory


class RecordingJob(BaseModel):
    """비동기 장문 녹음 인식 작업 상태 및 결과."""

    job_id: str
    status: RecordingStatus
    error: str | None = None
    duration_sec: int | None = None
    speakers: list[str] = Field(default_factory=list)
    segments: list[SpeechSegmentEntry] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    transcript: str | None = None
