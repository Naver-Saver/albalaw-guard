"""법령·최저임금 JSON 로더 (파트 A·C 연동).

기본적으로 Object Storage(`law-data/*.json`)에서 읽고, 객체가 없거나 조회에 실패하면
로컬 `backend/data/law-data/`를 fallback으로 읽는다.
환경변수 `LAW_DATA_DIR`가 지정된 경우(테스트·로컬 오버라이드)에는 해당 로컬 폴더만 직접 읽는다.

실제 NCP 버킷에서 읽을 때는 서버가 막히거나 요청마다 네트워크를 타지 않도록:
- 읽은 JSON은 프로세스 안에 캐시한다. 법령 JSON을 갱신한 뒤에는 서버를 재시작해 반영한다(서버 1대 운영).
- 실패·없음은 MISS_TTL_SEC 동안 기억해 그동안은 버킷을 다시 부르지 않고 로컬 파일을 쓴다.
- 짧은 타임아웃(연결 3초·읽기 10초, 재시도 1회)의 전용 클라이언트를 쓴다.
(In-Memory 스토리지 등 NCP가 아닌 구현은 그대로 통과시킨다.)
"""

import json
import logging
import os
import threading
import time
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.config import get_settings
from app.services.storage import NcpObjectStorage, StorageKeys, get_storage

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "law-data"

ARTICLES_FILE = "law-articles.json"
QNA_MANUAL_FILE = "qna-manual.json"
MIN_WAGE_FILE = "min-wage.json"

STORAGE_CONNECT_TIMEOUT_SEC = 3
STORAGE_READ_TIMEOUT_SEC = 10
STORAGE_MAX_ATTEMPTS = 1
MISS_TTL_SEC = 60

_lock = threading.Lock()
_cache_owner: NcpObjectStorage | None = None  # 캐시가 어느 스토리지 기준인지 (set_storage 로 바뀌면 비움)
_hits: dict[str, dict] = {}  # 버킷에서 읽는 데 성공한 JSON
_misses: dict[str, float] = {}  # 실패·없음 → 다시 시도해도 되는 시각 (time.monotonic 기준)
_fast_reader: NcpObjectStorage | None = None


def data_dir() -> Path:
    return Path(os.environ.get("LAW_DATA_DIR") or DEFAULT_DATA_DIR)


def clear_cache() -> None:
    """버킷 읽기 캐시와 실패 기록을 비운다 (테스트·수동 갱신용)."""
    global _cache_owner, _fast_reader
    with _lock:
        _cache_owner = None
        _fast_reader = None
        _hits.clear()
        _misses.clear()


def _build_client():
    """짧은 타임아웃의 S3 클라이언트 (테스트에서 monkeypatch)."""
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.object_storage_endpoint,
        region_name=s.object_storage_region,
        aws_access_key_id=s.ncp_access_key,
        aws_secret_access_key=s.ncp_secret_key,
        config=Config(
            signature_version="s3v4",
            connect_timeout=STORAGE_CONNECT_TIMEOUT_SEC,
            read_timeout=STORAGE_READ_TIMEOUT_SEC,
            retries={"max_attempts": STORAGE_MAX_ATTEMPTS},
        ),
    )


def _fast(shared: NcpObjectStorage) -> NcpObjectStorage:
    global _fast_reader
    if _fast_reader is None:
        s = get_settings()
        _fast_reader = NcpObjectStorage(
            bucket=shared.bucket,
            endpoint_url=s.object_storage_endpoint,
            region_name=s.object_storage_region,
            access_key=s.ncp_access_key,
            secret_key=s.ncp_secret_key,
            client=_build_client(),
        )
    return _fast_reader


def _read_local_json(path: Path) -> dict | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            return parsed
        logger.warning("데이터 파일 형식이 올바르지 않습니다: %s", path.name)
    except FileNotFoundError:
        logger.warning("데이터 파일이 없습니다: %s", path.name)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("데이터 파일을 읽을 수 없습니다: %s (%s)", path.name, type(e).__name__)
    return None


def _fetch(storage, key: str) -> dict | None:
    try:
        data = storage.get_json(key)
    except Exception as exc:
        logger.warning("Object Storage 읽기 실패, 로컬 fallback 시도: key=%s (%s)", key, type(exc).__name__)
        return None
    if isinstance(data, dict):
        return data
    if data is not None:
        logger.warning("Object Storage 데이터 형식이 올바르지 않습니다: %s", key)
    return None


def _read_storage(key: str) -> dict | None:
    global _cache_owner
    shared = get_storage()
    if not isinstance(shared, NcpObjectStorage):
        return _fetch(shared, key)  # In-Memory 등: 캐시·타임아웃 없이 그대로

    with _lock:
        if _cache_owner is not shared:  # 스토리지가 바뀌었으면 이전 캐시를 버린다
            _hits.clear()
            _misses.clear()
            _cache_owner = shared
        if key in _hits:
            return _hits[key]
        if _misses.get(key, 0.0) > time.monotonic():
            return None
        reader = _fast(shared)

    data = _fetch(reader, key)
    with _lock:
        if data is not None:
            _hits[key] = data
            _misses.pop(key, None)
        else:
            _misses[key] = time.monotonic() + MISS_TTL_SEC
    return data


def read_json(name: str) -> dict | None:
    """law-data/<name> 을 읽어 dict로 반환. 없거나 깨졌으면 None (경고 로그)."""
    override = os.environ.get("LAW_DATA_DIR", "").strip()
    if override:
        return _read_local_json(Path(override) / name)

    data = _read_storage(StorageKeys.law_data(name))
    if data is not None:
        return data
    return _read_local_json(DEFAULT_DATA_DIR / name)
