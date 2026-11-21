"""수집 스크립트를 순서대로 실행하고 meta/sync_log.json 을 남긴다.

사용: python -m sync.all --dry-run [--save-raw]
(수동 Q&A qna-manual.json 은 사람이 관리하는 파일이라 수집 대상이 아니다.)
"""

import argparse
import sys

from sync import law, wage
from sync.common import DRY_RUN_DIR, now_kst_iso, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="공공데이터 전체 수집")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--save-raw", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run:
        raise SystemExit(
            "업로드는 아직 연결되지 않았습니다 (C의 storage 모듈 대기). --dry-run 으로 실행하세요."
        )

    steps = {
        "wage": lambda: wage.main(["--dry-run"]),
        "law": lambda: law.main(["--dry-run"] + (["--save-raw"] if args.save_raw else [])),
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

    write_json(DRY_RUN_DIR.parent / "meta" / "sync_log.json", {"syncedAt": now_kst_iso(), "results": results})
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
