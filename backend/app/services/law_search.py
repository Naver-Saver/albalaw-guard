"""법령 근거 검색 (파트 A). 1단계는 키워드 검색 — 임베딩은 사용하지 않는다.

근거 출처(source):
- MANUAL    : 법령 조문을 바탕으로 정리한 수동 Q&A (쉬운 설명, 우선 노출)
- LAW_API   : 국가법령정보센터 조문 원문
(공공데이터포털 백문백답 API 복구 시 QNA100 등 추가 가능)
"""

import re
import threading

from app.services import law_data

MAX_TEXT_CHARS = 800
SOURCE_PRIORITY = {"MANUAL": 1.5, "QNA100": 1.5, "LIFELAW_RULE": 1.2, "LIFELAW_FAQ": 1.2, "LAW_API": 1.0}

# 한국어 조사·어미 (검색어 끝에서 떼어 내 어간을 한 번 더 시도)
_PARTICLES = (
    "에서는",
    "으로는",
    "에게는",
    "이란",
    "라는",
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "하면",
    "하는",
    "해요",
    "인가요",
    "나요",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "도",
    "만",
    "로",
    "과",
    "와",
)
# 거의 모든 근거에 나오는 말(근로자·사업주 등)과 질문투 말은 검색어에서 뺀다
_STOPWORDS = {
    "어떻게",
    "무엇",
    "어떤",
    "있나요",
    "되나요",
    "하나요",
    "경우",
    "대해",
    "관련",
    "알려줘",
    "없이",
    "일해요",
    "근로자",
    "사용자",
    "사업주",
    "사장",
    "사장님",
}
MIN_RELATIVE_SCORE = 0.3  # 1위 점수의 30% 미만인 결과는 노이즈로 보고 버린다

_lock = threading.Lock()
_index: dict[str, dict] = {}
_ordered: list[dict] = []
_loaded = False


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _normalize_manual(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "source": "MANUAL",
        "title": raw["question"],
        "text": raw["answer"],
        "sourceUrl": raw.get("sourceUrl", ""),
        "_keywords": raw.get("keywords", []),
        "_extra": " ".join([raw.get("category", ""), raw.get("relatedLaw", "")]),
        "relatedArticleIds": raw.get("relatedArticleIds", []),
    }


def _normalize_article(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "source": "LAW_API",
        "title": f"{raw['lawName']} {raw['articleNo']}({raw['title']})"
        if raw.get("title")
        else f"{raw['lawName']} {raw['articleNo']}",
        "text": raw["text"],
        "sourceUrl": raw.get("sourceUrl", ""),
        "_keywords": [],
        "_extra": raw.get("chapter", ""),
        "relatedArticleIds": [],
    }


def load_law_data() -> None:
    """서버 시작 시 1회 호출. law-data/*.json 을 메모리에 적재한다 (다시 호출하면 새로 읽음)."""
    global _index, _ordered, _loaded
    items: list[dict] = []
    manual = law_data.read_json(law_data.QNA_MANUAL_FILE)
    if manual:
        items += [_normalize_manual(r) for r in manual.get("items", [])]
    articles = law_data.read_json(law_data.ARTICLES_FILE)
    if articles:
        items += [_normalize_article(r) for r in articles.get("items", [])]
    with _lock:
        _ordered = items
        _index = {i["id"]: i for i in items}
        _loaded = True


def _ensure_loaded() -> None:
    if not _loaded:
        load_law_data()


def _tokens(query: str | list[str]) -> list[str]:
    parts = query if isinstance(query, list) else [query]
    out: list[str] = []
    for part in parts:
        for tok in re.split(r"[^0-9A-Za-z가-힣%]+", part or ""):
            if len(tok) < 2 or tok in _STOPWORDS:
                continue
            out.append(tok)
            for p in _PARTICLES:  # 조사 제거 어간
                if tok.endswith(p) and len(tok) - len(p) >= 2:
                    out.append(tok[: -len(p)])
                    break
    seen: set[str] = set()
    return [t for t in out if not (t in seen or seen.add(t))]


def _score(item: dict, tokens: list[str]) -> float:
    title, text = item["title"], item["text"]
    keywords = " ".join(item["_keywords"])
    extra = item["_extra"]
    total = 0.0
    for tok in tokens:
        weight = 1.0 + min(len(tok), 6) * 0.1  # 긴 단어가 더 구체적
        if tok in keywords:
            total += 4 * weight
        if tok in title:
            total += 3 * weight
        if tok in extra:
            total += 1 * weight
        if tok in text:
            total += 1 * weight
    return total * SOURCE_PRIORITY.get(item["source"], 1.0)


def _public(item: dict) -> dict:
    return {
        "id": item["id"],
        "source": item["source"],
        "title": item["title"],
        "text": _truncate(item["text"]),
        "sourceUrl": item["sourceUrl"],
    }


def search_evidence(query: str | list[str], limit: int = 5, sources: list[str] | None = None) -> list[dict]:
    """키워드(또는 문장)로 근거 검색. 점수 높은 순 상위 limit개 (점수 0은 제외)."""
    _ensure_loaded()
    tokens = _tokens(query)
    if not tokens or limit <= 0:
        return []
    scored = []
    for item in _ordered:
        if sources and item["source"] not in sources:
            continue
        s = _score(item, tokens)
        if s > 0:
            scored.append((s, item))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    if scored:
        floor = scored[0][0] * MIN_RELATIVE_SCORE
        scored = [pair for pair in scored if pair[0] >= floor]
    return [_public(item) for _, item in scored[:limit]]


def get_source(source_id: str) -> dict | None:
    """근거 원문 단건 조회 (출처 클릭용). text는 자르지 않는다."""
    _ensure_loaded()
    item = _index.get(source_id)
    if item is None:
        return None
    out = {k: item[k] for k in ("id", "source", "title", "text", "sourceUrl")}
    if item["relatedArticleIds"]:
        out["relatedArticleIds"] = item["relatedArticleIds"]
    return out


def build_evidence_block(items: list[dict], max_total_chars: int = 4000) -> str:
    """Studio 프롬프트의 [법령 근거] 블록. 각 근거 앞에 (id) 표기, 전체 max_total_chars 이내."""
    lines: list[str] = []
    used = 0
    for item in items:
        entry = f"({item['id']}) {item['title']}\n{_truncate(item['text'])}"
        if used + len(entry) > max_total_chars:
            remain = max_total_chars - used
            if remain > 80:  # 남은 공간이 충분하면 잘라서 넣고 종료
                lines.append(_truncate(entry, remain))
            break
        lines.append(entry)
        used += len(entry) + 2
    return "\n\n".join(lines)
