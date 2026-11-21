import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import law, wage
from app.core.response import register_exception_handlers
from sync.wage import parse_min_wage_csv
from tests.conftest import FIXTURE_DIR

# main.py(담당 B)에 law 라우터가 등록되기 전에도 검증할 수 있도록 테스트 전용 앱을 만든다.
app = FastAPI()
register_exception_handlers(app)
app.include_router(law.router, prefix="/api")
app.include_router(wage.router, prefix="/api")
client = TestClient(app)


def test_qa_search(law_data_dir):
    res = client.get("/api/qa/search", params={"q": "주휴수당", "limit": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert items and items[0]["id"] == "manual-t01"
    assert set(items[0]) == {"id", "source", "title", "snippet", "url"}
    assert len(items) <= 2


def test_qa_search_validation(law_data_dir):
    for params in ({}, {"q": ""}, {"q": "휴게", "limit": 11}):
        res = client.get("/api/qa/search", params=params)
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_qa_search_no_result(law_data_dir):
    res = client.get("/api/qa/search", params={"q": "zzzz없는단어"})
    assert res.json() == {"success": True, "data": {"items": []}}


def test_law_source(law_data_dir):
    res = client.get("/api/law/sources/manual-t01")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["related_article_ids"] == ["law-t-55"] and data["url"].endswith("manual-t01")


def test_law_source_not_found(law_data_dir):
    res = client.get("/api/law/sources/nope")
    assert res.status_code == 404
    assert res.json()["success"] is False
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.fixture
def wage_dir(tmp_path, monkeypatch):
    items = parse_min_wage_csv(FIXTURE_DIR / "min_wage_sample.csv")
    (tmp_path / "min-wage.json").write_text(json.dumps({"syncedAt": "x", "items": items}), encoding="utf-8")
    monkeypatch.setenv("LAW_DATA_DIR", str(tmp_path))
    return {i["year"]: i for i in items}


def test_minimum_wage_with_year(wage_dir):
    res = client.get("/api/wage/minimum", params={"year": 2025})
    assert res.status_code == 200
    assert res.json() == {
        "success": True,
        "data": {
            "year": 2025,
            "hourly_wage": wage_dir[2025]["hourlyWage"],
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "is_fallback": False,
        },
    }


def test_minimum_wage_unknown_year_404(wage_dir):
    res = client.get("/api/wage/minimum", params={"year": 1999})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_minimum_wage_invalid_year_422(wage_dir):
    res = client.get("/api/wage/minimum", params={"year": "abc"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_minimum_wage_default_year_has_flag(wage_dir):
    data = client.get("/api/wage/minimum").json()["data"]
    assert data["year"] in wage_dir and isinstance(data["is_fallback"], bool)
