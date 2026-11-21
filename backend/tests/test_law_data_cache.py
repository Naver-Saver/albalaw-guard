"""law_data: 실제 NCP 버킷에서 읽을 때의 캐시·실패 기억·짧은 타임아웃 (#40)."""

import io
import json

import pytest
from botocore.exceptions import ClientError

from app.services import law_data
from app.services.storage import InMemoryObjectStorage, NcpObjectStorage, StorageKeys, set_storage

PAYLOAD = {"syncedAt": "bucket", "items": [{"year": 2999, "hourlyWage": 1}]}
KEY = StorageKeys.LAW_MIN_WAGE


class FakeS3:
    """boto3 클라이언트 대역: get_object 호출 수를 세고, 없는 키·장애를 흉내 낸다."""

    def __init__(self, objects: dict[str, dict] | None = None, fail: bool = False) -> None:
        self.objects = objects or {}
        self.fail = fail
        self.calls = 0

    def get_object(self, Bucket: str, Key: str):  # noqa: N803 (boto3 시그니처)
        self.calls += 1
        if self.fail:
            raise RuntimeError("network down")
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "x"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
                "GetObject",
            )
        return {"Body": io.BytesIO(json.dumps(self.objects[Key]).encode("utf-8"))}


@pytest.fixture
def ncp(monkeypatch):
    """NCP 스토리지로 보이게 하되, 읽기용 클라이언트는 FakeS3 로 바꿔 끼운다."""
    fake = FakeS3({KEY: PAYLOAD})
    monkeypatch.setattr(law_data, "_build_client", lambda: fake)
    set_storage(
        NcpObjectStorage(
            bucket="b",
            endpoint_url="https://kr.object.ncloudstorage.com",
            region_name="kr-standard",
            access_key="a",
            secret_key="s",
            client=object(),
        )
    )
    law_data.clear_cache()
    monkeypatch.delenv("LAW_DATA_DIR", raising=False)
    return fake


def test_reads_bucket_and_caches(ncp):
    for _ in range(3):
        assert law_data.read_json(law_data.MIN_WAGE_FILE) == PAYLOAD
    assert ncp.calls == 1


def test_clear_cache_refetches(ncp):
    law_data.read_json(law_data.MIN_WAGE_FILE)
    law_data.clear_cache()
    law_data.read_json(law_data.MIN_WAGE_FILE)
    assert ncp.calls == 2


def test_missing_object_falls_back_to_local_and_is_remembered(ncp):
    ncp.objects.clear()
    local = law_data.read_json(law_data.MIN_WAGE_FILE)
    assert local is not None and local["syncedAt"] != "bucket"  # backend/data/law-data/ 사본
    law_data.read_json(law_data.MIN_WAGE_FILE)
    assert ncp.calls == 1  # 없음도 잠시 기억해 요청마다 다시 묻지 않는다


def test_error_falls_back_without_raising_and_is_remembered(ncp):
    ncp.fail = True
    assert law_data.read_json(law_data.MIN_WAGE_FILE) is not None
    law_data.read_json(law_data.MIN_WAGE_FILE)
    assert ncp.calls == 1


def test_retries_after_miss_ttl(ncp, monkeypatch):
    ncp.fail = True
    law_data.read_json(law_data.MIN_WAGE_FILE)
    ncp.fail = False
    now = law_data.time.monotonic()
    monkeypatch.setattr(law_data.time, "monotonic", lambda: now + law_data.MISS_TTL_SEC + 1)
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == PAYLOAD
    assert ncp.calls == 2


def test_each_file_is_cached_separately(ncp):
    ncp.objects[StorageKeys.LAW_QNA_MANUAL] = {"items": []}
    law_data.read_json(law_data.MIN_WAGE_FILE)
    law_data.read_json(law_data.QNA_MANUAL_FILE)
    law_data.read_json(law_data.MIN_WAGE_FILE)
    law_data.read_json(law_data.QNA_MANUAL_FILE)
    assert ncp.calls == 2


def test_swapping_storage_drops_old_cache(ncp):
    law_data.read_json(law_data.MIN_WAGE_FILE)
    set_storage(InMemoryObjectStorage())  # 다른 스토리지로 교체
    local = law_data.read_json(law_data.MIN_WAGE_FILE)
    assert local is not None and local["syncedAt"] != "bucket"


def test_in_memory_storage_is_not_cached():
    """로컬 개발·테스트용 In-Memory 는 쓰자마자 읽혀야 한다 (캐시·실패 기억 없음)."""
    storage = InMemoryObjectStorage()
    set_storage(storage)
    first = law_data.read_json(law_data.MIN_WAGE_FILE)  # 버킷에 없음 → 로컬 사본
    storage.put_json(KEY, PAYLOAD)
    assert first != PAYLOAD
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == PAYLOAD


def test_law_data_dir_override_never_touches_bucket(ncp, tmp_path, monkeypatch):
    monkeypatch.setenv("LAW_DATA_DIR", str(tmp_path))
    assert law_data.read_json(law_data.MIN_WAGE_FILE) is None
    assert ncp.calls == 0


def test_reader_client_has_short_timeouts():
    client = law_data._build_client()  # 네트워크 호출 없이 설정만 확인
    cfg = client.meta.config
    assert cfg.connect_timeout == law_data.STORAGE_CONNECT_TIMEOUT_SEC
    assert cfg.read_timeout == law_data.STORAGE_READ_TIMEOUT_SEC
    # boto3 는 max_attempts(재시도 횟수)를 total_max_attempts(첫 시도 포함 총 횟수)로 바꿔 저장한다
    assert cfg.retries["total_max_attempts"] == law_data.STORAGE_MAX_ATTEMPTS + 1


def test_reader_uses_shared_bucket(ncp):
    law_data.read_json(law_data.MIN_WAGE_FILE)
    assert law_data._fast_reader is not None and law_data._fast_reader.bucket == "b"


def _after(monkeypatch, seconds: float) -> None:
    now = law_data.time.monotonic()
    monkeypatch.setattr(law_data.time, "monotonic", lambda: now + seconds)


def test_hit_expires_after_cache_ttl_and_refetches(ncp, monkeypatch):
    """정기 수집으로 버킷이 갱신되면 캐시 시간이 지난 뒤 재시작 없이 반영된다 (#43)."""
    law_data.read_json(law_data.MIN_WAGE_FILE)
    ncp.objects[KEY] = {"syncedAt": "new", "items": []}
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == PAYLOAD  # 캐시 시간 안
    _after(monkeypatch, law_data.cache_ttl() + 1)
    assert law_data.read_json(law_data.MIN_WAGE_FILE)["syncedAt"] == "new"
    assert ncp.calls == 2


def test_refetch_failure_keeps_last_bucket_data(ncp, monkeypatch):
    law_data.read_json(law_data.MIN_WAGE_FILE)
    ncp.fail = True
    _after(monkeypatch, law_data.cache_ttl() + 1)
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == PAYLOAD  # 로컬 사본이 아닌 직전 버킷 값
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == PAYLOAD  # 실패 기억 중에도 유지
    assert ncp.calls == 2
