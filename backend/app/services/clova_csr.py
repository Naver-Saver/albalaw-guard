"""CLOVA Speech Recognition(CSR) 짧은 음성 인식 (AI-05). 응답 형식은 samples/raw/csr/ 의 실제 응답 기준.

- POST https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor, 본문 = 음성 바이너리
- 헤더 X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY (AI·NAVER API 앱 키)
- Content-Type application/octet-stream
- 성공 {"text": "..."} / 실패 {"errorMessage", "errorCode"}
  예) 60초를 넘는 파일 → 500 STT006 "Failed to pre-processing"
키·음성은 로그에 남기지 않는다.
"""

import logging
import os

import httpx

from app.core.config import get_settings
from app.core.errors import AiUnavailableError, BadRequestError, ServiceNotConfiguredError
from app.services.http import post_with_retry

logger = logging.getLogger("app.csr")
DEFAULT_URL = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt"
CSR_TIMEOUT_SEC = 30
# 음성을 읽지 못한 경우(길이 초과·지원하지 않는 형식 등)의 오류 코드
UNREADABLE_CODES = {"STT006"}


def is_configured() -> bool:
    s = get_settings()
    return bool(s.ainaver_client_id and s.ainaver_client_secret)


async def recognize(audio: bytes, lang: str = "Kor") -> str:
    """음성을 텍스트로 바꾼다. 인식된 말이 없으면 빈 문자열(BR-13).
    읽을 수 없는 음성은 BadRequestError, 서비스 장애는 AiUnavailableError."""
    s = get_settings()
    if not (s.ainaver_client_id and s.ainaver_client_secret):
        raise ServiceNotConfiguredError("음성 인식 설정이 아직 완료되지 않았어요.")
    headers = {
        "X-NCP-APIGW-API-KEY-ID": s.ainaver_client_id,
        "X-NCP-APIGW-API-KEY": s.ainaver_client_secret,
        "Content-Type": "application/octet-stream",
    }
    url = os.environ.get("CSR_ENDPOINT") or DEFAULT_URL
    try:
        res = await post_with_retry(
            "clova-csr", url, timeout=CSR_TIMEOUT_SEC, params={"lang": lang}, content=audio, headers=headers
        )
    except (
        httpx.HTTPStatusError
    ) as e:  # 재시도 후에도 5xx — 본문의 오류 코드로 읽을 수 없는 음성인지 구분한다
        _raise_for_error(e.response)
        raise AiUnavailableError("음성을 인식하지 못했어요.") from e
    except httpx.HTTPError as e:
        raise AiUnavailableError("음성을 인식하지 못했어요.") from e

    if res.status_code == 200:
        try:
            text = res.json().get("text", "")
        except (ValueError, AttributeError) as e:
            raise AiUnavailableError("음성을 인식하지 못했어요.") from e
        return text.strip() if isinstance(text, str) else ""

    _raise_for_error(res)
    raise AiUnavailableError("음성을 인식하지 못했어요.")


def _raise_for_error(res: httpx.Response) -> None:
    code = _error_code(res)
    logger.warning("clova-csr status %s code %s", res.status_code, code)
    if code in UNREADABLE_CODES:
        raise BadRequestError("녹음을 읽지 못했어요. 60초 이하의 mp3·wav 파일로 다시 시도해 주세요.")


def _error_code(res: httpx.Response) -> str | None:
    try:
        return res.json().get("errorCode")
    except (ValueError, AttributeError):
        return None
