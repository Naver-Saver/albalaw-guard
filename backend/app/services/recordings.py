"""대화 기록 정리 서비스 (API-05 · API-06 · FS-02 · AI-04).

녹음 업로드(Object Storage 임시 저장) → CLOVA Speech 비동기 장문 인식 →
폴링 완료 시 CLOVA Studio 타임라인 정리 및 원본 녹음 즉시 삭제를 처리한다.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import (
    AiUnavailableError,
    BadRequestError,
    FileTooLargeError,
    NotFoundError,
    ServiceNotConfiguredError,
    UnsupportedFileError,
)
from app.prompts import load as load_prompt
from app.schemas.recordings import (
    RecordingJob,
    RecordingStatus,
    SpeechSegmentEntry,
    TimelineCategory,
    TimelineEntry,
)
from app.services import clova_speech, clova_studio
from app.services.clova_speech import SpeechSegment, to_speech_data_key
from app.services.storage import StorageKeys, get_storage

logger = logging.getLogger("app.recordings")

ALLOWED_AUDIO_EXTENSIONS = frozenset({"m4a", "mp3", "wav"})
CONTENT_TYPE_BY_EXT = {
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
}
VALID_CATEGORIES: frozenset[str] = frozenset({"임금", "근무시간", "휴게·휴일", "약속·지시", "기타"})
TIMELINE_CHUNK_CHAR_LIMIT = 6000
_READ_CHUNK_BYTES = 1024 * 1024
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


@dataclass
class _JobRecord:
    job_id: str
    token: str
    audio_key: str
    status: RecordingStatus
    error: str | None = None
    duration_sec: int | None = None
    speakers: list[str] = field(default_factory=list)
    segments: list[SpeechSegmentEntry] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    transcript: str | None = None
    expires_at: float | None = None


_jobs_lock = threading.Lock()
_jobs: dict[str, _JobRecord] = {}


def clear_jobs() -> None:
    """테스트 간 인메모리 작업 저장소를 초기화한다."""
    with _jobs_lock:
        _jobs.clear()


def _prune_expired_locked(now: float) -> None:
    expired = [jid for jid, rec in _jobs.items() if rec.expires_at is not None and now >= rec.expires_at]
    for jid in expired:
        _jobs.pop(jid, None)


def _to_schema(record: _JobRecord) -> RecordingJob:
    return RecordingJob(
        job_id=record.job_id,
        status=record.status,
        error=record.error,
        duration_sec=record.duration_sec,
        speakers=list(record.speakers),
        segments=list(record.segments),
        timeline=list(record.timeline),
        transcript=record.transcript,
    )


def _wav_duration_sec(data: bytes) -> float | None:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return None
            return wav_file.getnframes() / float(frame_rate)
    except (wave.Error, EOFError):
        return None


async def _read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLargeError("50MB 이하 파일만 올릴 수 있어요.")
        chunks.append(chunk)
    return b"".join(chunks)


def _delete_audio_best_effort(audio_key: str | None) -> None:
    if not audio_key:
        return
    try:
        get_storage().delete(audio_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("recording audio delete failed: key=%s error=%s", audio_key, type(exc).__name__)


def extract_timeline_json(text: str) -> list[dict[str, Any]]:
    """CLOVA Studio 응답 문자열에서 타임라인 JSON 배열을 파싱한다."""
    stripped = text.strip()
    fence_match = _CODE_FENCE_RE.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass

    start = stripped.find("[")
    end = stripped.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("CLOVA Studio 응답에서 JSON 배열을 찾지 못했습니다.")

    parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("CLOVA Studio 타임라인 응답은 JSON 배열이어야 합니다.")
    return [item for item in parsed if isinstance(item, dict)]


def _chunk_segments(segments: list[SpeechSegment]) -> list[list[SpeechSegment]]:
    chunks: list[list[SpeechSegment]] = []
    current: list[SpeechSegment] = []
    current_chars = 0

    for seg in segments:
        line_len = len(seg.speaker) + len(seg.text) + 24
        if current and current_chars + line_len > TIMELINE_CHUNK_CHAR_LIMIT:
            chunks.append(current)
            current = [seg]
            current_chars = line_len
        else:
            current.append(seg)
            current_chars += line_len

    if current:
        chunks.append(current)
    return chunks


def _normalize_category(value: Any) -> TimelineCategory:
    raw = str(value or "").strip()
    if raw in VALID_CATEGORIES:
        return raw  # type: ignore[return-value]
    return "기타"


async def build_timeline(segments: list[SpeechSegment]) -> list[TimelineEntry]:
    """CLOVA Studio로 대화 세그먼트를 분류·정리한다. 실패 시 빈 타임라인(대본만 반환)으로 폴백한다."""
    if not segments or not clova_studio.is_configured():
        return []

    system_prompt = load_prompt("recording_timeline_system")
    entries: list[TimelineEntry] = []

    for chunk in _chunk_segments(segments):
        user_lines = [f"start_ms={seg.start_ms} | speaker={seg.speaker} | text={seg.text}" for seg in chunk]
        messages = [
            clova_studio.Message(role="system", content=system_prompt),
            clova_studio.Message(role="user", content="\n".join(user_lines)),
        ]

        parsed_rows: list[dict[str, Any]] | None = None
        for attempt in range(2):
            try:
                raw_text = await clova_studio.chat(
                    messages,
                    temperature=0.2,
                    max_tokens=1500,
                )
                parsed_rows = extract_timeline_json(raw_text)
                break
            except (AiUnavailableError, ServiceNotConfiguredError) as exc:
                logger.warning("recording timeline studio unavailable: %s", exc.code)
                return []
            except ValueError:
                if attempt == 0:
                    continue
                logger.warning("recording timeline json parse failed after retry")
                return []

        if not parsed_rows:
            continue

        for row in parsed_rows:
            text_val = str(row.get("text") or "").strip()
            speaker_val = str(row.get("speaker") or "").strip()
            if not text_val or not speaker_val:
                continue
            try:
                start_ms = max(0, int(row.get("start_ms") or 0))
            except (TypeError, ValueError):
                start_ms = 0
            entries.append(
                TimelineEntry(
                    start_ms=start_ms,
                    speaker=speaker_val,
                    text=text_val,
                    category=_normalize_category(row.get("category")),
                )
            )

    return entries


async def create_recording_job(*, file: UploadFile, consent: bool) -> RecordingJob:
    """녹음 파일을 검증·임시 저장하고 CLOVA Speech 장문 인식 비동기 작업을 생성한다."""
    if consent is not True:
        raise BadRequestError("녹음 관련 주의 문구에 동의해야 업로드할 수 있어요.")

    filename = file.filename or ""
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise UnsupportedFileError("m4a, mp3, wav 파일만 올릴 수 있어요.")

    s = get_settings()
    data = await _read_upload_with_limit(file, s.recording_max_bytes)
    if not data:
        raise BadRequestError("비어 있는 파일은 업로드할 수 없어요.")

    if ext == "wav":
        wav_seconds = _wav_duration_sec(data)
        if wav_seconds is not None and wav_seconds > s.recording_max_duration_sec:
            raise FileTooLargeError("녹음 길이는 최대 10분까지 지원해요.")

    job_id = f"rec_{uuid4().hex[:12]}"
    audio_key = StorageKeys.upload_recording(job_id, ext, s.upload_prefix)
    content_type = CONTENT_TYPE_BY_EXT[ext]
    storage = get_storage()

    await asyncio.to_thread(storage.upload_bytes, audio_key, data, content_type)
    data_key = to_speech_data_key(audio_key, s.clova_speech_data_key_prefix)

    try:
        submit = await clova_speech.request_recognition(data_key, language="ko-KR")
    except Exception:
        await asyncio.to_thread(_delete_audio_best_effort, audio_key)
        raise

    record = _JobRecord(
        job_id=job_id,
        token=submit.token,
        audio_key=audio_key,
        status="processing",
    )
    with _jobs_lock:
        _prune_expired_locked(time.monotonic())
        _jobs[job_id] = record

    return _to_schema(record)


async def get_recording_job(job_id: str) -> RecordingJob:
    """작업 상태를 폴링하고 인식 완료 시 타임라인 생성 및 원본 녹음 삭제를 수행한다."""
    now = time.monotonic()
    s = get_settings()

    with _jobs_lock:
        _prune_expired_locked(now)
        record = _jobs.get(job_id)
        if record is None:
            raise NotFoundError("녹음 작업을 찾을 수 없거나 만료되었어요.")
        if record.status in {"done", "failed"}:
            if record.expires_at is None:
                record.expires_at = now + s.recording_job_ttl_sec
            return _to_schema(record)
        token = record.token
        audio_key = record.audio_key

    poll = await clova_speech.get_recognition_status(token)
    if poll.status == "processing":
        return RecordingJob(job_id=job_id, status="processing")

    if poll.status == "failed":
        await asyncio.to_thread(_delete_audio_best_effort, audio_key)
        with _jobs_lock:
            current = _jobs.get(job_id)
            if current is None:
                raise NotFoundError("녹음 작업을 찾을 수 없거나 만료되었어요.")
            current.status = "failed"
            current.error = poll.error_message or "음성 인식에 실패했어요. 다시 시도해 주세요."
            current.expires_at = time.monotonic() + s.recording_job_ttl_sec
            return _to_schema(current)

    if not poll.segments:
        await asyncio.to_thread(_delete_audio_best_effort, audio_key)
        with _jobs_lock:
            current = _jobs.get(job_id)
            if current is None:
                raise NotFoundError("녹음 작업을 찾을 수 없거나 만료되었어요.")
            current.status = "failed"
            current.error = "음성에서 대화를 인식하지 못했어요."
            current.expires_at = time.monotonic() + s.recording_job_ttl_sec
            return _to_schema(current)

    if poll.duration_sec > s.recording_max_duration_sec:
        await asyncio.to_thread(_delete_audio_best_effort, audio_key)
        with _jobs_lock:
            current = _jobs.get(job_id)
            if current is None:
                raise NotFoundError("녹음 작업을 찾을 수 없거나 만료되었어요.")
            current.status = "failed"
            current.error = "녹음 길이는 최대 10분까지 지원해요."
            current.expires_at = time.monotonic() + s.recording_job_ttl_sec
            return _to_schema(current)

    timeline = await build_timeline(poll.segments)
    await asyncio.to_thread(_delete_audio_best_effort, audio_key)

    with _jobs_lock:
        current = _jobs.get(job_id)
        if current is None:
            raise NotFoundError("녹음 작업을 찾을 수 없거나 만료되었어요.")
        current.status = "done"
        current.error = None
        current.duration_sec = poll.duration_sec
        current.speakers = list(poll.speakers)
        current.segments = [
            SpeechSegmentEntry(
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                speaker=seg.speaker,
                text=seg.text,
            )
            for seg in poll.segments
        ]
        current.timeline = timeline
        current.transcript = poll.transcript
        current.expires_at = time.monotonic() + s.recording_job_ttl_sec
        return _to_schema(current)
