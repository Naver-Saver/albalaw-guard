"""sync 스크립트 공통 유틸: 저장 경로, 시각, JSON 쓰기, Object Storage 업로드."""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
DRY_RUN_DIR = BACKEND_DIR / "data" / "law-data"  # --dry-run 결과 (Object Storage law-data/ 와 같은 구조)
RAW_DIR = BACKEND_DIR / "samples" / "raw"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.services.storage import (  # noqa: E402
    ObjectStorage,
    create_storage,
    get_configured_storage,
)

KST = timezone(timedelta(hours=9))


def now_kst_iso() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_env(name: str) -> str:
    """환경변수 → 없으면 backend/.env 에서 읽는다. 값을 감싼 따옴표·공백은 제거한다."""
    value = os.environ.get(name, "")
    if not value.strip():
        env_file = BACKEND_DIR / ".env"
        if env_file.exists():
            m = re.search(rf"^{re.escape(name)}=(.*)$", env_file.read_text(encoding="utf-8"), re.M)
            value = m.group(1) if m else ""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


def get_upload_storage() -> ObjectStorage:
    """동기화 업로드용 ObjectStorage를 반환한다.

    테스트에서 set_storage()로 주입된 인스턴스가 있으면 우선 사용하고,
    실제 실행 시에는 backend/.env의 NCP 키로 NcpObjectStorage를 강제한다.
    """
    configured = get_configured_storage()
    if configured is not None:
        return configured
    settings = Settings(_env_file=BACKEND_DIR / ".env", storage_backend="ncp")
    return create_storage(settings)


def upload_json(key: str, payload: dict[str, Any], *, storage: ObjectStorage | None = None) -> str:
    """JSON 데이터를 Object Storage에 업로드하고 저장된 객체 키를 반환한다."""
    target = storage or get_upload_storage()
    return target.put_json(key, payload)
