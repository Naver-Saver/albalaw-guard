from datetime import date

from pydantic import BaseModel, Field


class WageCheckRequest(BaseModel):
    hourly_wage: int = Field(..., ge=0, description="계약서상 시급(원)")
    weekly_hours: float = Field(..., ge=0, le=168, description="주 소정근로시간")
    year: int = Field(
        default_factory=lambda: date.today().year, description="적용 연도 (기본: 요청 시점 연도, BR-03)"
    )


class WageCheckResponse(BaseModel):
    year: int
    minimum_hourly: int
    notice: str
    hourly_wage: int
    meets_minimum: bool
    shortfall_per_hour: int
    weekly_hours: float
    weekly_holiday_eligible: bool
    weekly_holiday_hours: float
    weekly_holiday_pay: int
