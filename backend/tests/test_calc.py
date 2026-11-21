import json
from datetime import date

import pytest

from app.services import calc
from sync.wage import parse_min_wage_csv
from tests.conftest import FIXTURE_DIR


@pytest.fixture
def wage_dir(tmp_path, monkeypatch):
    """CSV 샘플(tests/fixtures/min_wage_sample.csv)을 변환한 min-wage.json 을 LAW_DATA_DIR 로 지정."""
    items = parse_min_wage_csv(FIXTURE_DIR / "min_wage_sample.csv")
    (tmp_path / "min-wage.json").write_text(json.dumps({"syncedAt": "x", "items": items}), encoding="utf-8")
    monkeypatch.setenv("LAW_DATA_DIR", str(tmp_path))
    return {i["year"]: i for i in items}


def _today(monkeypatch, y, m=6, d=1):
    class FakeDate(date):
        @classmethod
        def today(cls):
            return cls(y, m, d)

    monkeypatch.setattr(calc, "date", FakeDate)


def test_get_min_wage_explicit_year(wage_dir):
    mw = calc.get_min_wage(2025)
    assert mw["hourlyWage"] == wage_dir[2025]["hourlyWage"]
    assert mw["isFallback"] is False
    assert set(mw) == {"year", "hourlyWage", "periodStart", "periodEnd", "isFallback"}


def test_get_min_wage_unknown_year_raises(wage_dir):
    with pytest.raises(calc.WageYearNotFound):
        calc.get_min_wage(1999)


def test_default_year_uses_this_year_when_present(wage_dir, monkeypatch):
    _today(monkeypatch, 2026)
    mw = calc.get_min_wage()
    assert mw["year"] == 2026 and mw["isFallback"] is False


def test_default_year_falls_back_to_latest(wage_dir, monkeypatch):
    latest = max(wage_dir)
    _today(monkeypatch, latest + 1, 1, 5)  # 새해 초: 새 연도 데이터가 아직 없음
    mw = calc.get_min_wage()
    assert mw["year"] == latest and mw["isFallback"] is True


def test_no_data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LAW_DATA_DIR", str(tmp_path))
    with pytest.raises(calc.WageYearNotFound):
        calc.get_min_wage()


def test_below_minimum_and_holiday_pay(wage_dir):
    minimum = wage_dir[2026]["hourlyWage"]
    r = calc.check_contract_wage(minimum - 320, 20, 2026)
    assert r["isBelowMinimum"] is True
    assert r["shortfallPerHour"] == 320
    assert r["weeklyHolidayEligible"] is True
    assert r["weeklyHolidayHours"] == 4.0
    assert r["weeklyHolidayPay"] == round(4.0 * minimum)  # 시급이 최저임금 미달이면 최저임금 기준 (BR-04)


def test_meets_minimum_uses_actual_wage_for_holiday_pay(wage_dir):
    wage = wage_dir[2026]["hourlyWage"] + 1000
    r = calc.check_contract_wage(wage, 40, 2026)
    assert r["isBelowMinimum"] is False and r["shortfallPerHour"] == 0
    assert r["weeklyHolidayHours"] == 8.0
    assert r["weeklyHolidayPay"] == 8 * wage


@pytest.mark.parametrize(("hours", "eligible"), [(14.9, False), (15, True), (52, True)])
def test_weekly_holiday_threshold(wage_dir, hours, eligible):
    r = calc.check_contract_wage(wage_dir[2026]["hourlyWage"], hours, 2026)
    assert r["weeklyHolidayEligible"] is eligible
    if not eligible:
        assert r["weeklyHolidayPay"] == 0
    if hours == 52:
        assert r["weeklyHolidayHours"] == 8.0  # 40시간 상한


@pytest.mark.parametrize(("wage", "hours"), [(0, 20), (-1, 20), (10000, 0), (10000, 169), (True, 20)])
def test_input_validation(wage_dir, wage, hours):
    with pytest.raises(ValueError):
        calc.check_contract_wage(wage, hours, 2026)


def test_contract_wage_unknown_year(wage_dir):
    with pytest.raises(calc.WageYearNotFound):
        calc.check_contract_wage(10000, 20, 1999)


def test_payslip_ok():
    r = calc.check_payslip_totals(
        [{"name": "기본급", "amount": 1000}, {"name": "주휴수당", "amount": 200}],
        [{"name": "세금", "amount": 100}],
        total_pay=1200,
        net_pay=1100,
    )
    assert r["totalMatches"] is True and r["netMatches"] is True
    assert r["mismatches"] == []
    assert (r["itemsSum"], r["deductionsSum"], r["expectedNetPay"]) == (1200, 100, 1100)


def test_payslip_mismatches():
    r = calc.check_payslip_totals([{"amount": 1000}], [{"amount": 100}], total_pay=1100, net_pay=900)
    assert r["totalMatches"] is False and r["netMatches"] is False
    fields = {m["field"]: m for m in r["mismatches"]}
    assert fields["totalPay"]["expected"] == 1000 and fields["totalPay"]["difference"] == 100
    assert fields["netPay"]["expected"] == 1000  # 총액(1100) - 공제(100)


def test_payslip_unknown_totals_skip_comparison():
    r = calc.check_payslip_totals([{"amount": 500}], [], total_pay=None, net_pay=None)
    assert r["totalMatches"] is None and r["netMatches"] is None and r["mismatches"] == []
    assert r["expectedNetPay"] == 500


def test_payslip_bad_amount():
    with pytest.raises(ValueError):
        calc.check_payslip_totals([{"name": "x", "amount": "천원"}], [], None, None)
