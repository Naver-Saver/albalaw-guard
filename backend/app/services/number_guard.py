"""LLM 설명 속 숫자 검증 — BR-05 / NFR-08.

설명 문장에 허용 목록에 없는 숫자가 있으면 그 문장을 지운다. 금액·시간은 코드가 계산한 값만 허용.
"""

import re

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")

# 상담 전화번호, 법정 기준(15시간, 40시간, 8시간) 등 항상 허용하는 숫자
ALWAYS_ALLOWED = {1350, 132, 15, 40, 8, 1, 4, 30, 50, 5}


def _to_number(token: str) -> float:
    return float(token.replace(",", ""))


def numbers_in(text: str) -> set[float]:
    return {_to_number(t) for t in _NUM.findall(text)}


def filter_unverified_sentences(text: str, allowed: set[float]) -> tuple[str, list[str]]:
    """(검증 통과 문장만 남긴 텍스트, 제거된 문장들)"""
    ok_set = {float(a) for a in allowed} | {float(a) for a in ALWAYS_ALLOWED}
    kept: list[str] = []
    removed: list[str] = []
    for sentence in (s.strip() for s in _SENTENCE_END.split(text)):
        if not sentence:
            continue
        if numbers_in(sentence) <= ok_set:
            kept.append(sentence)
        else:
            removed.append(sentence)
    return " ".join(kept), removed
