"""sync 스크립트 공통 유틸: 저장 경로, 시각, JSON 쓰기."""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DRY_RUN_DIR = BACKEND_DIR / "data" / "law-data"  # --dry-run 결과 (Object Storage law-data/ 와 같은 구조)
RAW_DIR = BACKEND_DIR / "samples" / "raw"

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
