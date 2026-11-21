"""법령·최저임금 JSON 로더 (파트 A).

운영에서는 Object Storage(law-data/*.json)에서 읽는다 (C의 clients/storage.py 구현 후 연결).
그 전에는 로컬 `backend/data/law-data/` (환경변수 LAW_DATA_DIR 로 변경 가능)를 읽는다.
"""

# STUB: 담당 C의 Object Storage 모듈 구현 시 read_json 안의 storage 읽기로 교체

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "law-data"

ARTICLES_FILE = "law-articles.json"
QNA_MANUAL_FILE = "qna-manual.json"
MIN_WAGE_FILE = "min-wage.json"


def data_dir() -> Path:
    return Path(os.environ.get("LAW_DATA_DIR") or DEFAULT_DATA_DIR)


def read_json(name: str) -> dict | None:
    """law-data/<name> 을 읽어 dict로 반환. 없거나 깨졌으면 None (경고 로그)."""
    path = data_dir() / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("데이터 파일이 없습니다: %s", path.name)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("데이터 파일을 읽을 수 없습니다: %s (%s)", path.name, type(e).__name__)
    return None
