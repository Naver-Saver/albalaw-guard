"""CLOVA Speech 장문 인식 클라이언트 (AI-02 · FS-02).

인식 대상·결과 저장 경로가 Object Storage 버킷과 연결된 장문 인식 도메인을 비동기 호출한다.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.config import get_settings
from app.core.errors import AiUnavailableError, ServiceNotConfiguredError
from app.services.http import get_with_retry, post_with_retry

logger = logging.getLogger("app.speech")
SPEECH_TIMEOUT_SEC = 15.0


@dataclass(frozen=True)
class SpeechSegment:
    """CLOVA Speech 화자 분리 인식 세그먼트."""

    start_ms: int
    end_ms: int
    speaker: str
    text: str


@dataclass(frozen=True)
class SpeechSubmitResult:
    """CLOVA Speech 비동기 인식 요청 반환값."""

    token: str


@dataclass(frozen=True)
class SpeechPollResult:
    """CLOVA Speech 작업 상태 조회 결과."""

    status: Literal["processing", "completed", "failed"]
    segments: list[SpeechSegment]
    speakers: list[str]
    transcript: str
    duration_sec: int
    error_message: str | None = None


def is_configured() -> bool:
    """CLOVA Speech 도메인 Invoke URL과 Secret Key가 설정되어 있는지 확인한다."""
    s = get_settings()
    return bool(s.clova_speech_invoke_url and s.clova_speech_secret)


def to_speech_data_key(object_key: str, prefix: str = "") -> str:
    """버킷 객체 키를 CLOVA Speech 도메인 인식 대상 경로 기준 dataKey로 변환한다."""
    clean_key = object_key.replace("\\", "/").lstrip("/")
    clean_prefix = prefix.replace("\\", "/").strip("/")
    if clean_prefix:
        prefix_with_slash = f"{clean_prefix}/"
        if clean_key.startswith(prefix_with_slash):
            clean_key = clean_key[len(prefix_with_slash) :]
    return clean_key


def _speaker_display_name(index: int) -> str:
    if 0 <= index < 26:
        return f"화자 {chr(ord('A') + index)}"
    return f"화자 {index + 1}"


def _extract_raw_speaker(segment: dict[str, Any]) -> str:
    speaker_info = segment.get("speaker")
    if isinstance(speaker_info, dict):
        label = speaker_info.get("label") or speaker_info.get("name")
        if label is not None and str(label).strip():
            return str(label).strip()
    elif isinstance(speaker_info, str) and speaker_info.strip():
        return speaker_info.strip()

    diarization = segment.get("diarization")
    if isinstance(diarization, dict):
        label = diarization.get("label")
        if label is not None and str(label).strip():
            return str(label).strip()

    return "0"


def _format_ms(ms: int) -> str:
    minutes, secs = divmod(max(0, ms) // 1000, 60)
    return f"{minutes:02d}:{secs:02d}"


def parse_speech_segments(raw: dict[str, Any]) -> tuple[list[SpeechSegment], list[str], str, int]:
    """CLOVA Speech 원본 응답을 세그먼트·화자 목록·대본·녹음 길이(초)로 정규화한다."""
    raw_segments = raw.get("segments") or []
    speaker_map: dict[str, str] = {}
    speakers: list[str] = []
    segments: list[SpeechSegment] = []
    transcript_lines: list[str] = []

    for seg in raw_segments:
        if not isinstance(seg, dict):
            continue
        text = str(seg.get("text") or "").strip()
        if not text:
            continue

        raw_label = _extract_raw_speaker(seg)
        if raw_label not in speaker_map:
            display = _speaker_display_name(len(speaker_map))
            speaker_map[raw_label] = display
            speakers.append(display)

        start_ms = max(0, int(seg.get("start") or 0))
        end_ms = max(start_ms, int(seg.get("end") or start_ms))
        speaker = speaker_map[raw_label]

        segments.append(SpeechSegment(start_ms=start_ms, end_ms=end_ms, speaker=speaker, text=text))
        transcript_lines.append(f"[{_format_ms(start_ms)}] {speaker}: {text}")

    raw_duration = raw.get("duration")
    if isinstance(raw_duration, int | float) and raw_duration > 0:
        duration_sec = int(round(float(raw_duration) / 1000.0))
    elif segments:
        duration_sec = int(math.ceil(max(seg.end_ms for seg in segments) / 1000.0))
    else:
        duration_sec = 0

    return segments, speakers, "\n".join(transcript_lines), duration_sec


async def request_recognition(data_key: str, *, language: str = "ko-KR") -> SpeechSubmitResult:
    """Object Storage 경로의 오디오에 대해 CLOVA Speech 비동기 장문 인식을 요청한다."""
    s = get_settings()
    if not is_configured():
        raise ServiceNotConfiguredError("CLOVA Speech 설정이 아직 완료되지 않았어요.")

    url = f"{s.clova_speech_invoke_url.rstrip('/')}/recognizer/object-storage"
    headers = {
        "X-CLOVASPEECH-API-KEY": s.clova_speech_secret,
        "Content-Type": "application/json",
    }
    body = {
        "dataKey": data_key,
        "language": language,
        "completion": "async",
        "resultToObs": True,
        "diarization": {"enable": True},
        "wordAlignment": False,
        "fullText": True,
    }

    try:
        res = await post_with_retry(
            "clova-speech",
            url,
            timeout=SPEECH_TIMEOUT_SEC,
            headers=headers,
            json=body,
        )
    except httpx.HTTPError as exc:
        raise AiUnavailableError("음성 인식 요청에 실패했어요.") from exc

    if res.status_code != 200:
        logger.warning("clova-speech submit status %s", res.status_code)
        raise AiUnavailableError("음성 인식 요청에 실패했어요.")

    try:
        data = res.json()
    except ValueError as exc:
        raise AiUnavailableError("음성 인식 응답을 해석하지 못했어요.") from exc

    token = str(data.get("token") or "").strip() if isinstance(data, dict) else ""
    if not token:
        logger.warning("clova-speech submit response missing token")
        raise AiUnavailableError("음성 인식 작업 토큰을 받지 못했어요.")
    return SpeechSubmitResult(token=token)


async def get_recognition_status(token: str) -> SpeechPollResult:
    """CLOVA Speech 작업 토큰으로 인식 상태와 완료 결과를 조회한다."""
    s = get_settings()
    if not is_configured():
        raise ServiceNotConfiguredError("CLOVA Speech 설정이 아직 완료되지 않았어요.")

    url = f"{s.clova_speech_invoke_url.rstrip('/')}/recognizer/{token}"
    headers = {"X-CLOVASPEECH-API-KEY": s.clova_speech_secret}

    try:
        res = await get_with_retry(
            "clova-speech",
            url,
            timeout=SPEECH_TIMEOUT_SEC,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise AiUnavailableError("음성 인식 상태 조회에 실패했어요.") from exc

    if res.status_code != 200:
        logger.warning("clova-speech poll status %s", res.status_code)
        raise AiUnavailableError("음성 인식 상태 조회에 실패했어요.")

    try:
        data = res.json()
    except ValueError as exc:
        raise AiUnavailableError("음성 인식 상태 응답을 해석하지 못했어요.") from exc

    if not isinstance(data, dict):
        raise AiUnavailableError("음성 인식 상태 응답 형식이 올바르지 않아요.")

    result_code = str(data.get("result") or "").upper()
    message = str(data.get("message") or "").strip()

    if result_code == "COMPLETED":
        segments, speakers, transcript, duration_sec = parse_speech_segments(data)
        return SpeechPollResult(
            status="completed",
            segments=segments,
            speakers=speakers,
            transcript=transcript,
            duration_sec=duration_sec,
        )

    if result_code in {"FAILED", "TIMEOUT"} or result_code.startswith("ERROR"):
        return SpeechPollResult(
            status="failed",
            segments=[],
            speakers=[],
            transcript="",
            duration_sec=0,
            error_message=message or "음성 인식에 실패했어요.",
        )

    return SpeechPollResult(
        status="processing",
        segments=[],
        speakers=[],
        transcript="",
        duration_sec=0,
    )
