"""질문 라우팅 — FS-03, AI-05, BR-11~13.

텍스트 질문 → CLOVA Chatbot(FAQ). 일치하면 route="faq".
일치하지 않으면 근거 검색 → CLOVA Studio 설명, route="studio".
근거를 못 찾거나 설명을 못 만들면 route="none" (상담 안내 + 찾은 근거).
숫자는 코드가 확인한다: '주 N일 하루 M시간' 같은 질문은 주휴 대상 여부를 코드로 계산해 Studio에 넘기고,
설명에 근거·질문·계산에 없는 숫자가 있으면 그 문장을 지운다.
"""

import logging
import re

from app.core.errors import AppError
from app.prompts import load
from app.schemas.ask import AskResult
from app.schemas.contracts import Source
from app.services import calc, clova_chatbot, clova_studio
from app.services.clova_studio import Message
from app.services.law_search import build_evidence_block, get_source, keywords_of, search_evidence
from app.services.number_guard import filter_unverified_sentences, numbers_in

logger = logging.getLogger("app.ask")

SNIPPET_CHARS = 160
EVIDENCE_MAX_CHARS = 3000
MANUAL_LIMIT = 2
HEARD_NOTHING = "잘 못 들었어요. 텍스트로 질문해 주세요."
NO_EVIDENCE = (
    "관련 근거를 찾지 못했어요. 계약서 점검이나 급여명세서 점검 메뉴를 이용하시거나 "
    "고용노동부 고객상담센터(국번 없이 1350)에 문의해 주세요."
)
NO_EXPLANATION = (
    "설명을 불러오지 못했어요. 아래 근거를 확인해 보시고, 궁금한 점은 "
    "고용노동부 고객상담센터(국번 없이 1350)에 문의해 주세요."
)

_WEEK_HOURS = re.compile(r"주\s*(\d+(?:\.\d+)?)\s*시간")
_DAYS = re.compile(r"주\s*(\d+)\s*(?:일|번|회)")
_PER_DAY = re.compile(r"(?:하루|매일|일)\s*(\d+(?:\.\d+)?)\s*시간|(\d+(?:\.\d+)?)\s*시간씩")


def weekly_hours_from(question: str) -> tuple[float, str] | None:
    """질문에서 주 소정근로시간을 읽는다. ('주 15시간', '주 3일 하루 5시간')을 지원하고 못 읽으면 None."""
    direct = _WEEK_HOURS.search(question)
    if direct:
        return float(direct.group(1)), f"주 {direct.group(1)}시간"
    days, per_day = _DAYS.search(question), _PER_DAY.search(question)
    if days and per_day:
        d = int(days.group(1))
        h = float(per_day.group(1) or per_day.group(2))
        if 1 <= d <= 7 and 0 < h <= 24:
            return d * h, f"주 {d}일 × 하루 {h:g}시간"
    return None


def calculation_text(question: str) -> tuple[str, set[float]] | None:
    """[계산 결과] 문구와, 그 안의 숫자(검증 허용 목록)를 만든다. 계산할 게 없으면 None."""
    parsed = weekly_hours_from(question)
    if parsed is None:
        return None
    hours, how = parsed
    holiday = calc.weekly_holiday_hours(hours)
    lines = [f"주 소정근로시간: {hours:g}시간 ({how})"]
    if holiday > 0:
        lines.append(
            f"주휴수당 대상: 해당해요 (주 {calc.WEEKLY_HOLIDAY_MIN_HOURS}시간 이상), 주휴시간 {holiday:g}시간"
        )
    else:
        lines.append(f"주휴수당 대상: 해당하지 않아요 (주 {calc.WEEKLY_HOLIDAY_MIN_HOURS}시간 미만)")
    text = "\n".join(lines)
    return text, numbers_in(text) | {hours, holiday}


