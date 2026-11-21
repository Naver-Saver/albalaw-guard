from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_id_generated_and_echoed():
    res = client.get("/api/health")
    assert res.headers["X-Request-ID"]
    res = client.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert res.headers["X-Request-ID"] == "abc123"


def test_not_found_uses_error_envelope():
    res = client.get("/api/nope")
    assert res.status_code == 404
    assert res.json() == {
        "success": False,
        "error": {"code": "NOT_FOUND", "message": "요청한 정보를 찾을 수 없어요."},
    }


def test_validation_error_envelope():
    res = client.post("/api/wage/check", json={"hourly_wage": -1, "weekly_hours": 20})
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "hourly_wage"


def test_business_error_envelope():
    res = client.post("/api/wage/check", json={"hourly_wage": 10000, "weekly_hours": 20, "year": 1999})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "BAD_REQUEST"
