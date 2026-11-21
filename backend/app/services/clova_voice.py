"""CLOVA Voice (TTS) 클라이언트 (API-09, AI-07).

공통 HTTP 재시도(http.post_with_retry)와 sha256 기반 인메모리 LRU·TTL 캐시를 제공한다.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AiUnavailableError, BadRequestError, ServiceNotConfiguredError
from app.services import http

logger = logging.getLogger("app.clova_voice")

TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
TIMEOUT_SEC = 15.0
MAX_TEXT_CHARS = 1000
MAX_CACHE_ITEMS = 500
CACHE_TTL_SEC = 86_400

SPEAKER_BY_LANG: dict[str, str] = {
    "ko": "nara",
    "en": "clara",
    "zh-CN": "meimei",
    "vi": "nara",
}

_UPSTREAM_ERROR_MSG = "음성을 생성하지 못했어요. 잠시 후 다시 시도해 주세요."

_cache_lock = threading.Lock()
_cache: OrderedDict[str, tuple[float, bytes]] = OrderedDict()


def is_configured(settings: Settings | None = None) -> bool:
    """CLOVA Voice(AI·NAVER API Application) 키 설정 여부를 반환한다."""
    cfg = settings or get_settings()
    return bool(cfg.ainaver_client_id.strip() and cfg.ainaver_client_secret.strip())


def resolve_speaker(lang: str) -> str:
    """요청 언어에 대응하는 CLOVA Voice 화자 이름을 반환한다."""
    return SPEAKER_BY_LANG.get(lang, "nara")


def clear_cache() -> None:
    """테스트 격리를 위해 음성 합성 캐시를 비운다."""
    with _cache_lock:
        _cache.clear()


def _make_cache_key(speaker: str, speed: int, text: str) -> str:
    raw = f"clova_voice:{speaker}:{speed}:{text}".encode()
    return hashlib.sha256(raw).hexdigest()


def _cache_get(key: str) -> bytes | None:
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        created_at, audio = entry
        if now - created_at >= CACHE_TTL_SEC:
            del _cache[key]
            return None
        _cache.move_to_end(key)
        return audio


def _cache_put(key: str, audio: bytes) -> None:
    now = time.monotonic()
    with _cache_lock:
        _cache[key] = (now, audio)
        _cache.move_to_end(key)
        while len(_cache) > MAX_CACHE_ITEMS:
            _cache.popitem(last=False)


async def synthesize(text: str, lang: str = "ko", *, speed: int = 0) -> bytes:
    """텍스트를 MP3 바이트로 합성한다. 동일 입력은 메모리 캐시에서 즉시 반환한다."""
    cleaned = text.strip()
    if not cleaned or len(cleaned) > MAX_TEXT_CHARS:
        raise BadRequestError("음성으로 변환할 텍스트는 1~1,000자여야 해요.")

    speaker = resolve_speaker(lang)
    cache_key = _make_cache_key(speaker, speed, cleaned)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    settings = get_settings()
    if not is_configured(settings):
        raise ServiceNotConfiguredError("음성 합성 서비스 설정이 아직 완료되지 않았어요.")

    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.ainaver_client_id,
        "X-NCP-APIGW-API-KEY": settings.ainaver_client_secret,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "speaker": speaker,
        "volume": "0",
        "speed": str(speed),
        "pitch": "0",
        "format": "mp3",
        "text": cleaned,
    }

    try:
        res = await http.post_with_retry(
            "clova_voice",
            TTS_URL,
            timeout=TIMEOUT_SEC,
            headers=headers,
            data=data,
        )
    except httpx.HTTPError as exc:
        logger.warning("clova_voice upstream failed (%s)", type(exc).__name__)
        raise AiUnavailableError(_UPSTREAM_ERROR_MSG) from exc

    if res.status_code != 200:
        logger.warning("clova_voice status=%s", res.status_code)
        raise AiUnavailableError(_UPSTREAM_ERROR_MSG)

    audio = res.content
    content_type = res.headers.get("content-type", "").lower()
    if not audio or ("audio" not in content_type and "octet-stream" not in content_type):
        logger.warning("clova_voice invalid response content_type=%s size=%d", content_type, len(audio))
        raise AiUnavailableError(_UPSTREAM_ERROR_MSG)

    _cache_put(cache_key, audio)
    return audio
