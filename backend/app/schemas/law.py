from pydantic import BaseModel, Field


class EvidenceSummary(BaseModel):
    """근거 검색 결과 한 건 (API-11). snippet 은 본문 앞부분."""

    id: str
    source: str = Field(description="MANUAL | LAW_API | ...")
    title: str
    snippet: str
    url: str


class QaSearchResponse(BaseModel):
    items: list[EvidenceSummary]


class LawSourceResponse(BaseModel):
    """근거 원문 단건 (API-12). text 는 자르지 않은 원문."""

    id: str
    source: str
    title: str
    text: str
    url: str
    related_article_ids: list[str] = Field(default_factory=list)


class MinimumWageResponse(BaseModel):
    """연도별 최저임금 (API-13). year 미지정 시 데이터에 있는 가장 최근 연도로 대체될 수 있다."""

    year: int
    hourly_wage: int
    period_start: str
    period_end: str
    is_fallback: bool = Field(description="요청 연도 데이터가 없어 다른 연도로 대체했으면 true")
