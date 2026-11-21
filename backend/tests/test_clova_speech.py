"""CLOVA Speech 장문 인식 클라이언트 단위 테스트."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.errors import AiUnavailableError, ServiceNotConfiguredError
from app.services import clova_speech


def test_to_speech_data_key():
    assert clova_speech.to_speech_data_key("uploads/rec_1.wav") == "uploads/rec_1.wav"
    assert clova_speech.to_speech_data_key("uploads/rec_1.wav", "uploads/") == "rec_1.wav"
    assert clova_speech.to_speech_data_key("/uploads/rec_1.wav", "/uploads") == "rec_1.wav"


def test_parse_speech_segments():
    raw = {
        "duration": 42300,
        "segments": [
            {"start": 1250, "end": 4890, "speaker": {"label": "1"}, "text": "  시급 9,500원입니다  "},
            {"start": 5000, "end": 6000, "speaker": {"label": "2"}, "text": "   "},
            {"start": 6200, "end": 9500, "diarization": {"label": "2"}, "text": "주휴수당은요?"},
            {"start": 10000, "end": 12000, "speaker": {"label": "1"}, "text": "수습이라 없어요"},
        ],
    }

    segments, speakers, transcript, duration_sec = clova_speech.parse_speech_segments(raw)
    assert speakers == ["화자 A", "화자 B"]
    assert duration_sec == 42
    assert len(segments) == 3
    assert segments[0].start_ms == 1250
    assert segments[0].speaker == "화자 A"
    assert segments[1].speaker == "화자 B"
    assert "[00:01] 화자 A: 시급 9,500원입니다" in transcript


async def test_request_and_poll_with_retry_and_error_prefix(settings, monkeypatch, mock_transport):
    monkeypatch.setattr(settings, "clova_speech_invoke_url", "https://speech.test/external/v1/1/k")
    monkeypatch.setattr(settings, "clova_speech_secret", "speech-secret")

    seen: list[tuple[str, str]] = []
    submit_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal submit_attempts
        seen.append((request.method, str(request.url)))
        assert request.headers["X-CLOVASPEECH-API-KEY"] == "speech-secret"

        if request.method == "POST" and request.url.path.endswith("/recognizer/object-storage"):
            submit_attempts += 1
            if submit_attempts == 1:
                return httpx.Response(503, json={"message": "temporary"})
            body = json.loads(request.read())
            assert body["dataKey"] == "uploads/rec_1.wav"
            assert body["completion"] == "async"
            assert body["resultToObs"] is True
            assert body["diarization"] == {"enable": True}
            return httpx.Response(200, json={"token": "tok-1", "result": "WAITING"})

        if request.url.path.endswith("/recognizer/tok-1"):
            return httpx.Response(
                200,
                json={
                    "result": "COMPLETED",
                    "segments": [{"start": 1000, "end": 2500, "speaker": {"label": "0"}, "text": "안녕"}],
                },
            )

        if request.url.path.endswith("/recognizer/tok-err"):
            return httpx.Response(
                200,
                json={"result": "ERROR_TOKEN_INVALID", "message": "Token does not exist"},
            )

        if request.url.path.endswith("/recognizer/tok-timeout"):
            return httpx.Response(200, json={"result": "TIMEOUT", "message": "timed out"})

        return httpx.Response(404)

    mock_transport(handler)

    sub = await clova_speech.request_recognition("uploads/rec_1.wav")
    assert sub.token == "tok-1"
    assert submit_attempts == 2

    done = await clova_speech.get_recognition_status("tok-1")
    assert done.status == "completed"
    assert done.speakers == ["화자 A"]
    assert done.segments[0].start_ms == 1000

    err_prefix = await clova_speech.get_recognition_status("tok-err")
    assert err_prefix.status == "failed"
    assert err_prefix.error_message == "Token does not exist"

    timeout_res = await clova_speech.get_recognition_status("tok-timeout")
    assert timeout_res.status == "failed"


async def test_speech_not_configured_and_5xx_failure(settings, monkeypatch, mock_transport):
    monkeypatch.setattr(settings, "clova_speech_invoke_url", "")
    monkeypatch.setattr(settings, "clova_speech_secret", "")
    with pytest.raises(ServiceNotConfiguredError):
        await clova_speech.request_recognition("uploads/rec_1.wav")

    monkeypatch.setattr(settings, "clova_speech_invoke_url", "https://speech.test/external/v1/1/k")
    monkeypatch.setattr(settings, "clova_speech_secret", "speech-secret")
    mock_transport(lambda _req: httpx.Response(500))
    with pytest.raises(AiUnavailableError):
        await clova_speech.request_recognition("uploads/rec_1.wav")
