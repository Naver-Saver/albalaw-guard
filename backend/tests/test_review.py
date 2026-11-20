import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import law_qa
from app.services.law_qa import LawQa, LawQaIndex

client = TestClient(app)

QA = [
    LawQa(
        id="qa-1",
        title="주휴수당은 누가 받을 수 있나요?",
        answer="1주 소정근로시간이 15시간 이상인 근로자는 …",
        keywords=("주휴",),
    ),
    LawQa(
        id="qa-2",
        title="최저임금보다 적게 받으면?",
        answer="최저임금액 이상을 지급해야 …",
        keywords=("최저임금",),
    ),
]


@pytest.fixture
def index(monkeypatch):
    monkeypatch.setattr(law_qa, "get_index", lambda: LawQaIndex(list(QA)))
    from app.services import review

    monkeypatch.setattr(review, "get_index", lambda: LawQaIndex(list(QA)))


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
    assert {s["id"] for s in d["sources"]} == {"qa-1", "qa-2"}
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


def test_search_ranks_title_hits():
    idx = LawQaIndex(list(QA))
    assert idx.search(["주휴"])[0].id == "qa-1"
    assert idx.search(["없는키워드"]) == []
