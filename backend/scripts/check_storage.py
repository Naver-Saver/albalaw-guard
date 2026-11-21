"""NCP Object Storage 연결 및 쓰기·조회·삭제 스모크 테스트 스크립트.

사용법 (backend/ 디렉터리에서):
    python scripts/check_storage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.storage import StorageKeys, create_storage  # noqa: E402


def main() -> int:
    settings = get_settings()
    storage = create_storage(settings)
    probe_key = StorageKeys.upload_recording("_storage_check", "json", settings.upload_prefix)
    payload = {"ok": True, "bucket": settings.object_storage_bucket}

    print(f"스토리지 백엔드: {type(storage).__name__} (bucket={settings.object_storage_bucket})")
    storage.put_json(probe_key, payload)
    assert storage.exists(probe_key), "업로드 후 exists() 확인 실패"
    loaded = storage.get_json(probe_key)
    assert loaded == payload, f"조회 데이터 불일치: {loaded}"
    storage.delete(probe_key)
    assert not storage.exists(probe_key), "삭제 후 잔존 객체 확인됨"
    print("PASS: 업로드 · 조회 · 존재 확인 · 삭제 정상 동작")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
