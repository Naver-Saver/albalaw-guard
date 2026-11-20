import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.clova_ocr import fields_to_lines, recognize

client = TestClient(app)

OCR_BODY = {
    "images": [
        {
            "inferResult": "SUCCESS",
            "fields": [
                {"inferText": "근로계약서", "lineBreak": True},
                {"inferText": "시급", "lineBreak": False},
                {"inferText": "10,000원", "lineBreak": True},
                {"inferText": "근무일", "lineBreak": False},
                {"inferText": "월~금", "lineBreak": True},
            ],
        }
    ]
}


def test_fields_to_lines():
    assert fields_to_lines(OCR_BODY["images"][0]["fields"]) == ["근로계약서", "시급 10,000원", "근무일 월~금"]


async def test_recognize_sends_base64_and_secret(settings, mock_transport):
    seen = {}

    def handler(request: httpx.Request):
        seen["secret"] = request.headers["X-OCR-SECRET"]
        seen["body"] = request.read()
        return httpx.Response(200, json=OCR_BODY)

    mock_transport(handler)
    text = await recognize(b"fake-image", "png")
    assert seen["secret"] == "test-secret"
    assert b'"data"' in seen["body"] and b'"format":"png"' in seen["body"].replace(b" ", b"")
    assert text.lines[1] == "시급 10,000원"


async def test_recognize_retries_once_then_fails(settings, mock_transport):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    mock_transport(handler)
    from app.core.errors import OcrFailedError

    with pytest.raises(OcrFailedError):
        await recognize(b"x", "jpg")
    assert len(calls) == 2


def test_ocr_endpoint_ok(settings, mock_transport):
    mock_transport(lambda r: httpx.Response(200, json=OCR_BODY))
    res = client.post("/api/contracts/ocr", files={"file": ("c.png", b"img", "image/png")})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["doc_type"] == "contract"
    assert "시급 10,000원" in data["raw_text"]


def test_ocr_rejects_unsupported_type(settings):
    res = client.post("/api/contracts/ocr", files={"file": ("c.gif", b"img", "image/gif")})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNSUPPORTED_FILE"


def test_ocr_rejects_too_large(settings):
    big = b"0" * (10 * 1024 * 1024 + 1)
    res = client.post("/api/contracts/ocr", files={"file": ("c.jpg", big, "image/jpeg")})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_ocr_not_configured(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "clova_ocr_invoke_url", "")
    res = client.post("/api/contracts/ocr", files={"file": ("c.jpg", b"img", "image/jpeg")})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "SERVICE_NOT_CONFIGURED"


def test_ocr_upstream_failure(settings, mock_transport):
    mock_transport(lambda r: httpx.Response(401, json={"code": "0002"}))
    res = client.post("/api/contracts/ocr", files={"file": ("c.jpg", b"img", "image/jpeg")})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "OCR_FAILED"
