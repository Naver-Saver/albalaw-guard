"""법령·최저임금 로더(law_data)와 수집 스크립트(sync)의 Object Storage 연동 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import calc, law_data, law_search
from app.services.storage import InMemoryObjectStorage, StorageKeys, get_storage, set_storage
from sync import all as sync_all
from sync import common as sync_common
from sync import law as sync_law
from sync import wage as sync_wage
from tests.conftest import FIXTURE_DIR


def test_read_json_prefers_object_storage_over_local(tmp_path, monkeypatch):
    (tmp_path / "min-wage.json").write_text(
        json.dumps({"syncedAt": "local", "items": [{"year": 2026, "hourlyWage": 1}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(law_data, "DEFAULT_DATA_DIR", tmp_path)
    monkeypatch.delenv("LAW_DATA_DIR", raising=False)

    storage = InMemoryObjectStorage()
    storage.put_json(
        StorageKeys.LAW_MIN_WAGE,
        {"syncedAt": "storage", "items": [{"year": 2026, "hourlyWage": 10320}]},
    )
    set_storage(storage)

    loaded = law_data.read_json(law_data.MIN_WAGE_FILE)
    assert loaded == {"syncedAt": "storage", "items": [{"year": 2026, "hourlyWage": 10320}]}


def test_read_json_falls_back_to_local_when_missing_or_error(tmp_path, monkeypatch):
    (tmp_path / "min-wage.json").write_text(
        json.dumps({"syncedAt": "local-fallback", "items": [{"year": 2026, "hourlyWage": 10320}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(law_data, "DEFAULT_DATA_DIR", tmp_path)
    monkeypatch.delenv("LAW_DATA_DIR", raising=False)

    # 1. Object Storage에 키가 없는 경우 로컬 fallback
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == {
        "syncedAt": "local-fallback",
        "items": [{"year": 2026, "hourlyWage": 10320}],
    }

    # 2. Object Storage 호출이 예외를 던져도 로컬 fallback
    class _BrokenStorage(InMemoryObjectStorage):
        def get_json(self, key: str):
            raise RuntimeError("boom")

    set_storage(_BrokenStorage())
    assert law_data.read_json(law_data.MIN_WAGE_FILE) == {
        "syncedAt": "local-fallback",
        "items": [{"year": 2026, "hourlyWage": 10320}],
    }


def test_read_json_law_data_dir_overrides_storage(tmp_path, monkeypatch):
    storage = InMemoryObjectStorage()
    storage.put_json(StorageKeys.LAW_MIN_WAGE, {"syncedAt": "storage", "items": []})
    set_storage(storage)

    override_dir = tmp_path / "override"
    override_dir.mkdir()
    monkeypatch.setenv("LAW_DATA_DIR", str(override_dir))

    # LAW_DATA_DIR이 지정되면 Object Storage를 건너뛰므로 파일 부재 시 None
    assert law_data.read_json(law_data.MIN_WAGE_FILE) is None

    (override_dir / "min-wage.json").write_text(
        json.dumps({"syncedAt": "override", "items": [{"year": 2026, "hourlyWage": 10320}]}),
        encoding="utf-8",
    )
    assert law_data.read_json(law_data.MIN_WAGE_FILE)["syncedAt"] == "override"


def test_sync_wage_uploads_to_storage():
    storage = get_storage()
    code = sync_wage.main(["--csv", str(FIXTURE_DIR / "min_wage_sample.csv")])
    assert code == 0

    uploaded = storage.get_json(StorageKeys.LAW_MIN_WAGE)
    assert uploaded is not None
    years = {item["year"]: item["hourlyWage"] for item in uploaded["items"]}
    assert years[2026] == 10320
    assert years[2027] == 10700


def test_sync_law_uploads_to_storage(monkeypatch):
    monkeypatch.setattr(sync_law, "load_oc", lambda: "test-oc")
    sample_payload = {
        "source": "LAW_API",
        "syncedAt": "2026-11-21T14:00:00+09:00",
        "laws": [
            {
                "lawId": "001872",
                "lawName": "근로기준법",
                "effectiveDate": "20261008",
                "articleCount": 1,
            }
        ],
        "items": [
            {
                "id": "law-001872-55",
                "source": "LAW_API",
                "lawId": "001872",
                "lawName": "근로기준법",
                "chapter": "제4장 근로시간과 휴식",
                "articleNo": "제55조",
                "title": "휴일",
                "text": "사용자는 근로자에게 1주에 평균 1회 이상의 유급휴일을 보장하여야 한다.",
                "effectiveDate": "20261008",
                "sourceUrl": "https://www.law.go.kr/법령/근로기준법/제55조",
            }
        ],
    }
    monkeypatch.setattr(sync_law, "collect", lambda laws, oc, save_raw: sample_payload)

    assert sync_law.main([]) == 0
    assert get_storage().get_json(StorageKeys.LAW_ARTICLES) == sample_payload


def test_sync_all_uploads_all_files_and_supports_search_and_calc(tmp_path, monkeypatch):
    monkeypatch.delenv("LAW_DATA_DIR", raising=False)
    monkeypatch.setattr(sync_law, "load_oc", lambda: "test-oc")
    monkeypatch.setattr(
        sync_law,
        "collect",
        lambda laws, oc, save_raw: json.loads(
            (FIXTURE_DIR / "law-data" / "law-articles.json").read_text(encoding="utf-8")
        ),
    )
    monkeypatch.setattr(sync_wage, "DEFAULT_CSV", FIXTURE_DIR / "min_wage_sample.csv")
    monkeypatch.setattr(sync_all, "DRY_RUN_DIR", FIXTURE_DIR / "law-data")

    assert sync_all.main([]) == 0

    storage = get_storage()
    assert storage.list_keys("") == [
        StorageKeys.LAW_ARTICLES,
        StorageKeys.LAW_MIN_WAGE,
        StorageKeys.LAW_QNA_MANUAL,
        StorageKeys.META_SYNC_LOG,
    ]
    sync_log = storage.get_json(StorageKeys.META_SYNC_LOG)
    assert sync_log["results"]["wage"]["ok"] is True
    assert sync_log["results"]["law"]["ok"] is True
    assert sync_log["results"]["qna_manual"]["ok"] is True

    min_wage_years = {item["year"] for item in storage.get_json(StorageKeys.LAW_MIN_WAGE)["items"]}
    assert {2026, 2027}.issubset(min_wage_years)

    # 로컬 fallback 경로를 비워 Object Storage에서만 읽는지 검증
    monkeypatch.setattr(law_data, "DEFAULT_DATA_DIR", tmp_path / "missing-local")
    law_search.load_law_data()
    found = law_search.search_evidence("주휴수당")
    assert found and found[0]["id"] == "manual-t01"
    assert calc.get_min_wage(2026)["hourlyWage"] == 10320
    assert calc.get_min_wage(2027)["hourlyWage"] == 10700


def test_upload_storage_requires_ncp_credentials_when_not_injected(tmp_path: Path, monkeypatch):
    set_storage(None)
    monkeypatch.setattr(sync_common, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("NCP_ACCESS_KEY", "")
    monkeypatch.setenv("NCP_SECRET_KEY", "")

    with pytest.raises(ValueError, match="NCP_ACCESS_KEY"):
        sync_common.get_upload_storage()


def test_read_json_caches_object_storage_within_ttl(monkeypatch):
    """Object Storage는 TTL 동안 다시 조회하지 않고, TTL이 지나면 새 값을 읽는다 (#43)."""
    import time as _time

    from app.services import law_data, storage
    from app.services.storage import InMemoryObjectStorage, StorageKeys

    monkeypatch.delenv("LAW_DATA_DIR", raising=False)
    mem = InMemoryObjectStorage()
    storage.set_storage(mem)
    law_data.clear_cache()
    key = StorageKeys.law_data(law_data.MIN_WAGE_FILE)
    mem.put_json(key, {"items": [{"year": 2026, "hourlyWage": 1}]})
    assert law_data.read_json(law_data.MIN_WAGE_FILE)["items"][0]["hourlyWage"] == 1

    mem.put_json(key, {"items": [{"year": 2026, "hourlyWage": 2}]})
    assert law_data.read_json(law_data.MIN_WAGE_FILE)["items"][0]["hourlyWage"] == 1  # 캐시

    now = _time.monotonic()
    monkeypatch.setattr(law_data.time, "monotonic", lambda: now + law_data.cache_ttl() + 1)
    assert law_data.read_json(law_data.MIN_WAGE_FILE)["items"][0]["hourlyWage"] == 2  # TTL 경과


def test_law_search_reload_keeps_index_when_storage_empty(monkeypatch, law_data_dir):
    from app.services import law_data, law_search

    law_search.load_law_data()
    before = len(law_search._ordered)
    assert before
    monkeypatch.setattr(law_data, "read_json", lambda name: None)
    law_search.load_law_data(keep_on_empty=True)
    assert len(law_search._ordered) == before
