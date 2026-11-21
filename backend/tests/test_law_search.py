import json

import pytest

from app.services import law_data, law_search


def test_search_finds_manual_qna_first(law_data_dir):
    res = law_search.search_evidence("주휴수당을 받을 수 있나요?")
    assert res, "결과가 있어야 한다"
    assert res[0]["id"] == "manual-t01"
    assert res[0]["source"] == "MANUAL"
    assert set(res[0]) == {"id", "source", "title", "text", "sourceUrl"}


def test_search_strips_particles_and_accepts_list(law_data_dir):
    assert law_search.search_evidence(["휴게시간을"])[0]["id"] in {"manual-t02", "law-t-54"}
    assert law_search.search_evidence(["해고", "예고"])[0]["id"] == "law-t-26"


def test_search_sources_filter_and_limit(law_data_dir):
    only_law = law_search.search_evidence("휴게시간", sources=["LAW_API"])
    assert only_law and all(i["source"] == "LAW_API" for i in only_law)
    assert len(law_search.search_evidence("휴게시간 주휴수당 해고", limit=1)) == 1


def test_search_no_match_or_empty(law_data_dir):
    assert law_search.search_evidence("zzzz없는단어") == []
    assert law_search.search_evidence("") == []
    assert law_search.search_evidence("휴게", limit=0) == []


def test_text_is_truncated_to_800(law_data_dir):
    long_text = "휴게시간 " + "가" * 2000
    path = law_data.data_dir() / law_data.ARTICLES_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    data["items"][0]["text"] = long_text
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    law_search.load_law_data()
    found = law_search.search_evidence("휴게시간", sources=["LAW_API"])
    assert all(len(i["text"]) <= 800 for i in found)
    # 원문 단건 조회는 자르지 않는다
    assert len(law_search.get_source(data["items"][0]["id"])["text"]) == len(long_text)


def test_get_source(law_data_dir):
    s = law_search.get_source("manual-t01")
    assert s["relatedArticleIds"] == ["law-t-55"]
    assert law_search.get_source("law-t-26")["sourceUrl"].endswith("law-t-26")
    assert law_search.get_source("nope") is None


def test_build_evidence_block(law_data_dir):
    items = law_search.search_evidence("휴게시간 주휴수당", limit=5)
    block = law_search.build_evidence_block(items)
    for it in items:
        assert f"({it['id']})" in block
    assert len(law_search.build_evidence_block(items, max_total_chars=150)) <= 150
    assert law_search.build_evidence_block([]) == ""


def test_missing_data_dir_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("LAW_DATA_DIR", str(tmp_path / "none"))
    law_search.load_law_data()
    assert law_search.search_evidence("주휴수당") == []
    monkeypatch.delenv("LAW_DATA_DIR")
    law_search.load_law_data()


REAL_DIR = law_data.DEFAULT_DATA_DIR


@pytest.mark.skipif(not (REAL_DIR / law_data.ARTICLES_FILE).exists(), reason="수집 데이터 없음")
class TestRealData:
    """수집한 실제 데이터(backend/data/law-data) 기준 검사 — AC-16, AC-17."""

    def setup_method(self):
        law_search.load_law_data()

    def test_ac17_weekly_holiday_pay_returns_result(self):
        res = law_search.search_evidence("주휴수당")
        assert res and res[0]["source"] == "MANUAL"

    def test_manual_items_reference_existing_articles(self):
        manual = json.loads((REAL_DIR / law_data.QNA_MANUAL_FILE).read_text(encoding="utf-8"))
        assert len(manual["items"]) >= 30
        for item in manual["items"]:
            assert item["relatedArticleIds"], item["id"]
            for aid in item["relatedArticleIds"]:
                assert law_search.get_source(aid), f"{item['id']} → 없는 조문 {aid}"

    @pytest.mark.parametrize("query", ["최저임금 미달", "휴게시간", "해고 예고", "급여명세서"])
    def test_typical_queries_hit_manual_first(self, query):
        res = law_search.search_evidence(query, limit=3)
        assert res and res[0]["id"].startswith("manual-")

    def test_unrelated_query_returns_nothing(self):
        assert law_search.search_evidence("고양이 사료") == []

    def test_generic_words_do_not_pull_unrelated_results(self):
        ids = [i["id"] for i in law_search.search_evidence("휴게시간 없이 일해요", limit=5)]
        assert ids and ids[0].startswith("manual-") and "manual-029" not in ids

    def test_article_ids_unique(self):
        articles = json.loads((REAL_DIR / law_data.ARTICLES_FILE).read_text(encoding="utf-8"))["items"]
        ids = [a["id"] for a in articles]
        assert len(ids) == len(set(ids))
