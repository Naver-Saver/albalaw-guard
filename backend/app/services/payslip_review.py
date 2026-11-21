"""급여명세서 점검 (파트 A). FS-01 급여명세서 흐름: 검산 · 필수 항목 · 최저임금·주휴수당 · 공제 확인.

문장과 금액은 코드 템플릿이 만든다 (NFR-08). 판단 근거는 calc(숫자), checklist(필수 항목),
law_search(법령 근거)이고, "위반"이라고 단정하지 않고 "확인이 필요해요"로 안내한다.
"""

import re

from app.schemas.contracts import CheckItem, Source
from app.schemas.payslips import (
    MissingField,
    PayslipMismatch,
    PayslipReviewRequest,
    PayslipReviewResult,
    PayslipTotals,
    PayslipWage,
)
from app.services import calc, checklist
from app.services.law_search import get_source, search_evidence

DISCLAIMER = (
    "이 결과는 법률 자문이 아니에요. 정확한 판단은 고용노동부 고객상담센터(국번 없이 1350) "
    "또는 대한법률구조공단(132)에 상담할 수 있어요."
)
SNIPPET_CHARS = 160

# 법령상 임금에서 함부로 뺄 수 없는 성격의 공제 이름 (근거: 근로기준법 제20·21·22·43조)
SUSPICIOUS_DEDUCTION = re.compile(r"위약|손해배상|벌금|교육비|강제\s*(저축|저금)|적금")
WEEKLY_HOLIDAY_ITEM = re.compile(r"주휴")

# 근거 검색 주제 → 검색어 (수동 Q&A 1건 + 그에 연결된 조문 1건)
TOPIC_QUERIES = {
    "payslip": "급여명세서",
    "min_wage": "최저임금",
    "weekly_holiday": "주휴수당",
    "deduction": "월급 공제",
    "penalty": "위약금 교육비 상계",
}


def _won(n: int | float) -> str:
    return f"{round(n):,}원"


def _fields(req: PayslipReviewRequest) -> dict:
    """checklist.find_missing 이 보는 필드 (이름·지급일은 값이 있는지만 쓴다)."""
    return {
        "employee_name": req.employee_name,
        "pay_date": req.pay_date,
        "total_pay": req.total_pay,
        "items": [i.name for i in req.items],
        "calculation_method": req.calculation_method,
        "deductions": [d.name for d in req.deductions],
    }


def _totals(req: PayslipReviewRequest) -> PayslipTotals:
    r = calc.check_payslip_totals(
        [i.model_dump() for i in req.items],
        [d.model_dump() for d in req.deductions],
        req.total_pay,
        req.net_pay,
    )
    return PayslipTotals(
        items_sum=r["itemsSum"],
        deductions_sum=r["deductionsSum"],
        total_pay=r["totalPay"],
        net_pay=r["netPay"],
        expected_net_pay=r["expectedNetPay"],
        total_matches=r["totalMatches"],
        net_matches=r["netMatches"],
        mismatches=[PayslipMismatch(**m) for m in r["mismatches"]],
    )


def _wage(req: PayslipReviewRequest) -> PayslipWage | None:
    """시급·주 소정근로시간을 둘 다 알 때만 최저임금·주휴수당을 계산한다. 연도 데이터가 없으면 건너뛴다."""
    if req.hourly_wage is None or req.weekly_hours is None:
        return None
    try:
        r = calc.check_contract_wage(req.hourly_wage, req.weekly_hours, req.year)
    except (ValueError, calc.WageYearNotFound):
        return None
    return PayslipWage(
        year=r["year"],
        minimum_wage=r["minimumWage"],
        hourly_wage=r["hourlyWage"],
        is_below_minimum=r["isBelowMinimum"],
        shortfall_per_hour=r["shortfallPerHour"],
        weekly_holiday_eligible=r["weeklyHolidayEligible"],
        weekly_holiday_hours=r["weeklyHolidayHours"],
        weekly_holiday_pay=r["weeklyHolidayPay"],
    )


