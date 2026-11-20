"""CLOVA Studio Chat Completions v3 공통 클라이언트 — AI-03·04·05 가 함께 쓴다.

인증: Authorization: Bearer <API 키> + X-NCP-CLOVASTUDIO-REQUEST-ID (4차시 실습과 같은 형식)
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import get_settings
from app.core.errors import AiUnavailableError, ServiceNotConfiguredError
from app.services.http import post_with_retry

logger = logging.getLogger("app.studio")
STUDIO_TIMEOUT_SEC = 20

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


def is_configured() -> bool:
    return bool(get_settings().clova_studio_api_key)


async def chat(
    messages: list[Message],
    *,
    temperature: float = 0.3,
    max_tokens: int = 600,
    top_p: float = 0.8,
    model: str | None = None,
) -> str:
    """메시지를 보내고 assistant 응답 텍스트를 반환한다. 실패하면 AiUnavailableError."""
    s = get_settings()
    if not s.clova_studio_api_key:
        raise ServiceNotConfiguredError("CLOVA Studio 설정이 아직 완료되지 않았어요.")

    url = f"{s.clova_studio_base_url.rstrip('/')}/{model or s.clova_studio_model}"
    headers = {
        "Authorization": f"Bearer {s.clova_studio_api_key.removeprefix('Bearer ').strip()}",
        "X-NCP-CLOVASTUDIO-REQUEST-ID": s.clova_studio_request_id or uuid.uuid4().hex,
        "Content-Type": "application/json",
    }
    body = {
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
        "topP": top_p,
        "topK": 0,
        "maxTokens": max_tokens,
        "repetitionPenalty": 1.1,
    }
    try:
        res = await post_with_retry(
            "clova-studio", url, timeout=STUDIO_TIMEOUT_SEC, json=body, headers=headers
        )
    except httpx.HTTPError as e:
        raise AiUnavailableError() from e

    if res.status_code != 200:
        logger.warning("clova-studio status %s", res.status_code)
        raise AiUnavailableError()
    data = res.json()
    status = (data.get("status") or {}).get("code")
    content = ((data.get("result") or {}).get("message") or {}).get("content")
    if status not in (None, "20000") or not content:
        logger.warning("clova-studio status code %s", status)
        raise AiUnavailableError()
    return content.strip()
