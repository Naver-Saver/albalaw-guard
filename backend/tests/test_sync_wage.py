from pathlib import Path

import pytest

from sync.wage import ANNOUNCED_CSV, build_payload, main, merge_announced, parse_min_wage_csv

FIXTURE = Path(__file__).parent / "fixtures" / "min_wage_sample.csv"


def test_parse_sample_csv():
    items = parse_min_wage_csv(FIXTURE)
    assert len(items) == 13
    assert [i["year"] for i in items] == sorted((i["year"] for i in items), reverse=True)
    latest = items[0]
    assert latest["year"] == 2026
    assert latest["periodStart"] == "2026-01-01"
    assert latest["periodEnd"] == "2026-12-31"
    assert latest["hourlyWage"] > 0


def test_payload_shape():
    payload = build_payload(parse_min_wage_csv(FIXTURE))
    assert set(payload) == {"syncedAt", "items"}
    assert set(payload["items"][0]) == {"year", "hourlyWage", "periodStart", "periodEnd"}


def test_rejects_duplicate_year(tmp_path):
    p = tmp_path / "dup.csv"
    p.write_text("순번,연도,시간급\n1,2026,100\n2,2026,200\n", encoding="cp949")
    with pytest.raises(ValueError):
        parse_min_wage_csv(p)


def test_rejects_non_positive_wage(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("순번,연도,시간급\n1,2026,0\n", encoding="cp949")
    with pytest.raises(ValueError):
        parse_min_wage_csv(p)


def test_accepts_utf8_with_commas(tmp_path):
    p = tmp_path / "u.csv"
    p.write_text('순번,연도,시간급\n1,2025,"10,030"\n', encoding="utf-8-sig")
    assert parse_min_wage_csv(p)[0]["hourlyWage"] == 10030


def test_dry_run_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr("sync.wage.DRY_RUN_DIR", tmp_path)
    assert main(["--csv", str(FIXTURE), "--dry-run"]) == 0
    assert (tmp_path / "min-wage.json").exists()


def test_merge_announced_adds_missing_year_only(tmp_path):
    official = parse_min_wage_csv(FIXTURE)
    p = tmp_path / "announced.csv"
    p.write_text("순번,연도,시간급\n1,2027,10700\n2,2026,1\n", encoding="utf-8")
    merged = merge_announced(official, parse_min_wage_csv(p))
    assert merged[0] == {
        "year": 2027,
        "hourlyWage": 10700,
        "periodStart": "2027-01-01",
        "periodEnd": "2027-12-31",
    }
    # 공공데이터 CSV에 있는 연도는 보충분으로 덮어쓰지 않는다
    assert next(i for i in merged if i["year"] == 2026)["hourlyWage"] != 1


def test_announced_csv_in_repo_is_valid():
    items = parse_min_wage_csv(ANNOUNCED_CSV)
    assert {
        "year": 2027,
        "hourlyWage": 10700,
        "periodStart": "2027-01-01",
        "periodEnd": "2027-12-31",
    } in items
