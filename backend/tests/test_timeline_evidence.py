import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import evidence
from app.core.config import get_settings
from app.core.response import register_exception_handlers
from app.schemas.evidence import TimelineEvidenceRequest, TimelineInput
from app.services import timeline_evidence as te
from app.services import translate


def _entry(text, category="임금", start_ms=1000, speaker="화자 B"):
    return TimelineInput(start_ms=start_ms, speaker=speaker, text=text, category=category)


def _req(*entries, lang="ko"):
    return TimelineEvidenceRequest(entries=list(entries), lang=lang)


@pytest.mark.parametrize(
    ("text", "category", "expected"),
    [
        ("이번 달부터 시급 만 원으로 할게", "임금", True),
        ("주휴수당은 따로 안 줘도 되지?", "임금", True),
        ("계약서는 나중에 써줄게", "약속·지시", True),
        ("쉬는 시간은 알아서 먹어", "휴게·휴일", True),
        ("안녕하세요 반갑습니다", "기타", False),
        ("오늘 날씨가 좋네요", "임금", False),
        ("시급 만 원으로 할게", "기타", False),  # 분류가 기타면 약속으로 보지 않는다
    ],
)
def test_verbal_promise_detection(text, category, expected):
    assert te.is_verbal_promise(_entry(text, category)) is expected


def test_promise_entry_gets_advice_and_guidance_source():
    r = te.find_timeline_evidence(_req(_entry("이번 달부터 시급 만 원으로 할게")))
    e = r.entries[0]
    assert e.verbal_promise is True and "계약서" in (e.advice or "")
    assert e.sources and all(s.id.startswith("manual-") for s in e.sources)
    assert len({s.id for s in e.sources}) == len(e.sources)
    assert len(e.sources) <= te.SOURCES_PER_ENTRY + 1


def test_non_promise_entry_has_no_advice():
    r = te.find_timeline_evidence(_req(_entry("안녕하세요 반갑습니다", "기타")))
    e = r.entries[0]
    assert e.verbal_promise is False and e.advice is None


def test_category_fallback_finds_evidence_when_sentence_has_no_keywords():
    r = te.find_timeline_evidence(_req(_entry("그렇게 하자고", "휴게·휴일")))
    assert r.entries[0].sources, "문장에서 못 찾아도 분류 검색어로 근거를 찾는다"


def test_keyword_sentences_find_relevant_topics():
    r = te.find_timeline_evidence(
        _req(
            _entry("수습 3개월은 월급 90%만 줄게", "임금"),
            _entry("쉬는 시간은 따로 없고 알아서 먹어", "휴게·휴일"),
            _entry("야근하면 수당은 안 나가", "임금"),
        )
    )
    titles = [" ".join(s.title for s in e.sources) for e in r.entries]
    assert "수습" in titles[0]
    assert "휴게" in titles[1]
    assert "야간" in titles[2] or "연장" in titles[2]


def test_indexes_and_start_ms_follow_request_order():
    r = te.find_timeline_evidence(
        _req(_entry("시급 만 원", start_ms=5000), _entry("월급 줄게", start_ms=9000))
    )
    assert [(e.index, e.start_ms) for e in r.entries] == [(0, 5000), (1, 9000)]


def test_checklist_and_disclaimer():
    with_promise = te.find_timeline_evidence(_req(_entry("시급 만 원으로 할게")))
    without = te.find_timeline_evidence(_req(_entry("안녕하세요", "기타")))
    assert len(with_promise.checklist_for_next_time) == 3 and len(without.checklist_for_next_time) == 2
    assert "법률 자문이 아니에요" in with_promise.disclaimer
    text = " ".join(with_promise.checklist_for_next_time) + (with_promise.entries[0].advice or "")
    assert not any(w in text for w in ("불법", "위법", "신고하세요"))


# ---------- POST /recordings/evidence ----------

app = FastAPI()
register_exception_handlers(app)
app.include_router(evidence.router, prefix="/api")
client = TestClient(app)


def _body(**over):
    return {
        "entries": [
            {
                "start_ms": 12000,
                "speaker": "화자 B",
                "text": "이번 달부터 시급 만 원으로 할게",
                "category": "임금",
            }
        ],
        **over,
    }


def test_route_ok():
    res = client.post("/api/recordings/evidence", json=_body())
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["entries"][0]["verbal_promise"] is True
    assert {"entries", "checklist_for_next_time", "disclaimer"} == set(data)


@pytest.mark.parametrize(
    "body",
    [
        {"entries": []},
        {"entries": [{"start_ms": 0, "speaker": "a", "text": "", "category": "임금"}]},
        {"entries": [{"start_ms": 0, "speaker": "a", "text": "x" * 501, "category": "임금"}]},
        {"entries": [{"start_ms": 0, "speaker": "a", "text": "x", "category": "없는분류"}]},
        {"entries": [{"start_ms": -1, "speaker": "a", "text": "x", "category": "임금"}]},
        _body(entries=[{"start_ms": 0, "speaker": "a", "text": "x", "category": "임금"}] * 51),
        _body(lang="xx"),
    ],
)
def test_route_validation(body):
    res = client.post("/api/recordings/evidence", json=body)
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_route_translates_advice_checklist_and_disclaimer_only(mock_transport, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "papago_client_id", "id")
    monkeypatch.setattr(s, "papago_client_secret", "secret")
    translate.clear_cache()

    def handler(request: httpx.Request):
        body = json.loads(request.read())
        return httpx.Response(
            200, json={"message": {"result": {"translatedText": f"[{body['target']}]{body['text']}"}}}
        )

    mock_transport(handler)
    res = client.post("/api/recordings/evidence", json=_body(lang="en"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["entries"][0]["advice"].startswith("[en]")
    assert all(c.startswith("[en]") for c in data["checklist_for_next_time"])
    assert data["disclaimer"].startswith("[en]")
    assert not data["entries"][0]["sources"][0]["title"].startswith("[en]")


def test_route_translation_failure_keeps_korean(mock_transport, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "papago_client_id", "id")
    monkeypatch.setattr(s, "papago_client_secret", "secret")
    translate.clear_cache()
    mock_transport(lambda request: httpx.Response(500))
    res = client.post("/api/recordings/evidence", json=_body(lang="vi"))
    assert res.status_code == 200
    assert res.json()["data"]["entries"][0]["advice"] == te.ADVICE
