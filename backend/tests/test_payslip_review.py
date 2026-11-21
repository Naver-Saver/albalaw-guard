import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import payslips
from app.core.config import get_settings
from app.core.response import register_exception_handlers
from app.schemas.payslips import PayslipLine, PayslipReviewRequest
from app.services import translate
from app.services.payslip_review import review_payslip


def _line(name, amount):
    return PayslipLine(name=name, amount=amount)


def _full(**over):
    """모든 필수 항목이 있고 숫자도 맞는 명세서."""
    base = dict(
        employee_name="가상인물",
        pay_date="2026-11-10",
        items=[_line("기본급", 800_000), _line("주휴수당", 160_000)],
        deductions=[_line("국민연금", 40_000)],
        total_pay=960_000,
        net_pay=920_000,
        calculation_method="시급 × 근무시간",
    )
    return PayslipReviewRequest(**{**base, **over})


def _titles(result, level=None):
    return [i.title for i in result.items if level is None or i.level == level]


def test_clean_payslip_has_no_check_items():
    r = review_payslip(_full())
    assert [i for i in r.items if i.level == "check"] == []
    assert r.totals.total_matches is True and r.totals.net_matches is True
    assert r.missing == [] or all(m.conditional for m in r.missing)
    assert "지급 항목 합계와 총액이 같아요" in _titles(r, "ok")


def test_total_mismatch_reports_amounts():
    r = review_payslip(_full(total_pay=1_000_000, net_pay=960_000))
    assert r.totals.total_matches is False
    item = next(i for i in r.items if i.title == "지급 항목 합계와 총액이 달라요")
    assert item.level == "check"
    assert "960,000원" in item.description and "1,000,000원" in item.description
    assert "40,000원 차이" in item.description


def test_net_mismatch_reports_amounts():
    r = review_payslip(_full(net_pay=900_000))
    item = next(i for i in r.items if i.title.startswith("총액에서 공제를 뺀 금액과 실지급액이"))
    assert "920,000원" in item.description and "900,000원" in item.description


def test_missing_required_items_listed_with_sources():
    r = review_payslip(_full(employee_name=None, pay_date=None))
    keys = {m.field_key for m in r.missing}
    assert {"employee_name", "pay_date"} <= keys
    item = next(i for i in r.items if i.title.startswith("명세서에 있어야 할 항목"))
    assert "임금지급일" in item.description
    assert any(s.id == "law-003058-27-2" for s in r.sources)  # 근거 조문이 출처에 포함


def test_calculation_method_is_a_check_but_not_a_required_item():
    r = review_payslip(_full(calculation_method=None))
    assert "항목별 계산방법이 적혀 있는지 확인해 보세요" in _titles(r, "check")
    assert not any(i.title.startswith("명세서에 있어야 할 항목") for i in r.items)


def test_deductions_missing_only_flagged_when_amounts_differ():
    r = review_payslip(_full(deductions=[], net_pay=960_000))  # 공제 없이 총액 = 실지급액
    assert "공제 내역이 적혀 있지 않아요" not in _titles(r)
    r2 = review_payslip(_full(deductions=[], net_pay=920_000))  # 차이가 있는데 공제 항목이 없음
    assert "공제 내역이 적혀 있지 않아요" in _titles(r2, "check")


def test_minimum_wage_and_weekly_holiday_item():
    r = review_payslip(
        _full(hourly_wage=9_000, weekly_hours=20, items=[_line("기본급", 960_000)], total_pay=960_000)
    )
    assert r.wage is not None and r.wage.is_below_minimum is True
    titles = _titles(r, "check")
    assert "시급이 최저임금보다 낮아요" in titles
    assert "주휴수당 항목이 보이지 않아요" in titles  # 주 15시간 이상인데 주휴수당 항목이 없음
    assert r.wage.weekly_holiday_pay > 0


def test_weekly_holiday_item_present_is_ok_and_short_hours_skip():
    r = review_payslip(_full(hourly_wage=12_000, weekly_hours=20))
    assert "주휴수당 항목이 보이지 않아요" not in _titles(r)
    assert "시급이 최저임금 이상이에요" in _titles(r, "ok")
    r2 = review_payslip(_full(hourly_wage=12_000, weekly_hours=10, items=[_line("기본급", 960_000)]))
    assert "주휴수당 항목이 보이지 않아요" not in _titles(r2)


