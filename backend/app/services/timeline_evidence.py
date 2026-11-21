"""대화 타임라인 발언의 근거 찾기 (파트 A). FS-02 확장: 주요 발언마다 관련 근거와 '말로만 한 약속' 안내.

타임라인(C의 recordings)의 분류(임금·근무시간·휴게·휴일·약속·지시)와 발언 문장으로 근거를 검색한다.
"위반이다"라고 판단하지 않고, 관련 근거를 보여 주고 서면(계약서)으로 남기도록 안내만 한다.
"""

import re

from app.schemas.contracts import Source
from app.schemas.evidence import EntryEvidence, TimelineEvidenceRequest, TimelineEvidenceResult, TimelineInput
from app.services.law_search import search_evidence

DISCLAIMER = (
    "이 결과는 법률 자문이 아니에요. 정확한 판단은 고용노동부 고객상담센터(국번 없이 1350) "
    "또는 대한법률구조공단(132)에 상담할 수 있어요."
)
SNIPPET_CHARS = 160
SOURCES_PER_ENTRY = 2

# 분류만으로 찾을 때의 검색어 (발언 문장으로 찾지 못했을 때)
CATEGORY_QUERIES = {
    "임금": "최저임금",
    "근무시간": "근로시간",
    "휴게·휴일": "휴게시간 주휴수당",
    "약속·지시": "근로계약서",
    "기타": "",
}

# 말로 한 조건·약속처럼 보이는 표현 (금액·시간·수당·계약 관련)
PROMISE_MARKERS = re.compile(
    r"\d|만\s*원|올려|깎|줄게|주기로|해줄|안\s*줘도|안\s*써도|안\s*나가|나중에|알아서|구두|말로|따로"
)
PROMISE_CATEGORIES = {"임금", "근무시간", "휴게·휴일", "약속·지시"}
GUIDE_QUERY = "구두 약속 서면 계약서에 적어"
ADVICE = "말로만 한 조건이에요. 계약서나 문자로 남겨 달라고 요청해 보세요."
CHECKLIST = [
    "시급·근무시간·휴게시간을 계약서에 적어 달라고 요청하세요.",
    "급여를 받을 때 급여명세서(항목별 금액과 공제 내역)를 받아 두세요.",
    "말로 들은 조건은 문자나 메신저로 한 번 더 확인해 기록으로 남겨 두세요.",
]


def _to_source(item: dict) -> Source:
    return Source(
        id=item["id"],
        title=item["title"],
        snippet=item["text"][:SNIPPET_CHARS] or None,
        url=item["sourceUrl"] or None,
    )


def evidence_for(entry: TimelineInput) -> list[Source]:
    """발언 문장으로 수동 Q&A를 찾고, 없으면 분류 검색어로 대신 찾는다."""
    found = search_evidence(entry.text, limit=SOURCES_PER_ENTRY, sources=["MANUAL"])
    if not found and CATEGORY_QUERIES.get(entry.category):
        found = search_evidence(CATEGORY_QUERIES[entry.category], limit=1, sources=["MANUAL"])
    return [_to_source(item) for item in found]


def is_verbal_promise(entry: TimelineInput) -> bool:
    return entry.category in PROMISE_CATEGORIES and bool(PROMISE_MARKERS.search(entry.text))


def find_timeline_evidence(req: TimelineEvidenceRequest) -> TimelineEvidenceResult:
    entries: list[EntryEvidence] = []
    any_promise = False
    for index, entry in enumerate(req.entries):
        promise = is_verbal_promise(entry)
        any_promise = any_promise or promise
        sources = evidence_for(entry)
        if promise:  # 말로 한 조건은 서면으로 남기도록 하는 근거를 함께 보여 준다 (근로기준법 제17조)
            for guide in search_evidence(GUIDE_QUERY, limit=1, sources=["MANUAL"]):
                if all(s.id != guide["id"] for s in sources):
                    sources.append(_to_source(guide))
        entries.append(
            EntryEvidence(
                index=index,
                start_ms=entry.start_ms,
                sources=sources,
                verbal_promise=promise,
                advice=ADVICE if promise else None,
            )
        )
    return TimelineEvidenceResult(
        entries=entries,
        checklist_for_next_time=CHECKLIST if any_promise else CHECKLIST[:2],
        disclaimer=DISCLAIMER,
    )
