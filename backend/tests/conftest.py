import shutil
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def law_data_dir(tmp_path, monkeypatch):
    """tests/fixtures/law-data 를 임시 폴더에 복사해 LAW_DATA_DIR 로 지정하고, 검색 인덱스를 새로 읽는다."""
    target = tmp_path / "law-data"
    shutil.copytree(FIXTURE_DIR / "law-data", target)
    monkeypatch.setenv("LAW_DATA_DIR", str(target))
    from app.services import law_search

    law_search.load_law_data()
    yield target
    monkeypatch.delenv("LAW_DATA_DIR", raising=False)
    law_search.load_law_data()
