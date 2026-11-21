"""녹음 업로드 · 비동기 폴링 API (/api/recordings) 통합 테스트."""

from __future__ import annotations

import io
import json
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import recordings
from app.services.storage import InMemoryObjectStorage, StorageKeys, set_storage

client = TestClient(app)


def _make_wav_bytes(duration_sec: float = 1.0, sample_rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(1)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00" * int(duration_sec * sample_rate))
    return buf.getvalue()


@pytest.fixture
def rec_env(settings, monkeypatch, mock_transport):
    monkeypatch.setattr(settings, "clova_speech_invoke_url", "https://speech.test/external/v1/1/k")
    monkeypatch.setattr(settings, "clova_speech_secret", "speech-secret")
    monkeypatch.setattr(settings, "clova_speech_data_key_prefix", "")
    monkeypatch.setattr(settings, "upload_prefix", "uploads/")
    monkeypatch.setattr(settings, "clova_studio_api_key", "nv-test")
    monkeypatch.setattr(settings, "clova_studio_request_id", "req-test")

    storage = InMemoryObjectStorage()
    set_storage(storage)
    recordings.clear_jobs()
    yield storage, mock_transport, settings
    recordings.clear_jobs()
    set_storage(None)


def test_recording_upload_poll_timeline_and_audio_cleanup(rec_env):
    storage, install_transport, _ = rec_env
    poll_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal poll_calls
        url = str(request.url)
        if url.endswith("/recognizer/object-storage"):
            return httpx.Response(200, json={"token": "tok-rec-1", "result": "WAITING"})

        if url.endswith("/recognizer/tok-rec-1"):
            poll_calls += 1
            if poll_calls == 1:
                return httpx.Response(200, json={"token": "tok-rec-1", "result": "PROCESSING"})
            return httpx.Response(
                200,
                json={
                    "token": "tok-rec-1",
                    "result": "COMPLETED",
                    "duration": 30000,
                    "segments": [
                        {
                            "start": 12000,
                            "end": 18000,
                            "speaker": {"label": "1"},
                            "text": "이번 달부터 시급 만 원으로 할게",
                        },
                        {
                            "start": 20000,
                            "end": 25000,
                            "speaker": {"label": "2"},
                            "text": "네 알겠습니다",
                        },
                    ],
                },
            )

        if "clovastudio" in url:
            timeline_json = json.dumps(
                [
                    {
                        "start_ms": 12000,
                        "speaker": "화자 A",
                        "text": "이번 달부터 시급 만 원으로 할게",
                        "category": "임금",
                    }
                ],
                ensure_ascii=False,
            )
            return httpx.Response(
                200,
                json={
                    "status": {"code": "20000"},
                    "result": {"message": {"role": "assistant", "content": timeline_json}},
                },
            )

        return httpx.Response(404)

    install_transport(handler)

    up = client.post(
        "/api/recordings",
        files={"file": ("talk.wav", _make_wav_bytes(2.0), "audio/wav")},
        data={"consent": "true"},
    )
    assert up.status_code == 202
    assert "X-Request-ID" in up.headers
    up_body = up.json()
    assert up_body["success"] is True
    job_id = up_body["data"]["job_id"]
    assert up_body["data"]["status"] == "processing"

    audio_key = StorageKeys.upload_recording(job_id, "wav")
    assert storage.exists(audio_key)

    # 1차 폴링: processing (원본 유지)
    p1 = client.get(f"/api/recordings/{job_id}")
    assert p1.status_code == 200
    assert p1.json()["data"]["status"] == "processing"
    assert storage.exists(audio_key)

    # 2차 폴링: done + 타임라인 생성 + 원본 즉시 삭제
    p2 = client.get(f"/api/recordings/{job_id}")
    assert p2.status_code == 200
    done_data = p2.json()["data"]
    assert done_data["status"] == "done"
    assert done_data["duration_sec"] == 30
    assert done_data["speakers"] == ["화자 A", "화자 B"]
    assert done_data["segments"] == [
        {
            "start_ms": 12000,
            "end_ms": 18000,
            "speaker": "화자 A",
            "text": "이번 달부터 시급 만 원으로 할게",
        },
        {
            "start_ms": 20000,
            "end_ms": 25000,
            "speaker": "화자 B",
            "text": "네 알겠습니다",
        },
    ]
    assert done_data["timeline"] == [
        {
            "start_ms": 12000,
            "speaker": "화자 A",
            "text": "이번 달부터 시급 만 원으로 할게",
            "category": "임금",
        }
    ]
    assert "이번 달부터 시급 만 원으로 할게" in done_data["transcript"]
    assert not storage.exists(audio_key)

    # 3차 폴링: 멱등하게 done 재반환
    p3 = client.get(f"/api/recordings/{job_id}")
    assert p3.status_code == 200
    assert p3.json()["data"] == done_data


def test_recording_studio_parse_failure_falls_back_to_transcript(rec_env):
    storage, install_transport, _ = rec_env

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/recognizer/object-storage"):
            return httpx.Response(200, json={"token": "tok-fallback"})
        if url.endswith("/recognizer/tok-fallback"):
            return httpx.Response(
                200,
                json={
                    "result": "COMPLETED",
                    "segments": [
                        {"start": 1000, "end": 4000, "speaker": {"label": "0"}, "text": "시급 이야기"}
                    ],
                },
            )
        if "clovastudio" in url:
            return httpx.Response(
                200,
                json={
                    "status": {"code": "20000"},
                    "result": {"message": {"role": "assistant", "content": "JSON이 아닌 텍스트"}},
                },
            )
        return httpx.Response(404)

    install_transport(handler)
    up = client.post(
        "/api/recordings",
        files={"file": ("talk.mp3", b"fake-mp3", "audio/mpeg")},
        data={"consent": "true"},
    )
    job_id = up.json()["data"]["job_id"]
    poll = client.get(f"/api/recordings/{job_id}")
    assert poll.status_code == 200
    data = poll.json()["data"]
    assert data["status"] == "done"
    assert data["duration_sec"] == 4
    assert data["segments"] == [
        {
            "start_ms": 1000,
            "end_ms": 4000,
            "speaker": "화자 A",
            "text": "시급 이야기",
        }
    ]
    assert data["timeline"] == []
    assert "시급 이야기" in data["transcript"]
    assert storage.list_keys("uploads/") == []


def test_recording_validation_rollback_and_failure_cleanup(rec_env):
    storage, install_transport, settings = rec_env

    # consent=false -> 400 BAD_REQUEST
    r_consent = client.post(
        "/api/recordings",
        files={"file": ("a.wav", _make_wav_bytes(1.0), "audio/wav")},
        data={"consent": "false"},
    )
    assert r_consent.status_code == 400
    assert r_consent.json()["error"]["code"] == "BAD_REQUEST"

    # 미지원 확장자 -> 400 UNSUPPORTED_FILE
    r_ext = client.post(
        "/api/recordings",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"consent": "true"},
    )
    assert r_ext.status_code == 400
    assert r_ext.json()["error"]["code"] == "UNSUPPORTED_FILE"

    # 10분 초과 WAV -> 413 FILE_TOO_LARGE
    r_dur = client.post(
        "/api/recordings",
        files={"file": ("long.wav", _make_wav_bytes(610, sample_rate=10), "audio/wav")},
        data={"consent": "true"},
    )
    assert r_dur.status_code == 413
    assert r_dur.json()["error"]["code"] == "FILE_TOO_LARGE"

    # 크기 제한 초과 -> 413 FILE_TOO_LARGE
    old_limit = settings.recording_max_bytes
    settings.recording_max_bytes = 16
    try:
        r_size = client.post(
            "/api/recordings",
            files={"file": ("big.mp3", b"x" * 32, "audio/mpeg")},
            data={"consent": "true"},
        )
        assert r_size.status_code == 413
        assert r_size.json()["error"]["code"] == "FILE_TOO_LARGE"
    finally:
        settings.recording_max_bytes = old_limit

    # Speech 요청 실패(500) -> 502 AI_UNAVAILABLE + 업로드 오디오 롤백 삭제
    install_transport(lambda _req: httpx.Response(500))
    r_submit_err = client.post(
        "/api/recordings",
        files={"file": ("ok.m4a", b"audio", "audio/mp4")},
        data={"consent": "true"},
    )
    assert r_submit_err.status_code == 502
    assert r_submit_err.json()["error"]["code"] == "AI_UNAVAILABLE"
    assert storage.list_keys("uploads/") == []

    # Speech 폴링 실패(ERROR_TOKEN_INVALID) -> status=failed + 원본 삭제
    def fail_poll_handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/recognizer/object-storage"):
            return httpx.Response(200, json={"token": "tok-bad"})
        return httpx.Response(200, json={"result": "ERROR_TOKEN_INVALID", "message": "Token invalid"})

    install_transport(fail_poll_handler)
    up = client.post(
        "/api/recordings",
        files={"file": ("ok.m4a", b"audio", "audio/mp4")},
        data={"consent": "true"},
    )
    job_id = up.json()["data"]["job_id"]
    poll = client.get(f"/api/recordings/{job_id}")
    assert poll.status_code == 200
    assert poll.json()["data"]["status"] == "failed"
    assert poll.json()["data"]["error"] == "Token invalid"
    assert storage.list_keys("uploads/") == []


