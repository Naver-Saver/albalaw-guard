from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_law_routes_registered_on_main_app():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:  # lifespan(근거 데이터 적재) 포함
        res = c.get("/api/qa/search", params={"q": "주휴수당"})
        assert res.status_code == 200 and res.json()["data"]["items"]
        first = res.json()["data"]["items"][0]["id"]
        assert c.get(f"/api/law/sources/{first}").status_code == 200
