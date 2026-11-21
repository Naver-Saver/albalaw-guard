"""법령·최저임금 JSON 로더 (파트 A·C 연동).

기본적으로 Object Storage(`law-data/*.json`)에서 읽고, 객체가 없거나 조회에 실패하면
로컬 `backend/data/law-data/`를 fallback으로 읽는다.
환경변수 `LAW_DATA_DIR`가 지정된 경우(테스트·로컬 오버라이드)에는 해당 로컬 폴더만 직접 읽는다.
"""

import json
import logging
import os
from pathlib import Path

from app.services.storage import StorageKeys, get_storage

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "law-data"

ARTICLES_FILE = "law-articles.json"
QNA_MANUAL_FILE = "qna-manual.json"
MIN_WAGE_FILE = "min-wage.json"


def data_dir() -> Path:
    return Path(os.environ.get("LAW_DATA_DIR") or DEFAULT_DATA_DIR)


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


def read_json(name: str) -> dict | None:
    """law-data/<name> 을 읽어 dict로 반환. 없거나 깨졌으면 None (경고 로그)."""
    override = os.environ.get("LAW_DATA_DIR", "").strip()
    if override:
        return _read_local_json(Path(override) / name)

    key = StorageKeys.law_data(name)
    try:
        data = get_storage().get_json(key)
    except Exception as exc:
        logger.warning("Object Storage 읽기 실패, 로컬 fallback 시도: key=%s (%s)", key, type(exc).__name__)
        data = None

    if isinstance(data, dict):
        return data
    if data is not None:
        logger.warning("Object Storage 데이터 형식이 올바르지 않습니다: %s", key)

    return _read_local_json(DEFAULT_DATA_DIR / name)
