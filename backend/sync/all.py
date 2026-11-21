"""수집 스크립트를 순서대로 실행하고 meta/sync_log.json 을 남긴다.

사용:
    python -m sync.all [--save-raw]             # Object Storage 업로드 (qna-manual.json 포함)
    python -m sync.all --dry-run [--save-raw]   # 로컬 backend/data/ 저장
"""

import argparse
import json
import sys
from pathlib import Path

from app.services.storage import StorageKeys
from sync import law, wage
from sync.common import DRY_RUN_DIR, now_kst_iso, upload_json, write_json


def upload_manual_qna(path: Path | None = None) -> int:
    """수동 Q&A(qna-manual.json)를 검증하고 Object Storage에 업로드한다."""
    source = path or (DRY_RUN_DIR / "qna-manual.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"수동 Q&A JSON 형식이 올바르지 않습니다: {source}")
    key = upload_json(StorageKeys.LAW_QNA_MANUAL, payload)
    print(f"수동 Q&A {len(payload['items'])}건 업로드: {key}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="공공데이터 전체 수집")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--save-raw", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run:
        steps = {
            "wage": lambda: wage.main(["--dry-run"]),
            "law": lambda: law.main(["--dry-run"] + (["--save-raw"] if args.save_raw else [])),
        }
    else:
        steps = {
            "wage": lambda: wage.main([]),
            "law": lambda: law.main(["--save-raw"] if args.save_raw else []),
            "qna_manual": upload_manual_qna,
        }

    results: dict[str, dict] = {}
    exit_code = 0
    for name, run in steps.items():
        try:
            code = run()
            results[name] = {"ok": code == 0, "at": now_kst_iso()}
        except (Exception, SystemExit) as e:  # 한 단계가 실패해도 나머지는 계속 진행
            results[name] = {"ok": False, "at": now_kst_iso(), "error": type(e).__name__}
            exit_code = 1
            print(f"[{name}] 실패: {type(e).__name__}", file=sys.stderr)

    sync_log = {"syncedAt": now_kst_iso(), "results": results}
    if args.dry_run:
        write_json(DRY_RUN_DIR.parent / "meta" / "sync_log.json", sync_log)
    else:
        try:
            upload_json(StorageKeys.META_SYNC_LOG, sync_log)
        except Exception as e:
            exit_code = 1
            print(f"[sync_log] 업로드 실패: {type(e).__name__}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
