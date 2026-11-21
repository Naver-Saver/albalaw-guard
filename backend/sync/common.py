"""sync 스크립트 공통 유틸: 저장 경로, 시각, JSON 쓰기."""

import json
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
