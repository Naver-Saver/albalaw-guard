"""CLOVA OCR (General) 클라이언트 — AI-01.

이미지는 base64로 바로 보내고 디스크·Object Storage에 저장하지 않는다 (NFR-01).
"""

import base64
import logging
import time
import uuid
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.errors import OcrFailedError, ServiceNotConfiguredError
from app.services.http import post_with_retry

logger = logging.getLogger("app.ocr")
OCR_TIMEOUT_SEC = 15


@dataclass(frozen=True)
class OcrText:
    raw_text: str
    lines: list[str]


def fields_to_lines(fields: list[dict]) -> list[str]:
    """OCR fields(inferText, lineBreak)를 줄 단위 문자열로 합친다."""
    lines: list[str] = []
    current: list[str] = []
    for f in fields:
        text = (f.get("inferText") or "").strip()
        if text:
            current.append(text)
        if f.get("lineBreak"):
            if current:
                lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    return lines


async def recognize(content: bytes, image_format: str) -> OcrText:
    settings = get_settings()
    if not settings.clova_ocr_invoke_url or not settings.clova_ocr_secret:
        raise ServiceNotConfiguredError("OCR 설정이 아직 완료되지 않았어요.")

    payload = {
        "version": "V2",
        "requestId": uuid.uuid4().hex,
        "timestamp": int(time.time() * 1000),
        "lang": "ko",
        "images": [{"format": image_format, "name": "document", "data": base64.b64encode(content).decode()}],
    }
    headers = {"X-OCR-SECRET": settings.clova_ocr_secret, "Content-Type": "application/json"}
    try:
        res = await post_with_retry(
            "clova-ocr", settings.clova_ocr_invoke_url, timeout=OCR_TIMEOUT_SEC, json=payload, headers=headers
        )
    except httpx.HTTPError as e:
        raise OcrFailedError() from e
    if res.status_code != 200:
        logger.warning("clova-ocr status %s", res.status_code)
        raise OcrFailedError()

    images = res.json().get("images") or [{}]
    image = images[0]
    if image.get("inferResult") not in (None, "SUCCESS"):
        logger.info("clova-ocr inferResult=%s", image.get("inferResult"))
        raise OcrFailedError()
    lines = fields_to_lines(image.get("fields") or [])
    return OcrText(raw_text="\n".join(lines), lines=lines)
