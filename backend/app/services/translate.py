"""점검 결과 번역 (파트 A). Papago 호출 + 메모리 캐시(비용 절감).

- translate_texts: 문장 목록 번역. 기본은 실패 시 원문을 돌려주고 경고 로그만 남긴다
  (결과 화면을 깨지 않기 위해). strict=True 이면 실패를 예외로 던진다 (POST /translate 가 502 를 낼 때 사용).
- translate_result: 평가 결과에서 '설명 문장'만 번역한다.
  서류·발언 원문(evidenceText 등)과 출처 제목은 번역하지 않는다.
"""

import asyncio
import copy
import logging
import re
from collections import OrderedDict

from app.core.errors import AppError, BadRequestError
from app.services import papago

logger = logging.getLogger("app.translate")

SUPPORTED_TARGETS = ("en", "vi", "zh-CN")  # openapi Lang(ko 제외)
CACHE_MAX = 2000
CONCURRENCY = 5

_cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()


def clear_cache() -> None:
    _cache.clear()


def _cache_get(key: tuple[str, str, str]) -> str | None:
    value = _cache.get(key)
    if value is not None:
        _cache.move_to_end(key)
    return value


def _cache_put(key: tuple[str, str, str], value: str) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)


def _chunks(text: str, limit: int = papago.MAX_CHARS) -> list[str]:
    """긴 글을 문장·줄 경계에서 limit 이하로 나눈다."""
    if len(text) <= limit:
        return [text]
    pieces = re.split(r"(?<=[.!?。\n])\s*", text)
    out: list[str] = []
    cur = ""
    for p in pieces:
        while len(p) > limit:  # 경계가 없는 아주 긴 조각은 강제로 자른다
            if cur:
                out.append(cur)
                cur = ""
            out.append(p[:limit])
            p = p[limit:]
        if len(cur) + len(p) + 1 > limit and cur:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip() if cur else p
    if cur:
        out.append(cur)
    return out


async def _translate_text(text: str, target: str, source: str) -> str:
    key = (source, target, text)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    parts = [await papago.translate_one(chunk, target, source) for chunk in _chunks(text)]
    result = " ".join(parts)
    _cache_put(key, result)
    return result


def _check_target(target: str) -> None:
    if target != "ko" and target not in SUPPORTED_TARGETS:
        raise BadRequestError("지원하지 않는 언어예요.")


async def translate_texts(
    texts: list[str], target: str, source: str = "ko", *, strict: bool = False
) -> list[str]:
    """texts 를 target 언어로 번역해 같은 순서로 반환한다.

    - target == source 이거나 "ko" 면 그대로 반환 (Papago 호출 없음).
    - 빈 문장은 그대로 둔다. 같은 문장은 한 번만 번역하고 캐시한다.
    - strict=False(기본): 번역에 실패한 문장은 원문을 쓰고 경고 로그를 남긴다.
    - strict=True: 한 문장이라도 실패하면 AppError(502 등)를 그대로 던진다.
    - 지원하지 않는 target 이면 BadRequestError.
    """
    if target == "ko" or target == source:
        return list(texts)
    _check_target(target)

    unique = list(dict.fromkeys(t for t in texts if t and t.strip()))
    sem = asyncio.Semaphore(CONCURRENCY)
    translations: dict[str, str] = {}

    async def run(text: str) -> None:
        async with sem:
            try:
                translations[text] = await _translate_text(text, target, source)
            except AppError as e:
                if strict:
                    raise
                logger.warning("번역 실패, 원문을 사용합니다 (%s)", e.code)
                translations[text] = text

    await asyncio.gather(*(run(t) for t in unique))
    return [translations.get(t, t) for t in texts]


# 번역하는 필드 (평가 결과 공통 형식). 서류·발언 원문과 출처 제목은 번역하지 않는다.
_TOP_LEVEL = ("explanation", "disclaimer")
_LIST_OF_TEXT = ("checklistForNextTime",)
_LIST_OF_DICT_FIELDS = {
    "items": ("title", "description"),  # /contracts/review 결과
    "findings": ("explanation",),
    "verbalPromises": ("advice",),
}


async def translate_result(result: dict, target: str) -> dict:
    """평가 결과 dict 에서 설명 문장만 번역한 새 dict 를 반환한다 (입력은 바꾸지 않는다).
    번역 실패 시 해당 문장은 원문 그대로 둔다. target == "ko" 면 사본을 그대로 반환한다.
    """
    out = copy.deepcopy(result)
    if target == "ko":
        return out
    _check_target(target)

    # (설정 함수, 원문) 목록을 모아 한 번에 번역한 뒤 제자리에 채운다
    slots: list[tuple[dict | list, str | int, str]] = []
    for key in _TOP_LEVEL:
        if isinstance(out.get(key), str) and out[key].strip():
            slots.append((out, key, out[key]))
    for key in _LIST_OF_TEXT:
        values = out.get(key)
        if isinstance(values, list):
            slots += [(values, i, v) for i, v in enumerate(values) if isinstance(v, str) and v.strip()]
    for key, fields in _LIST_OF_DICT_FIELDS.items():
        entries = out.get(key)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    slots += [
                        (entry, f, entry[f])
                        for f in fields
                        if isinstance(entry.get(f), str) and entry[f].strip()
                    ]

    translated = await translate_texts([s[2] for s in slots], target)
    for (container, key, _), text in zip(slots, translated, strict=True):
        container[key] = text
    if "lang" in out:
        out["lang"] = target
    return out
