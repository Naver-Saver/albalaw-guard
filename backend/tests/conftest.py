import shutil
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services import http, storage
from app.services.storage import InMemoryObjectStorage

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolate_storage():
    """모든 테스트가 실제 .env의 NCP Object Storage를 호출하지 않도록 인메모리로 격리한다."""
    from app.services import law_data

    storage.set_storage(InMemoryObjectStorage())
    law_data.clear_cache()  # 근거 데이터 TTL 캐시가 테스트 사이에 새지 않도록
    yield
    storage.set_storage(None)
    law_data.clear_cache()


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


@pytest.fixture
def law_data_dir(tmp_path, monkeypatch):
    """tests/fixtures/law-data 를 임시 폴더에 복사해 LAW_DATA_DIR 로 지정하고, 검색 인덱스를 새로 읽는다."""
    target = tmp_path / "law-data"
    shutil.copytree(FIXTURE_DIR / "law-data", target)
    monkeypatch.setenv("LAW_DATA_DIR", str(target))
    from app.services import law_search

    law_search.load_law_data()
    yield target
    monkeypatch.delenv("LAW_DATA_DIR", raising=False)
    law_search.load_law_data()