def test_recording_not_found_and_ttl_expiry(rec_env):
    _, install_transport, _ = rec_env
    r_missing = client.get("/api/recordings/rec_missing")
    assert r_missing.status_code == 404
    assert r_missing.json()["error"]["code"] == "NOT_FOUND"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/recognizer/object-storage"):
            return httpx.Response(200, json={"token": "tok-ttl"})
        if "clovastudio" in url:
            return httpx.Response(
                200,
                json={
                    "status": {"code": "20000"},
                    "result": {"message": {"role": "assistant", "content": "[]"}},
                },
            )
        return httpx.Response(
            200,
            json={
                "result": "COMPLETED",
                "segments": [{"start": 0, "end": 1000, "speaker": {"label": "0"}, "text": "확인"}],
            },
        )

    install_transport(handler)
    up = client.post(
        "/api/recordings",
        files={"file": ("ttl.mp3", b"audio", "audio/mpeg")},
        data={"consent": "true"},
    )
    job_id = up.json()["data"]["job_id"]
    done = client.get(f"/api/recordings/{job_id}")
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "done"

    # 조회 후 만료 시각 도래 시 404 NOT_FOUND
    recordings._jobs[job_id].expires_at = 0.0
    expired = client.get(f"/api/recordings/{job_id}")
    assert expired.status_code == 404
    assert expired.json()["error"]["code"] == "NOT_FOUND"