def faq_fits_question(question: str, reply: clova_chatbot.ChatbotAnswer) -> bool:
    """FAQ 답이 질문에 맞는지 한 번 더 본다. 정확 일치는 그대로 인정하고, 그 밖의 매칭(model)은
    질문의 핵심어가 하나라도 FAQ 답변이나 시나리오 이름에 나와야 한다(엉뚱한 FAQ 매칭 방지)."""
    if reply.matching_type == "exactMatch":
        return True
    return any(k in reply.text or k in (reply.scenario or "") for k in keywords_of(question))


def _to_source(item: dict) -> Source:
    return Source(
        id=item["id"],
        title=item["title"],
        snippet=item["text"][:SNIPPET_CHARS] or None,
        url=item["sourceUrl"] or None,
    )


def find_evidence(question: str, manual_limit: int = MANUAL_LIMIT) -> list[dict]:
    """질문과 관련된 쉬운 Q&A와 각 Q&A에 연결된 조문 1건을 찾는다 (중복 제거). Q&A가 없으면 조문 검색."""
    found: list[dict] = []
    seen: set[str] = set()

    def add(item: dict | None) -> None:
        if item and item["id"] not in seen:
            seen.add(item["id"])
            found.append(item)

    manuals = search_evidence(question, limit=manual_limit, sources=["MANUAL"])
    for m in manuals:
        add(m)
        for article_id in ((get_source(m["id"]) or {}).get("relatedArticleIds") or [])[:1]:
            add(get_source(article_id))
    if not manuals:
        for article in search_evidence(question, limit=manual_limit, sources=["LAW_API"]):
            add(article)
    return found


async def _explain(question: str, found: list[dict]) -> str | None:
    """근거 안에서만 설명을 만든다. 실패하거나 검증 후 남은 문장이 없으면 None."""
    if not clova_studio.is_configured():
        return None
    block = build_evidence_block(found, max_total_chars=EVIDENCE_MAX_CHARS)
    calc_part = calculation_text(question)
    user = f"[질문]\n{question}\n\n"
    allowed = numbers_in(question) | numbers_in(block)
    if calc_part:
        user += f"[계산 결과]\n{calc_part[0]}\n\n"
        allowed |= calc_part[1]
    user += f"[근거 원문]\n{block}"
    try:
        text = await clova_studio.chat([Message("system", load("ask_explain_system")), Message("user", user)])
    except AppError as e:
        logger.info("ask explanation skipped: %s", e.code)
        return None
    kept, removed = filter_unverified_sentences(text.replace("**", ""), allowed)  # 굵게(**) 표시 제거
    if removed:
        logger.info("number guard removed %d sentence(s)", len(removed))
    return kept or None


async def answer_question(question: str) -> AskResult:
    q = " ".join(question.split())[:300]
    if not q:
        return AskResult(question="", route="none", answer=HEARD_NOTHING, sources=[])

    # 1) FAQ (Chatbot). 실패해도 Studio 경로로 이어간다.
    # '주 10시간 일하면…'처럼 내 근무시간을 말한 질문은 일반 FAQ 답이 맞지 않을 수 있어(실제로 점수 0.73으로
    # 엉뚱한 FAQ가 걸림) 계산을 붙여 설명하는 Studio 경로로 바로 보낸다.
    if clova_chatbot.is_configured() and weekly_hours_from(q) is None:
        try:
            reply = await clova_chatbot.ask(q)
        except AppError as e:
            logger.info("chatbot skipped: %s", e.code)
        else:
            if reply.is_faq and reply.text and faq_fits_question(q, reply):
                sources = [_to_source(i) for i in find_evidence(q, manual_limit=1)]
                return AskResult(question=q, route="faq", answer=reply.text, sources=sources)

    # 2) 근거 검색 + Studio 설명
    found = find_evidence(q)
    if not found:
        return AskResult(question=q, route="none", answer=NO_EVIDENCE, sources=[])
    sources = [_to_source(i) for i in found]
    explanation = await _explain(q, found)
    if explanation:
        return AskResult(question=q, route="studio", answer=explanation, sources=sources)
    return AskResult(question=q, route="none", answer=NO_EXPLANATION, sources=sources)
