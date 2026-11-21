"""서류 평가 — FS-01 단계 5~6 (BR-03~06, NFR-07·08).

금액·시간 문구는 이 모듈의 템플릿이 만들고, CLOVA Studio는 근거 원문을 바탕으로 한 설명만 쓴다.
"""

import json
import logging
from dataclasses import asdict

from app.core.errors import AppError
from app.prompts import load
from app.schemas.contracts import CheckItem, ReviewRequest, ReviewResult, Source
from app.schemas.wage import WageCheckResponse
from app.services import clova_studio
from app.services.clova_studio import Message
from app.services.law_search import build_evidence_block, search_evidence
from app.services.number_guard import filter_unverified_sentences
from app.services.wage import WageCheckResult, check_wage

logger = logging.getLogger("app.review")

DISCLAIMER = (
    "이 결과는 법률 자문이 아니에요. 정확한 판단은 고용노동부 고객상담센터(국번 없이 1350) "
    "또는 대한법률구조공단(132)에 상담할 수 있어요."
)
SNIPPET_CHARS = 160
CONTEXT_CHARS = 800


def _fmt(n: float) -> str:
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:,}"


def build_items(req: ReviewRequest, c: WageCheckResult) -> tuple[list[CheckItem], list[str]]:
    """확인 항목과 근거 검색 키워드를 만든다."""
    items: list[CheckItem] = []
    keywords = ["최저임금"]

    if c.meets_minimum:
        items.append(
            CheckItem(
                level="ok",
                title="시급이 최저임금 이상이에요",
                description=(
                    f"{c.year}년 최저시급은 {_fmt(c.minimum_hourly)}원이고, "
                    f"계약 시급은 {_fmt(c.hourly_wage)}원이에요."
                ),
            )
        )
    else:
        items.append(
            CheckItem(
                level="check",
                title="시급이 최저임금보다 낮아요",
                description=(
                    f"{c.year}년 최저시급은 {_fmt(c.minimum_hourly)}원이에요. "
                    f"계약 시급 {_fmt(c.hourly_wage)}원은 시간당 {_fmt(c.shortfall_per_hour)}원 적어요."
                ),
            )
        )

    if c.weekly_holiday_eligible:
        keywords.append("주휴")
        items.append(
            CheckItem(
                level="check",
                title="주휴수당 대상이에요",
                description=(
                    f"1주 소정근로시간이 {_fmt(c.weekly_hours)}시간이라 주 15시간 이상이에요. "
                    f"계산상 주휴시간은 {_fmt(c.weekly_holiday_hours)}시간, "
                    f"주휴수당은 주 {_fmt(c.weekly_holiday_pay)}원이에요. "
                    "계약서·명세서에 주휴수당이 반영됐는지 확인해 보세요."
                ),
            )
        )
    else:
        items.append(
            CheckItem(
                level="ok",
                title="주휴수당 대상이 아니에요",
                description=f"1주 소정근로시간이 {_fmt(c.weekly_hours)}시간으로 주 15시간 미만이에요.",
            )
        )

    if req.break_minutes is not None and req.work_days:
        daily_hours = req.weekly_hours / len(req.work_days)
        required = 60 if daily_hours >= 8 else 30 if daily_hours >= 4 else 0
        if required and req.break_minutes < required:
            keywords.append("휴게")
            items.append(
                CheckItem(
                    level="check",
                    title="휴게시간이 짧을 수 있어요",
                    description=(
                        f"하루 약 {_fmt(round(daily_hours, 1))}시간 일하면 "
                        f"휴게시간이 {required}분 이상이어야 해요. "
                        f"입력된 휴게시간은 {req.break_minutes}분이에요."
                    ),
                )
            )
    return items, keywords


def _allowed_numbers(req: ReviewRequest, c: WageCheckResult) -> set[float]:
    values = {float(v) for v in asdict(c).values() if isinstance(v, int | float) and not isinstance(v, bool)}
    if req.break_minutes is not None:
        values.add(float(req.break_minutes))
    if req.work_days:
        values.add(float(len(req.work_days)))
    return values


async def explain(req: ReviewRequest, c: WageCheckResult, sources: list[dict]) -> str | None:
    """근거가 있을 때만 Studio 설명을 만든다. 실패하면 None (FS-01 예외 표)."""
    if not sources or not clova_studio.is_configured():
        return None
    calc = {k: v for k, v in asdict(c).items() if k != "notice"}
    context = build_evidence_block(sources, max_total_chars=CONTEXT_CHARS * len(sources))
    user = f"[계산 결과]\n{json.dumps(calc, ensure_ascii=False)}\n\n[근거 원문]\n{context}"
    try:
        text = await clova_studio.chat(
            [Message("system", load("review_explain_system")), Message("user", user)], temperature=0.3
        )
    except AppError as e:
        logger.info("explanation skipped: %s", e.code)
        return None
    kept, removed = filter_unverified_sentences(text, _allowed_numbers(req, c))
    if removed:
        logger.info("number guard removed %d sentence(s)", len(removed))
    return kept or None


async def review(req: ReviewRequest) -> ReviewResult:
    c = check_wage(req.hourly_wage, req.weekly_hours, req.year)
    items, keywords = build_items(req, c)
    found = search_evidence(keywords, limit=3)
    explanation = await explain(req, c, found)
    return ReviewResult(
        calculation=WageCheckResponse(**asdict(c)),
        items=items,
        explanation=explanation,
        sources=[
            Source(
                id=s["id"], title=s["title"], snippet=s["text"][:SNIPPET_CHARS] or None, url=s["sourceUrl"]
            )
            for s in found
        ],
        disclaimer=DISCLAIMER,
    )
