"""최저임금·주휴수당·급여 검산 (파트 A). 숫자 판단은 LLM이 아니라 이 모듈이 한다.

최저임금은 law-data/min-wage.json(고용노동부 CSV 변환본)에서만 읽는다 — 코드에 금액을 넣지 않는다.
계산 규칙은 docs/spec/02-functional-spec.md 의 BR-03·BR-04 를 따른다 (팀 검토 필요, 법적 판단 아님).
"""

from datetime import date

from app.services import law_data

WEEKLY_HOLIDAY_MIN_HOURS = (
    15  # 4주 평균 1주 소정근로시간 15시간 미만은 주휴 대상 아님 (근로기준법 제18조 제3항: law-001872-18)
)
FULL_TIME_WEEKLY_HOURS = 40
FULL_TIME_HOLIDAY_HOURS = 8


class WageYearNotFound(Exception):
    """요청한 연도의 최저임금 데이터가 없다."""


def _items() -> list[dict]:
    data = law_data.read_json(law_data.MIN_WAGE_FILE)
    items = (data or {}).get("items", [])
    return sorted(items, key=lambda i: i["year"], reverse=True)


def get_min_wage(year: int | None = None) -> dict:
    """연도별 최저임금. year가 None이면 올해, 올해 데이터가 없으면 가장 최근 연도로 대체(isFallback=True).
    year를 직접 지정했는데 데이터가 없으면 WageYearNotFound.
    반환: {"year", "hourlyWage", "periodStart", "periodEnd", "isFallback"}
    """
    items = _items()
    if not items:
        raise WageYearNotFound("최저임금 데이터가 없습니다.")
    by_year = {i["year"]: i for i in items}
    if year is not None:
        if year not in by_year:
            raise WageYearNotFound(f"{year}년 최저임금 데이터가 없습니다.")
        return {**_pick(by_year[year]), "isFallback": False}
    this_year = date.today().year
    if this_year in by_year:
        return {**_pick(by_year[this_year]), "isFallback": False}
    candidates = [y for y in by_year if y < this_year] or list(by_year)
    return {**_pick(by_year[max(candidates)]), "isFallback": True}


def _pick(item: dict) -> dict:
    return {k: item[k] for k in ("year", "hourlyWage", "periodStart", "periodEnd")}


def weekly_holiday_hours(weekly_hours: float) -> float:
    """주휴시간. 주 15시간 미만이면 0, 아니면 min(주 소정근로시간, 40) / 40 × 8."""
    return _weekly_holiday_hours(weekly_hours)


def _weekly_holiday_hours(weekly_hours: float) -> float:
    if weekly_hours < WEEKLY_HOLIDAY_MIN_HOURS:
        return 0.0
    return round(
        min(weekly_hours, FULL_TIME_WEEKLY_HOURS) / FULL_TIME_WEEKLY_HOURS * FULL_TIME_HOLIDAY_HOURS, 2
    )


def check_contract_wage(hourly_wage: int, weekly_hours: float, year: int | None = None) -> dict:
    """계약서의 시급·주 소정근로시간 점검.
    - isBelowMinimum = 시급 < 최저임금, shortfallPerHour = max(0, 최저임금 - 시급)
    - 주휴: 주 15시간 이상이면 대상, 주휴시간 = min(주 소정근로시간, 40) / 40 × 8
    - 주휴수당 = round(주휴시간 × max(시급, 최저임금))  (BR-04)
    입력이 올바르지 않으면 ValueError, 연도 데이터가 없으면 WageYearNotFound.
    """
    if isinstance(hourly_wage, bool) or not isinstance(hourly_wage, int | float) or hourly_wage <= 0:
        raise ValueError("시급은 0보다 커야 합니다.")
    if (
        isinstance(weekly_hours, bool)
        or not isinstance(weekly_hours, int | float)
        or not (0 < weekly_hours <= 168)
    ):
        raise ValueError("주 소정근로시간은 0보다 크고 168 이하여야 합니다.")
    mw = get_min_wage(year)
    minimum = mw["hourlyWage"]
    holiday_hours = _weekly_holiday_hours(weekly_hours)
    return {
        "year": mw["year"],
        "minimumWage": minimum,
        "hourlyWage": hourly_wage,
        "isBelowMinimum": hourly_wage < minimum,
        "shortfallPerHour": max(0, minimum - hourly_wage),
        "weeklyHolidayEligible": holiday_hours > 0,
        "weeklyHolidayHours": holiday_hours,
        "weeklyHolidayPay": round(holiday_hours * max(hourly_wage, minimum)),
    }


def _amount(entry: dict, label: str) -> int:
    value = entry.get("amount") if isinstance(entry, dict) else None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{label} 항목의 amount가 숫자가 아닙니다: {entry!r}")
    return round(value)


def check_payslip_totals(
    items: list[dict], deductions: list[dict], total_pay: int | None, net_pay: int | None
) -> dict:
    """급여명세서 검산: 항목 합 = 총액, (총액 - 공제 합) = 실지급액.
    items·deductions 의 각 원소는 {"name": str, "amount": 원(int)}.
    총액/실지급액을 알 수 없으면(None) 해당 비교는 건너뛰고 matches 는 None.
    """
    items_sum = sum(_amount(i, "지급") for i in items)
    deductions_sum = sum(_amount(d, "공제") for d in deductions)
    mismatches: list[dict] = []

    total_matches: bool | None = None
    if total_pay is not None:
        total_matches = items_sum == total_pay
        if not total_matches:
            mismatches.append(
                {
                    "field": "totalPay",
                    "expected": items_sum,
                    "actual": total_pay,
                    "difference": total_pay - items_sum,
                }
            )

    base = total_pay if total_pay is not None else items_sum
    expected_net = base - deductions_sum
    net_matches: bool | None = None
    if net_pay is not None:
        net_matches = expected_net == net_pay
        if not net_matches:
            mismatches.append(
                {
                    "field": "netPay",
                    "expected": expected_net,
                    "actual": net_pay,
                    "difference": net_pay - expected_net,
                }
            )

    return {
        "itemsSum": items_sum,
        "deductionsSum": deductions_sum,
        "totalPay": total_pay,
        "netPay": net_pay,
        "expectedNetPay": expected_net,
        "totalMatches": total_matches,
        "netMatches": net_matches,
        "mismatches": mismatches,
    }
