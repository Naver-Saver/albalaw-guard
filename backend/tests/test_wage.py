import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.wage import check_wage, weekly_holiday_hours

client = TestClient(app)


@pytest.mark.parametrize(
    ("weekly_hours", "expected"),
    [(14.9, 0.0), (15, 3.0), (20, 4.0), (40, 8.0), (52, 8.0)],
)
def test_weekly_holiday_hours(weekly_hours, expected):
    assert weekly_holiday_hours(weekly_hours) == expected


def test_below_minimum_2026():
    r = check_wage(hourly_wage=10_000, weekly_hours=20, year=2026)
    assert r.meets_minimum is False
    assert r.shortfall_per_hour == 320
    # 주휴수당은 최저임금 이상 시급 기준으로 계산
    assert r.weekly_holiday_pay == 4 * 10_320


def test_meets_minimum_2027():
    r = check_wage(hourly_wage=10_700, weekly_hours=40, year=2027)
    assert r.meets_minimum is True
    assert r.weekly_holiday_pay == 8 * 10_700


def test_api_wage_check_envelope():
    res = client.post("/api/wage/check", json={"hourly_wage": 10000, "weekly_hours": 20, "year": 2026})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["meets_minimum"] is False
    assert data["weekly_holiday_pay"] == 41_280