def test_wage_needs_both_inputs_and_known_year():
    assert review_payslip(_full(hourly_wage=9_000)).wage is None
    assert review_payslip(_full(weekly_hours=20)).wage is None
    assert review_payslip(_full(hourly_wage=9_000, weekly_hours=20, year=1999)).wage is None


@pytest.mark.parametrize("name", ["위약금", "교육비 공제", "강제 저축", "손해배상", "벌금"])
def test_suspicious_deduction_names_are_flagged(name):
    r = review_payslip(_full(deductions=[_line(name, 40_000)]))
    item = next(i for i in r.items if i.title.startswith("임금에서 뺄 수 있는지"))
    assert name in item.description and item.level == "check"


@pytest.mark.parametrize("name", ["국민연금", "건강보험", "소득세", "고용보험"])
def test_ordinary_deductions_are_not_flagged(name):
    r = review_payslip(_full(deductions=[_line(name, 40_000)]))
    assert not any(i.title.startswith("임금에서 뺄 수 있는지") for i in r.items)


def test_check_items_come_before_ok_and_wording_is_not_assertive():
    r = review_payslip(_full(total_pay=1_000_000, hourly_wage=9_000, weekly_hours=20))
    levels = [i.level for i in r.items]
    assert levels == sorted(levels, key=lambda lv: lv != "check")
    text = " ".join(i.title + i.description for i in r.items)
    for banned in ("불법", "위법", "신고하세요"):
        assert banned not in text
    assert "법률 자문이 아니에요" in r.disclaimer


def test_sources_are_unique_and_have_urls():
    r = review_payslip(_full(deductions=[_line("교육비", 40_000)], hourly_wage=9_000, weekly_hours=20))
    ids = [s.id for s in r.sources]
    assert ids and len(ids) == len(set(ids))
    assert any(i.startswith("manual-") for i in ids) and any(i.startswith("law-") for i in ids)


def test_personal_values_are_not_echoed():
    r = review_payslip(_full(employee_name="홍길동", pay_date="2026-11-10"))
    dumped = json.dumps(r.model_dump(), ensure_ascii=False)
    assert "홍길동" not in dumped and "2026-11-10" not in dumped


# ---------- POST /payslips/review ----------

app = FastAPI()
register_exception_handlers(app)
app.include_router(payslips.router, prefix="/api")
client = TestClient(app)

BODY = {
    "items": [{"name": "기본급", "amount": 900_000}],
    "deductions": [{"name": "국민연금", "amount": 40_000}],
    "total_pay": 950_000,
    "net_pay": 910_000,
}


def test_route_ok():
    res = client.post("/api/payslips/review", json=BODY)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["totals"]["total_matches"] is False
    assert any(i["title"] == "지급 항목 합계와 총액이 달라요" for i in data["items"])
    assert {"totals", "wage", "missing", "items", "sources", "disclaimer"} <= set(data)


@pytest.mark.parametrize(
    "patch",
    [
        {"items": [{"name": "", "amount": 1}]},
        {"items": [{"name": "기본급", "amount": -1}]},
        {"items": [{"name": "기본급", "amount": 1}] * 31},
        {"lang": "xx"},
        {"hourly_wage": 0},
        {"weekly_hours": 169},
    ],
)
def test_route_validation(patch):
    res = client.post("/api/payslips/review", json={**BODY, **patch})
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_route_translates_explanations_only(mock_transport, monkeypatch):
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
    res = client.post("/api/payslips/review", json={**BODY, "lang": "en"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert all(i["title"].startswith("[en]") for i in data["items"])
    assert data["disclaimer"].startswith("[en]")
    assert not data["sources"][0]["title"].startswith("[en]")  # 출처 제목은 번역하지 않는다
    assert data["totals"]["items_sum"] == 900_000  # 숫자는 그대로


def test_route_translation_failure_keeps_korean(mock_transport, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "papago_client_id", "id")
    monkeypatch.setattr(s, "papago_client_secret", "secret")
    translate.clear_cache()
    mock_transport(lambda request: httpx.Response(500))
    res = client.post("/api/payslips/review", json={**BODY, "lang": "vi"})
    assert res.status_code == 200
    assert res.json()["data"]["items"][0]["title"] == "지급 항목 합계와 총액이 달라요"
