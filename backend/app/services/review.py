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
from app.services.law_search import build_evidence_block, get_source, search_evidence
from app.services.number_guard import filter_unverified_sentences, numbers_in
from app.services.wage import WageCheckResult, check_wage

logger = logging.getLogger("app.review")

DISCLAIMER = (
    "이 결과는 법률 자문이 아니에요. 정확한 판단은 고용노동부 고객상담센터(국번 없이 1350) "
    "또는 대한법률구조공단(132)에 상담할 수 있어요."
)
SNIPPET_CHARS = 160
EVIDENCE_MAX_CHARS = 4000  # Studio 프롬프트 [근거 원문] 전체 길이

# 확인 항목 주제별 근거 검색어.
# 주제마다 따로 검색해야 한 주제(문항 수가 많은 최저임금)가 근거를 독식하지 않는다.
TOPIC_QUERIES = {
    "min_wage": "최저임금",
    "weekly_holiday": "주휴수당",
    "break_time": "휴게시간",
}
MANUAL_PER_TOPIC = 1  # 주제마다 쉬운 설명(수동 Q&A) 1건
ARTICLES_PER_TOPIC = 1  # + 그 Q&A에 연결된 법령 조문 1건


def _fmt(n: float) -> str:
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:,}"


def build_items(req: ReviewRequest, c: WageCheckResult) -> tuple[list[CheckItem], list[str]]:
    """확인 항목과 근거를 찾을 주제를 만든다. 주제는 '확인 필요(check)' 항목이 먼저 오도록 정렬한다."""
    items: list[CheckItem] = []
    topics: list[tuple[str, str]] = []  # (주제, level)

    topics.append(("min_wage", "ok" if c.meets_minimum else "check"))
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

    topics.append(("weekly_holiday", "check" if c.weekly_holiday_eligible else "ok"))
    if c.weekly_holiday_eligible:
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
            topics.append(("break_time", "check"))
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
    ordered = [t for t, level in topics if level == "check"] + [t for t, level in topics if level == "ok"]
    return items, ordered


def find_evidence(topics: list[str]) -> list[dict]:
    """주제마다 수동 Q&A와 그에 연결된 법령 조문을 모은다 (중복 제거, 주제 순서 유지)."""
    found: list[dict] = []
    seen: set[str] = set()

    def add(item: dict | None) -> None:
        if item and item["id"] not in seen:
            seen.add(item["id"])
            found.append(item)

    for topic in topics:
        manuals = search_evidence(TOPIC_QUERIES[topic], limit=MANUAL_PER_TOPIC, sources=["MANUAL"])
        if not manuals:  # 수동 Q&A가 없으면 조문 검색으로 대체
            manuals = search_evidence(TOPIC_QUERIES[topic], limit=MANUAL_PER_TOPIC)
        for m in manuals:
            add(m)
            related = (get_source(m["id"]) or {}).get("relatedArticleIds") or []
            for article_id in related[:ARTICLES_PER_TOPIC]:
                add(get_source(article_id))
    return found


def _allowed_numbers(req: ReviewRequest, c: WageCheckResult, items: list[CheckItem]) -> set[float]:
    values = {float(v) for v in asdict(c).values() if isinstance(v, int | float) and not isinstance(v, bool)}
    for item in items:  # 확인 항목 문구의 숫자는 코드 템플릿이 만든 값
        values |= numbers_in(item.description)
    if req.break_minutes is not None:
        values.add(float(req.break_minutes))
    if req.work_days:
        values.add(float(len(req.work_days)))
    return values


def build_user_prompt(c: WageCheckResult, items: list[CheckItem], sources: list[dict]) -> str:
    calc = {k: v for k, v in asdict(c).items() if k != "notice"}
    checks = "\n".join(
        f"- [{'확인 필요' if i.level == 'check' else '문제 없음'}] {i.title}: {i.description}" for i in items
    )
    context = build_evidence_block(sources, max_total_chars=EVIDENCE_MAX_CHARS)
    return (
        f"[확인 항목]\n{checks}\n\n"
        f"[계산 결과]\n{json.dumps(calc, ensure_ascii=False)}\n\n"
        f"[근거 원문]\n{context}"
    )


async def explain(
    req: ReviewRequest, c: WageCheckResult, items: list[CheckItem], sources: list[dict]
) -> str | None:
    """근거가 있을 때만 Studio 설명을 만든다. 실패하면 None (FS-01 예외 표)."""
    if not sources or not clova_studio.is_configured():
        return None
    user = build_user_prompt(c, items, sources)
    try:
        text = await clova_studio.chat(
            [Message("system", load("review_explain_system")), Message("user", user)], temperature=0.3
        )
    except AppError as e:
        logger.info("explanation skipped: %s", e.code)
        return None
    kept, removed = filter_unverified_sentences(text, _allowed_numbers(req, c, items))
    if removed:
        logger.info("number guard removed %d sentence(s)", len(removed))
    return kept or None


async def review(req: ReviewRequest) -> ReviewResult:
    c = check_wage(req.hourly_wage, req.weekly_hours, req.year)
    items, topics = build_items(req, c)
    found = find_evidence(topics)
    explanation = await explain(req, c, items, found)
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