def build_items(
    req: PayslipReviewRequest, totals: PayslipTotals, wage: PayslipWage | None, missing: list[MissingField]
) -> tuple[list[CheckItem], list[str]]:
    """확인 항목 문장과, 근거를 찾을 주제 목록(확인이 필요한 것 먼저)을 만든다."""
    checks: list[tuple[str, CheckItem]] = []  # (주제, 항목)

    # 1) 검산: 지급 항목 합 = 총액, 총액 - 공제 = 실지급액
    if totals.total_matches is True:
        checks.append(
            (
                "payslip",
                CheckItem(
                    level="ok",
                    title="지급 항목 합계와 총액이 같아요",
                    description=f"지급 항목을 더하면 {_won(totals.items_sum)}으로 총액과 같아요.",
                ),
            )
        )
    for m in totals.mismatches:
        if m.field == "totalPay":
            desc = (
                f"지급 항목을 더하면 {_won(m.expected)}인데 총액은 {_won(m.actual)}이에요. "
                f"{_won(abs(m.difference))} 차이가 나니 빠진 항목이 있는지 확인해 보세요."
            )
            title = "지급 항목 합계와 총액이 달라요"
        else:
            desc = (
                f"총액에서 공제 {_won(totals.deductions_sum)}을 빼면 {_won(m.expected)}인데 "
                f"실지급액은 {_won(m.actual)}이에요. {_won(abs(m.difference))} 차이가 나요."
            )
            title = "총액에서 공제를 뺀 금액과 실지급액이 달라요"
        checks.append(("payslip", CheckItem(level="check", title=title, description=desc)))
    if totals.net_matches is True:
        checks.append(
            (
                "payslip",
                CheckItem(
                    level="ok",
                    title="총액에서 공제를 뺀 금액이 실지급액과 같아요",
                    description=f"실지급액 {_won(totals.expected_net_pay)}이 계산과 맞아요.",
                ),
            )
        )

    # 2) 필수 항목 (근로기준법 시행령 제27조의2)
    required = [m.item for m in missing if not m.conditional]
    if required:
        checks.append(
            (
                "payslip",
                CheckItem(
                    level="check",
                    title="명세서에 있어야 할 항목이 빠져 있을 수 있어요",
                    description=", ".join(required)
                    + " 항목이 보이지 않아요. 명세서에 적혀 있는지 확인해 보세요.",
                ),
            )
        )
    by_key = {m.field_key: m for m in missing}
    if "calculation_method" in by_key:
        checks.append(
            (
                "payslip",
                CheckItem(
                    level="check",
                    title="항목별 계산방법이 적혀 있는지 확인해 보세요",
                    description=(
                        "근무시간 등에 따라 금액이 달라진다면 " "항목별 계산방법이 명세서에 적혀 있어야 해요."
                    ),
                ),
            )
        )
    if "deductions" in by_key and totals.total_pay is not None and totals.net_pay is not None:
        if totals.total_pay != totals.net_pay and not req.deductions:
            checks.append(
                (
                    "deduction",
                    CheckItem(
                        level="check",
                        title="공제 내역이 적혀 있지 않아요",
                        description=(
                            f"총액 {_won(totals.total_pay)}과 실지급액 {_won(totals.net_pay)}이 다른데 "
                            "공제 항목이 없어요. 무엇이 얼마 빠졌는지 확인해 보세요."
                        ),
                    ),
                )
            )

    # 3) 최저임금·주휴수당 (시급·주 소정근로시간을 입력한 경우)
    if wage is not None:
        if wage.is_below_minimum:
            checks.append(
                (
                    "min_wage",
                    CheckItem(
                        level="check",
                        title="시급이 최저임금보다 낮아요",
                        description=(
                            f"{wage.year}년 최저시급은 {_won(wage.minimum_wage)}이에요. "
                            f"입력한 시급 {_won(wage.hourly_wage)}은 "
                            f"시간당 {_won(wage.shortfall_per_hour)} 적어요."
                        ),
                    ),
                )
            )
        else:
            checks.append(
                (
                    "min_wage",
                    CheckItem(
                        level="ok",
                        title="시급이 최저임금 이상이에요",
                        description=(
                            f"{wage.year}년 최저시급은 {_won(wage.minimum_wage)}이고, "
                            f"입력한 시급은 {_won(wage.hourly_wage)}이에요."
                        ),
                    ),
                )
            )
        has_holiday_pay = any(WEEKLY_HOLIDAY_ITEM.search(i.name) for i in req.items)
        if wage.weekly_holiday_eligible and not has_holiday_pay:
            checks.append(
                (
                    "weekly_holiday",
                    CheckItem(
                        level="check",
                        title="주휴수당 항목이 보이지 않아요",
                        description=(
                            f"1주 소정근로시간이 {req.weekly_hours:g}시간이라 주 15시간 이상이에요. "
                            f"계산상 주휴수당은 주 {_won(wage.weekly_holiday_pay)}이에요. "
                            "기본급에 포함됐는지 확인해 보세요."
                        ),
                    ),
                )
            )

    # 4) 공제 이름 (위약금·교육비 등)
    odd = [d.name for d in req.deductions if SUSPICIOUS_DEDUCTION.search(d.name)]
    if odd:
        checks.append(
            (
                "penalty",
                CheckItem(
                    level="check",
                    title="임금에서 뺄 수 있는지 확인이 필요한 공제가 있어요",
                    description=(
                        ", ".join(odd) + " 항목이 공제돼 있어요. 위약금·교육비 같은 공제가 "
                        "법령상 가능한지 확인이 필요해요."
                    ),
                ),
            )
        )

    ordered = [c for c in checks if c[1].level == "check"] + [c for c in checks if c[1].level == "ok"]
    topics: list[str] = []
    for topic, _ in ordered:
        if topic not in topics:
            topics.append(topic)
    return [item for _, item in ordered], topics


