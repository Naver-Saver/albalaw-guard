"""고용노동부 연도별 최저임금 CSV → law-data/min-wage.json.

사용: python -m sync.wage --csv <파일> [--dry-run]
CSV는 cp949, 열 순서 = 순번, 연도, 시간급 (헤더 1행). 적용기간 열은 없으므로 해당 연도 1/1~12/31로 채운다.
금액은 CSV에서만 읽는다 (코드에 하드코딩하지 않음).
"""

import argparse
import csv
from pathlib import Path

from sync.common import BACKEND_DIR, DRY_RUN_DIR, now_kst_iso, write_json

DEFAULT_CSV = BACKEND_DIR / "samples" / "raw" / "wage" / "min_wage_20260101.csv"
OUTPUT_NAME = "min-wage.json"
CSV_ENCODINGS = ("utf-8-sig", "cp949")


def read_csv_rows(path: Path) -> list[list[str]]:
    for enc in CSV_ENCODINGS:
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.reader(f))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"CSV 인코딩을 읽을 수 없습니다: {path}")


def parse_min_wage_csv(path: Path) -> list[dict]:
    rows = read_csv_rows(path)
    items: list[dict] = []
    for row in rows[1:]:  # 헤더 제외
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) < 3:
            raise ValueError(f"열이 부족한 행: {row}")
        year = int(row[1].strip())
        hourly = int(row[2].strip().replace(",", ""))
        if hourly <= 0:
            raise ValueError(f"시간급이 올바르지 않습니다: {row}")
        items.append(
            {
                "year": year,
                "hourlyWage": hourly,
                "periodStart": f"{year}-01-01",
                "periodEnd": f"{year}-12-31",
            }
        )
    if not items:
        raise ValueError("CSV에 데이터 행이 없습니다.")
    years = [i["year"] for i in items]
    if len(years) != len(set(years)):
        raise ValueError("연도가 중복되었습니다.")
    return sorted(items, key=lambda i: i["year"], reverse=True)


def build_payload(items: list[dict]) -> dict:
    return {"syncedAt": now_kst_iso(), "items": items}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="최저임금 CSV 변환")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 backend/data/law-data/ 에 저장")
    args = parser.parse_args(argv)

    payload = build_payload(parse_min_wage_csv(args.csv))
    if not args.dry_run:
        # TODO: Object Storage 업로드 — C의 clients/storage.py 구현 후 연결
        raise SystemExit("업로드는 아직 연결되지 않았습니다. --dry-run 으로 실행하세요.")
    out = DRY_RUN_DIR / OUTPUT_NAME
    write_json(out, payload)
    print(f"{len(payload['items'])}건 저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
