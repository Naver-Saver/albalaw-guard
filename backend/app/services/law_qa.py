"""백문백답 근거 문항 검색 (FS-06의 검색 부분).

데이터 원본은 데이터·콘텐츠 담당의 수집 스크립트가 만드는 manyask-worker.json 이다
(Object Storage law-data/ → 서버 시작 시 로드). 그 로더가 붙기 전까지는 로컬 파일
backend/data/law_qa/manyask-worker.json 이 있으면 쓰고, 없으면 빈 목록이다.
"""

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("app.law_qa")
LOCAL_PATH = Path(__file__).resolve().parents[2] / "data" / "law_qa" / "manyask-worker.json"


@dataclass(frozen=True)
class LawQa:
    id: str
    title: str
    answer: str
    keywords: tuple[str, ...] = ()
    url: str | None = None


@dataclass
class LawQaIndex:
    items: list[LawQa] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict) -> "LawQaIndex":
        items = [
            LawQa(
                id=str(it["id"]),
                title=it["title"],
                answer=it.get("answer", ""),
                keywords=tuple(it.get("keywords") or ()),
                url=it.get("url"),
            )
            for it in data.get("items", [])
        ]
        return cls(items)

    def search(self, keywords: list[str], limit: int = 3) -> list[LawQa]:
        scored = []
        for qa in self.items:
            score = 0
            for kw in keywords:
                if kw in qa.title or kw in qa.keywords:
                    score += 3
                elif kw in qa.answer:
                    score += 1
            if score:
                scored.append((score, qa))
        scored.sort(key=lambda x: -x[0])
        return [qa for _, qa in scored[:limit]]


@lru_cache
def get_index() -> LawQaIndex:
    if LOCAL_PATH.exists():
        try:
            return LawQaIndex.from_json(json.loads(LOCAL_PATH.read_text(encoding="utf-8")))
        except (ValueError, KeyError) as e:
            logger.warning("law_qa local file invalid: %s", e)
    return LawQaIndex()
