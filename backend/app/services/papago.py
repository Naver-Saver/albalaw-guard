"""Papago 번역 클라이언트 (AI-06). 호출 형식은 samples/raw/papago/ 의 실제 응답 기준.

- POST https://papago.apigw.ntruss.com/nmt/v1/translation  (환경변수 PAPAGO_ENDPOINT 로 변경 가능)
- 헤더 X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY — Papago Translation 앱 키 (AI·NAVER API 키와 별개)
- 요청 JSON {"source","target","text"} → 응답 message.result.translatedText
- 실패 응답 {"error": {"errorCode", "message"}} (예: N2MT04 지원하지 않는 target 언어)
키·본문은 로그에 남기지 않는다.
"""

import logging
import os

import httpx

from app.core.config import get_settings
from app.core.errors import AiUnavailableError, ServiceNotConfiguredError
from app.services.http import post_with_retry

logger = logging.getLogger("app.papago")

DEFAULT_URL = "https://papago.apigw.ntruss.com/nmt/v1/translation"
PAPAGO_TIMEOUT_SEC = 10
MAX_CHARS = 4500  # Papago 1회 요청 한도(5,000자)보다 여유 있게


def is_configured() -> bool:
    s = get_settings()
    return bool(s.papago_client_id and s.papago_client_secret)


async def translate_one(text: str, target: str, source: str = "ko") -> str:
    """한 덩어리(MAX_CHARS 이하)를 번역한다.
    실패하면 AiUnavailableError, 키가 없으면 ServiceNotConfiguredError."""
    s = get_settings()
    if not (s.papago_client_id and s.papago_client_secret):
        raise ServiceNotConfiguredError("Papago 설정이 아직 완료되지 않았어요.")
    headers = {
        "X-NCP-APIGW-API-KEY-ID": s.papago_client_id,
        "X-NCP-APIGW-API-KEY": s.papago_client_secret,
        "Content-Type": "application/json",
    }
    url = os.environ.get("PAPAGO_ENDPOINT") or DEFAULT_URL
    try:
        res = await post_with_retry(
            "papago",
            url,
            timeout=PAPAGO_TIMEOUT_SEC,
            json={"source": source, "target": target, "text": text},
            headers=headers,
        )
    except httpx.HTTPError as e:
        raise AiUnavailableError("번역을 불러오지 못했어요.") from e

    if res.status_code != 200:
        code = _error_code(res)
        logger.warning("papago status %s code %s", res.status_code, code)
        raise AiUnavailableError("번역을 불러오지 못했어요.")
    try:
        translated = res.json()["message"]["result"]["translatedText"]
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("papago unexpected response shape")
        raise AiUnavailableError("번역을 불러오지 못했어요.") from e
    if not isinstance(translated, str) or not translated:
        raise AiUnavailableError("번역을 불러오지 못했어요.")
    return translated


def _error_code(res: httpx.Response) -> str | None:
    try:
        return (res.json().get("error") or {}).get("errorCode")
    except (ValueError, AttributeError):
        return None
