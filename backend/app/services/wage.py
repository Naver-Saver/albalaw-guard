"""최저임금·주휴수당 계산.

LLM은 숫자 계산을 틀릴 수 있으므로 모든 금액 계산은 이 모듈(코드)에서만 한다.
CLOVA Studio는 이 계산 결과를 '설명'만 한다.
"""

from dataclasses import dataclass

from app.services.calc import WageYearNotFound, get_min_wage

# 최저임금 금액은 law-data/min-wage.json(sync.wage)에서만 읽는다 (BR-03). 코드에 금액을 두지 않는다.

WEEKLY_HOLIDAY_MIN_HOURS = 15  # 주 소정근로시간 15시간 이상이면 주휴수당 대상
FULL_TIME_WEEKLY_HOURS = 40
FULL_TIME_HOLIDAY_HOURS = 8


@dataclass(frozen=True)
class WageCheckResult:
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


def minimum_wage(year: int) -> tuple[int, str]:
    try:
        entry = get_min_wage(year)
    except WageYearNotFound as e:
        raise ValueError(str(e)) from e
    return int(entry["hourlyWage"]), f"고용노동부 최저임금 고시 ({year}년 적용분)"


def weekly_holiday_hours(weekly_hours: float) -> float:
    """주휴시간 = (주 소정근로시간 / 40) × 8, 최대 8시간. 15시간 미만은 0."""
    if weekly_hours < WEEKLY_HOLIDAY_MIN_HOURS:
        return 0.0
    capped = min(weekly_hours, FULL_TIME_WEEKLY_HOURS)
    return round(capped / FULL_TIME_WEEKLY_HOURS * FULL_TIME_HOLIDAY_HOURS, 2)


def check_wage(hourly_wage: int, weekly_hours: float, year: int) -> WageCheckResult:
    if hourly_wage < 0 or weekly_hours < 0:
        raise ValueError("시급과 근로시간은 0 이상이어야 합니다.")
    min_hourly, notice = minimum_wage(year)
    holiday_hours = weekly_holiday_hours(weekly_hours)
    return WageCheckResult(
        year=year,
        minimum_hourly=min_hourly,
        notice=notice,
        hourly_wage=hourly_wage,
        meets_minimum=hourly_wage >= min_hourly,
        shortfall_per_hour=max(0, min_hourly - hourly_wage),
        weekly_hours=weekly_hours,
        weekly_holiday_eligible=holiday_hours > 0,
        weekly_holiday_hours=holiday_hours,
        weekly_holiday_pay=round(holiday_hours * max(hourly_wage, min_hourly)),
    )
