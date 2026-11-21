"""CLOVA Voice (POST /api/tts) 단위·통합 테스트."""

from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import clova_voice

client = TestClient(app)


@pytest.fixture
def tts_env(settings, monkeypatch, mock_transport):
    monkeypatch.setattr(settings, "ainaver_client_id", "id-test")
    monkeypatch.setattr(settings, "ainaver_client_secret", "secret-test")
    clova_voice.clear_cache()
    yield settings, mock_transport
    clova_voice.clear_cache()


def test_tts_success_returns_mp3_and_caches(tts_env):
    _, install_transport = tts_env
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert str(request.url) == clova_voice.TTS_URL
        assert request.headers["x-ncp-apigw-api-key-id"] == "id-test"
        assert request.headers["x-ncp-apigw-api-key"] == "secret-test"
        form = parse_qs(request.content.decode("utf-8"))
        assert form["speaker"] == ["nara"]
        assert form["format"] == ["mp3"]
        assert form["text"] == ["주휴수당을 확인해 보세요."]
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"ID3-MP3-DATA")

    install_transport(handler)

    res1 = client.post("/api/tts", json={"text": "주휴수당을 확인해 보세요.", "lang": "ko"})
    res2 = client.post("/api/tts", json={"text": "주휴수당을 확인해 보세요.", "lang": "ko"})

    assert res1.status_code == 200
    assert res1.headers["content-type"].startswith("audio/mpeg")
    assert res1.content == b"ID3-MP3-DATA"
    assert res2.status_code == 200
    assert res2.content == b"ID3-MP3-DATA"
    assert calls == 1


@pytest.mark.parametrize(
    ("lang", "expected_speaker"),
    [("ko", "nara"), ("en", "clara"), ("zh-CN", "meimei"), ("vi", "nara")],
)
def test_tts_speaker_mapping_by_lang(tts_env, lang, expected_speaker):
    _, install_transport = tts_env
    seen_speakers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode("utf-8"))
        seen_speakers.extend(form["speaker"])
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"MP3")

    install_transport(handler)

    res = client.post("/api/tts", json={"text": "Hello", "lang": lang})
    assert res.status_code == 200
    assert seen_speakers == [expected_speaker]


def test_tts_cache_eviction_and_ttl(tts_env, monkeypatch):
    _, install_transport = tts_env
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=f"AUDIO-{calls}".encode())

    install_transport(handler)
    monkeypatch.setattr(clova_voice, "MAX_CACHE_ITEMS", 2)

    assert client.post("/api/tts", json={"text": "first"}).content == b"AUDIO-1"
    assert client.post("/api/tts", json={"text": "second"}).content == b"AUDIO-2"
    assert client.post("/api/tts", json={"text": "third"}).content == b"AUDIO-3"
    # 최대 2건 초과로 가장 오래된 "first" 제거됨 → 재요청 시 upstream 호출
    assert client.post("/api/tts", json={"text": "first"}).content == b"AUDIO-4"
    assert calls == 4

    # TTL 만료 시 캐시 무효화
    fake_now = [100.0]
    monkeypatch.setattr(clova_voice.time, "monotonic", lambda: fake_now[0])
    monkeypatch.setattr(clova_voice, "CACHE_TTL_SEC", 10)
    clova_voice.clear_cache()

    assert client.post("/api/tts", json={"text": "ttl-item"}).content == b"AUDIO-5"
    assert client.post("/api/tts", json={"text": "ttl-item"}).content == b"AUDIO-5"
    fake_now[0] = 111.0
    assert client.post("/api/tts", json={"text": "ttl-item"}).content == b"AUDIO-6"
    assert calls == 6


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "", "lang": "ko"},
        {"text": "   \n  ", "lang": "ko"},
        {"text": "가" * 1001, "lang": "ko"},
        {"text": "안녕하세요", "lang": "jp"},
    ],
)
def test_tts_validation_errors(tts_env, payload):
    res = client.post("/api/tts", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_tts_service_not_configured(settings, monkeypatch):
    clova_voice.clear_cache()
    monkeypatch.setattr(settings, "ainaver_client_id", "")
    monkeypatch.setattr(settings, "ainaver_client_secret", "")

    res = client.post("/api/tts", json={"text": "테스트", "lang": "ko"})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "SERVICE_NOT_CONFIGURED"


def test_tts_upstream_5xx_retries_once_then_succeeds_or_502(tts_env):
    _, install_transport = tts_env
    calls = 0

    def recover_handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, text="temporary error")
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"RECOVERED")

    install_transport(recover_handler)
    res_ok = client.post("/api/tts", json={"text": "재시도 성공"})
    assert res_ok.status_code == 200
    assert res_ok.content == b"RECOVERED"
    assert calls == 2

    calls_fail = 0

    def always_500(request: httpx.Request) -> httpx.Response:
        nonlocal calls_fail
        calls_fail += 1
        return httpx.Response(502, text="bad gateway")

    install_transport(always_500)
    res_fail = client.post("/api/tts", json={"text": "재시도 실패"})
    assert res_fail.status_code == 502
    assert res_fail.json()["error"]["code"] == "AI_UNAVAILABLE"
    assert calls_fail == 2


def test_tts_upstream_4xx_no_retry_returns_502(tts_env):
    _, install_transport = tts_env
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": {"message": "unauthorized"}})

    install_transport(handler)
    res = client.post("/api/tts", json={"text": "인증 오류"})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_UNAVAILABLE"
    assert calls == 1


@pytest.mark.parametrize("mode", ["timeout", "json_body", "empty_body"])
def test_tts_timeout_and_non_audio_response_return_502(tts_env, mode):
    _, install_transport = tts_env
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if mode == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if mode == "json_body":
            return httpx.Response(200, headers={"content-type": "application/json"}, json={"ok": False})
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"")

    install_transport(handler)
    res = client.post("/api/tts", json={"text": f"case-{mode}"})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_UNAVAILABLE"
    assert calls == (2 if mode == "timeout" else 1)