def test_recording_reads_result_to_obs_json_and_deletes_it(rec_env):
    """실제 CLOVA Speech(resultToObs=True)는 상태 조회의 segments 를 '[]'로 주고, 결과는 버킷의
    '{파일 이름}_{token}.json' 에 남긴다. 그 파일을 읽어 타임라인을 만들고 원본·결과를 모두 지운다."""
    storage, install_transport, _ = rec_env

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/recognizer/object-storage"):
            return httpx.Response(200, json={"token": "tok-obs", "result": "WAITING"})
        if url.endswith("/recognizer/tok-obs"):
            return httpx.Response(200, json={"token": "tok-obs", "result": "COMPLETED", "segments": "[]"})
        if "clovastudio" in url:
            content = json.dumps(
                [{"start_ms": 0, "speaker": "화자 A", "text": "시급은 만 원", "category": "임금"}],
                ensure_ascii=False,
            )
            return httpx.Response(
                200,
                json={
                    "status": {"code": "20000"},
                    "result": {"message": {"role": "assistant", "content": content}},
                },
            )
        return httpx.Response(404)

    install_transport(handler)
    up = client.post(
        "/api/recordings",
        files={"file": ("talk.wav", _make_wav_bytes(1.0), "audio/wav")},
        data={"consent": "true"},
    )
    job_id = up.json()["data"]["job_id"]
    audio_key = StorageKeys.upload_recording(job_id, "wav")
    result_key = recordings.speech_result_key(audio_key, "tok-obs")
    assert result_key == f"{job_id}.wav_tok-obs.json"
    storage.put_json(
        result_key,
        {
            "result": "COMPLETED",
            "segments": [
                {"start": 0, "end": 2000, "speaker": {"label": "1"}, "text": "시급은 만 원으로 할게요"}
            ],
        },
    )

    done = client.get(f"/api/recordings/{job_id}").json()["data"]
    assert done["status"] == "done"
    assert done["segments"][0]["text"] == "시급은 만 원으로 할게요"
    assert done["timeline"][0]["category"] == "임금"
    assert not storage.exists(audio_key) and not storage.exists(result_key)


def test_speech_result_key_respects_prefix():
    assert recordings.speech_result_key("uploads/recordings/a.mp3", "t", "results/") == "results/a.mp3_t.json"


def test_recording_waits_for_late_result_json(rec_env, monkeypatch):
    """COMPLETED 직후 결과 JSON이 아직 없으면 processing 을 유지하고, 생기면 done, 60초 넘으면 failed."""
    storage, install_transport, _ = rec_env

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/recognizer/object-storage"):
            return httpx.Response(200, json={"token": "tok-late", "result": "WAITING"})
        if url.endswith("/recognizer/tok-late"):
            return httpx.Response(200, json={"token": "tok-late", "result": "COMPLETED", "segments": "[]"})
        if "clovastudio" in url:
            content = json.dumps([{"start_ms": 0, "speaker": "화자 A", "text": "시급", "category": "임금"}])
            return httpx.Response(
                200,
                json={
                    "status": {"code": "20000"},
                    "result": {"message": {"role": "assistant", "content": content}},
                },
            )
        return httpx.Response(404)

    install_transport(handler)
    files = {"file": ("talk.wav", _make_wav_bytes(1.0), "audio/wav")}
    job_id = client.post("/api/recordings", files=files, data={"consent": "true"}).json()["data"]["job_id"]
    audio_key = StorageKeys.upload_recording(job_id, "wav")
    assert client.get(f"/api/recordings/{job_id}").json()["data"]["status"] == "processing"
    assert storage.exists(audio_key)  # 아직 지우지 않는다

    storage.put_json(
        recordings.speech_result_key(audio_key, "tok-late"),
        {"segments": [{"start": 0, "end": 1000, "speaker": {"label": "1"}, "text": "시급은 만 원"}]},
    )
    assert client.get(f"/api/recordings/{job_id}").json()["data"]["status"] == "done"

    # 결과 파일이 끝내 없으면 60초 뒤 실패
    job2 = client.post("/api/recordings", files=files, data={"consent": "true"}).json()["data"]["job_id"]
    assert client.get(f"/api/recordings/{job2}").json()["data"]["status"] == "processing"
    now = recordings.time.monotonic()
    monkeypatch.setattr(recordings.time, "monotonic", lambda: now + recordings.OBS_RESULT_WAIT_SEC + 1)
    failed = client.get(f"/api/recordings/{job2}").json()["data"]
    assert failed["status"] == "failed"
