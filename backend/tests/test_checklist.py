import json

import pytest

from app.services import law_data
from app.services.checklist import CHECKLISTS, find_missing


def test_contract_all_missing():
    keys = {m["fieldKey"] for m in find_missing("CONTRACT", {})}
    assert keys == {k for _, k, _, _ in CHECKLISTS["CONTRACT"]}


def test_zero_is_not_missing_but_blank_is():
    fields = {"break_minutes": 0, "work_place": "  ", "job_description": None, "weekly_hours": 20}
    keys = {m["fieldKey"] for m in find_missing("CONTRACT", fields)}
    assert "break_minutes" not in keys
    assert "weekly_hours" not in keys
    assert {"work_place", "job_description"} <= keys


def test_empty_list_is_missing_and_result_has_sources():
    res = find_missing("PAYSLIP", {"items": [], "total_pay": 100})
    by_key = {m["fieldKey"]: m for m in res}
    assert "items" in by_key and "total_pay" not in by_key
    assert by_key["deductions"]["conditional"] is True
    assert by_key["items"]["sourceIds"] == ["law-003058-27-2"]


def test_complete_document_has_no_missing():
    fields = {k: "x" for _, k, _, _ in CHECKLISTS["CONTRACT"]}
    assert find_missing("CONTRACT", fields) == []


def test_unknown_doc_type():
    with pytest.raises(ValueError):
        find_missing("OTHER", {})


@pytest.mark.skipif(
    not (law_data.DEFAULT_DATA_DIR / law_data.ARTICLES_FILE).exists(), reason="수집 데이터 없음"
)
def test_every_source_id_exists_in_collected_law_data():
    path = law_data.DEFAULT_DATA_DIR / law_data.ARTICLES_FILE
    ids = {a["id"] for a in json.loads(path.read_text(encoding="utf-8"))["items"]}
    for items in CHECKLISTS.values():
        for _, _, source_ids, _ in items:
            assert source_ids, "근거 없는 체크리스트 항목은 둘 수 없다"
            assert set(source_ids) <= ids