def find_evidence(topics: list[str], extra_source_ids: list[str] | None = None) -> list[dict]:
    """주제마다 수동 Q&A 1건과 그에 연결된 조문 1건, 그리고 누락 항목의 근거 조문을 모은다 (중복 제거)."""
    found: list[dict] = []
    seen: set[str] = set()

    def add(item: dict | None) -> None:
        if item and item["id"] not in seen:
            seen.add(item["id"])
            found.append(item)

    for topic in topics:
        manuals = search_evidence(TOPIC_QUERIES[topic], limit=1, sources=["MANUAL"])
        for m in manuals:
            add(m)
            for article_id in ((get_source(m["id"]) or {}).get("relatedArticleIds") or [])[:1]:
                add(get_source(article_id))
    for source_id in extra_source_ids or []:
        add(get_source(source_id))
    return found


def review_payslip(req: PayslipReviewRequest) -> PayslipReviewResult:
    totals = _totals(req)
    wage = _wage(req)
    missing = [
        MissingField(
            item=m["item"], field_key=m["fieldKey"], source_ids=m["sourceIds"], conditional=m["conditional"]
        )
        for m in checklist.find_missing("PAYSLIP", _fields(req))
    ]
    items, topics = build_items(req, totals, wage, missing)
    required_missing_sources = [sid for m in missing if not m.conditional for sid in m.source_ids]
    found = find_evidence(topics, required_missing_sources)
    return PayslipReviewResult(
        totals=totals,
        wage=wage,
        missing=missing,
        items=items,
        sources=[
            Source(
                id=s["id"],
                title=s["title"],
                snippet=s["text"][:SNIPPET_CHARS] or None,
                url=s["sourceUrl"] or None,
            )
            for s in found
        ],
        disclaimer=DISCLAIMER,
    )
