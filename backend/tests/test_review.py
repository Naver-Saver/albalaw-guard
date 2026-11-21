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
    monkeypatch.setattr(review, "search_evidence", lambda keywords, limit=3: list(EVIDENCE))


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
