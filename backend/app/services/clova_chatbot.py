"""CLOVA Chatbot 호출 (AI-05). 응답 형식은 samples/raw/chatbot/ 의 실제 응답 기준.

- 요청: POST <Invoke URL>, 본문 {"version":"v2","userId","timestamp","bubbles":[...],"event":"send"}
- 서명: 헤더 X-NCP-CHATBOT_SIGNATURE = base64(HMAC-SHA256(Secret Key, 요청 본문 바이트))
- 응답: bubbles[0].data.description = 답변, bubbles[0].information = [{key, value}, ...]
  FAQ 일치 → score("1.0"), matchingType("exactMatch"), scenarioName
  일치 없음 → 기본 답변, defaultMsgType("canNotHelpMsg")·failureMsgId (score 없음)
"""

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.errors import AiUnavailableError, ServiceNotConfiguredError
from app.services.http import post_with_retry

logger = logging.getLogger("app.chatbot")
CHATBOT_TIMEOUT_SEC = 10
# BR-11. 실제 Chatbot 응답 35문항으로 점검한 결과(scripts/faq_probe.py): 0.70이면 엉뚱한 FAQ가 8건 걸려서
# 0.75로 올리고, 정확 일치가 아닌 매칭은 질문의 핵심어가 답변·시나리오에 나올 때만 FAQ로 인정한다(ask.py).
FAQ_MIN_SCORE = 0.75


@dataclass(frozen=True)
class ChatbotAnswer:
    text: str
    score: float | None
    matching_type: str | None
    scenario: str | None
    is_fallback: bool

    @property
    def is_faq(self) -> bool:
        """기본(실패) 답변이 아니고 신뢰도가 기준 이상이면 FAQ 경로 (BR-11)."""
        return not self.is_fallback and self.score is not None and self.score >= FAQ_MIN_SCORE


def is_configured() -> bool:
    s = get_settings()
    return bool(s.clova_chatbot_invoke_url and s.clova_chatbot_secret)


def sign(secret: str, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()).decode("ascii")


def parse_response(data: dict) -> ChatbotAnswer:
    """Chatbot 응답 JSON → ChatbotAnswer. 형식이 다르면 ValueError."""
    bubble = (data.get("bubbles") or [None])[0]
    if not isinstance(bubble, dict):
        raise ValueError("bubbles 없음")
    text = ((bubble.get("data") or {}).get("description") or "").strip()
    info: dict[str, str] = {}
    for entry in bubble.get("information") or []:
        if isinstance(entry, dict) and "key" in entry:
            info.setdefault(str(entry["key"]), str(entry.get("value", "")))
    try:
        score = float(info["score"]) if "score" in info else None
    except ValueError:
        score = None
    fallback = "defaultMsgType" in info or "failureMsgId" in info
    return ChatbotAnswer(
        text=text,
        score=score,
        matching_type=info.get("matchingType"),
        scenario=info.get("scenarioName"),
        is_fallback=fallback,
    )


async def ask(question: str) -> ChatbotAnswer:
    """질문을 보내고 답을 받는다. 키가 없으면 ServiceNotConfiguredError, 호출 실패는 AiUnavailableError."""
    s = get_settings()
    if not (s.clova_chatbot_invoke_url and s.clova_chatbot_secret):
        raise ServiceNotConfiguredError("CLOVA Chatbot 설정이 아직 완료되지 않았어요.")
    body = json.dumps(
        {
            "version": "v2",
            "userId": uuid.uuid4().hex,  # 대화 상태를 쓰지 않으니 요청마다 임시 ID
            "timestamp": int(time.time() * 1000),
            "bubbles": [{"type": "text", "data": {"description": question}}],
            "event": "send",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json;UTF-8",
        "X-NCP-CHATBOT_SIGNATURE": sign(s.clova_chatbot_secret, body),
    }
    try:
        res = await post_with_retry(
            "clova-chatbot",
            s.clova_chatbot_invoke_url,
            timeout=CHATBOT_TIMEOUT_SEC,
            content=body,
            headers=headers,
        )
    except httpx.HTTPError as e:
        raise AiUnavailableError() from e
    if res.status_code != 200:
        logger.warning("clova-chatbot status %s", res.status_code)
        raise AiUnavailableError()
    try:
        return parse_response(res.json())
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("clova-chatbot unexpected response shape")
        raise AiUnavailableError() from e
