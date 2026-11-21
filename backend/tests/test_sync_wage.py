from pathlib import Path

import pytest

from sync.wage import build_payload, main, parse_min_wage_csv

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
