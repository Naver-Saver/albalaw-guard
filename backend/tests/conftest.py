import pytest

from app.core.config import get_settings
from app.services import http


@pytest.fixture
def settings(monkeypatch):
    """테스트용 키를 넣은 설정. 실제 .env 값은 쓰지 않는다."""
    s = get_settings()
    monkeypatch.setattr(s, "clova_ocr_invoke_url", "https://ocr.test/general")
    monkeypatch.setattr(s, "clova_ocr_secret", "test-secret")
    monkeypatch.setattr(s, "clova_studio_api_key", "nv-test")
    monkeypatch.setattr(s, "clova_studio_request_id", "req-test")
    return s


@pytest.fixture
def mock_transport():
    """httpx.MockTransport 를 외부 호출에 꽂는다. 사용: mock_transport(handler)"""

    def install(handler):
        import httpx

        http.set_transport(httpx.MockTransport(handler))

    yield install
    http.set_transport(None)
