import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import review

client = TestClient(app)

EVIDENCE = [
    {
        "id": "MANUAL-1",
        "source": "MANUAL",
        "title": "주휴수당은 누가 받을 수 있나요?",
        "text": "1주 소정근로시간이 15시간 이상인 근로자는 …",
        "sourceUrl": "https://www.law.go.kr/",
    },
    {
        "id": "LAW-1",
        "source": "LAW_API",
        "title": "최저임금법 제6조",
        "text": "사용자는 최저임금의 적용을 받는 근로자에게 최저임금액 이상의 임금을 지급하여야 한다.",
        "sourceUrl": "https://www.law.go.kr/",
    },
]


@pytest.fixture
def index(monkeypatch):
    monkeypatch.setattr(review, "find_evidence", lambda topics: list(EVIDENCE))


def _post(**body):
    return client.post("/api/contracts/review", json={"year": 2026, **body})


def test_ac02_below_minimum_with_weekly_holiday(monkeypatch):
    monkeypatch.setattr("app.services.clova_studio.is_configured", lambda: False)
    res = _post(hourly_wage=10_000, weekly_hours=20)
    assert res.status_code == 200
    d = res.json()["data"]
    assert d["calculation"]["shortfall_per_hour"] == 320
    assert d["calculation"]["weekly_holiday_pay"] == 41_280
    titles = [i["title"] for i in d["items"]]
    assert "시급이 최저임금보다 낮아요" in titles and "주휴수당 대상이에요" in titles
    assert "41,280원" in d["items"][1]["description"]
    assert "1350" in d["disclaimer"] and d["explanation"] is None


def test_ac03_under_15_hours(monkeypatch):
    monkeypatch.setattr("app.services.clova_studio.is_configured", lambda: False)
    d = _post(hourly_wage=10_320, weekly_hours=14).json()["data"]
    assert d["calculation"]["weekly_holiday_eligible"] is False
    assert d["calculation"]["weekly_holiday_pay"] == 0
    assert all(i["level"] == "ok" for i in d["items"])


def test_break_time_check():
    d = _post(
        hourly_wage=10_320, weekly_hours=40, work_days=["월", "화", "수", "목", "금"], break_minutes=30
    ).json()["data"]
    assert any(i["title"] == "휴게시간이 짧을 수 있어요" for i in d["items"])


def test_explanation_with_sources_and_number_guard(settings, mock_transport, index):
    content = "시급이 최저임금 10,320원보다 320원 낮아요. 매달 77,777원을 손해 봐요. 1350에 상담해 보세요."
    mock_transport(
        lambda r: httpx.Response(
            200,
            json={
                "status": {"code": "20000"},
                "result": {"message": {"role": "assistant", "content": content}},
            },
        )
    )
    d = _post(hourly_wage=10_000, weekly_hours=20).json()["data"]
    assert {s["id"] for s in d["sources"]} == {"MANUAL-1", "LAW-1"}
    assert "77,777" not in d["explanation"]  # AC-06
    assert "10,320원" in d["explanation"]


def test_studio_failure_returns_null_explanation(settings, mock_transport, index):
    mock_transport(lambda r: httpx.Response(500))
    res = _post(hourly_wage=10_000, weekly_hours=20)
    assert res.status_code == 200
    assert res.json()["data"]["explanation"] is None
    assert len(res.json()["data"]["sources"]) == 2


def test_unknown_year():
    res = _post(hourly_wage=10_000, weekly_hours=20, year=1999)
    assert res.status_code == 400 and res.json()["error"]["code"] == "BAD_REQUEST"


def test_review_uses_real_evidence_data(monkeypatch):
    """근거 검색은 law-data/*.json(law_search)을 쓴다 — 실제 데이터로 1건 이상."""
    monkeypatch.setattr("app.services.clova_studio.is_configured", lambda: False)
    d = _post(hourly_wage=10_000, weekly_hours=20).json()["data"]
    assert d["sources"] and all(s["id"] and s["title"] for s in d["sources"])


def test_evidence_covers_each_check_topic():
    """주휴수당 대상 + 최저임금 미달이면 두 주제의 근거가 모두 들어가야 한다 (#37)."""
    from app.services.wage import check_wage

    req = review.ReviewRequest(hourly_wage=10_000, weekly_hours=17.5, year=2026)
    items, topics = review.build_items(req, check_wage(10_000, 17.5, 2026))
    assert topics[:2] == ["min_wage", "weekly_holiday"]
    found = review.find_evidence(topics)
    text = " ".join(f"{e['title']} {e['text']}" for e in found)
    assert "최저임금" in text and "주휴" in text
    assert any(e["source"] == "LAW_API" for e in found)  # 연결 조문 포함
    assert len({e["id"] for e in found}) == len(found)


def test_check_topics_come_first():
    from app.services.wage import check_wage

    req = review.ReviewRequest(
        hourly_wage=10_320,
        weekly_hours=40,
        work_days=["월", "화", "수", "목", "금"],
        break_minutes=30,
        year=2026,
    )
    _, topics = review.build_items(req, check_wage(10_320, 40, 2026))
    # 최저임금은 충족(ok)이라 뒤로, 주휴·휴게(check)가 앞
    assert topics == ["weekly_holiday", "break_time", "min_wage"]


def test_prompt_lists_check_items():
    from app.services.wage import check_wage

    c = check_wage(10_000, 17.5, 2026)
    req = review.ReviewRequest(hourly_wage=10_000, weekly_hours=17.5, year=2026)
    items, _ = review.build_items(req, c)
    prompt = review.build_user_prompt(c, items, list(EVIDENCE))
    assert "[확인 항목]" in prompt and "[확인 필요] 주휴수당 대상이에요" in prompt
    assert "(MANUAL-1)" in prompt


def test_number_guard_keeps_statute_references():
    from app.services.number_guard import filter_unverified_sentences

    kept, removed = filter_unverified_sentences("근로기준법 제55조에 따라 유급휴일을 줘야 해요.", {10_320.0})
    assert removed == [] and "제55조" in kept
    _, removed = filter_unverified_sentences("매달 77,777원을 더 받아요.", {10_320.0})
    assert removed
