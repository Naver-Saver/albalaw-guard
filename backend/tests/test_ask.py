import json
import struct
import wave
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import ask as ask_route
from app.core.config import get_settings
from app.core.errors import AiUnavailableError, BadRequestError, ServiceNotConfiguredError
from app.core.response import register_exception_handlers
from app.services import ask, audio, clova_chatbot, clova_csr, clova_studio

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "raw"


def _sample(folder: str, name: str) -> dict:
    return json.loads((SAMPLES / folder / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def keys(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "clova_chatbot_invoke_url", "https://chatbot.test/invoke")
    monkeypatch.setattr(s, "clova_chatbot_secret", "chatbot-secret")
    monkeypatch.setattr(s, "ainaver_client_id", "csr-id")
    monkeypatch.setattr(s, "ainaver_client_secret", "csr-secret")
    return s


# ---------- CLOVA Chatbot ----------


def test_parse_faq_hit_sample():
    a = clova_chatbot.parse_response(_sample("chatbot", "faq_hit"))
    assert a.is_faq and a.score == 1.0 and a.matching_type == "exactMatch" and a.scenario == "주휴수당_조건"
    assert "15시간" in a.text


def test_parse_no_match_sample_is_fallback():
    a = clova_chatbot.parse_response(_sample("chatbot", "no_match"))
    assert a.is_fallback and a.score is None and not a.is_faq
    assert a.text


@pytest.mark.parametrize(
    ("score", "faq"), [(1.0, True), (0.75, True), (0.74, False), (0.7, False), (None, False)]
)
def test_faq_threshold(score, faq):
    a = clova_chatbot.ChatbotAnswer("x", score, "model", "s", is_fallback=False)
    assert a.is_faq is faq


def test_parse_rejects_unexpected_shape():
    with pytest.raises(ValueError):
        clova_chatbot.parse_response({"bubbles": []})


def test_signature_is_base64_hmac_sha256():
    import base64
    import hashlib
    import hmac

    expected = base64.b64encode(hmac.new(b"key", b"body", hashlib.sha256).digest()).decode()
    assert clova_chatbot.sign("key", b"body") == expected
    assert clova_chatbot.sign("key", b"body") != clova_chatbot.sign("key", b"bodY")


async def test_chatbot_request_headers_and_body(keys, mock_transport):
    seen = {}

    def handler(request: httpx.Request):
        body = request.read()
        seen["body"] = json.loads(body)
        seen["sig"] = request.headers["X-NCP-CHATBOT_SIGNATURE"]
        seen["expected"] = clova_chatbot.sign("chatbot-secret", body)
        return httpx.Response(200, json=_sample("chatbot", "faq_hit"))

    mock_transport(handler)
    a = await clova_chatbot.ask("주휴수당 받을 수 있어?")
    assert a.is_faq
    assert seen["sig"] == seen["expected"]
    assert seen["body"]["bubbles"][0]["data"]["description"] == "주휴수당 받을 수 있어?"
    assert seen["body"]["event"] == "send" and seen["body"]["version"] == "v2"


async def test_chatbot_errors(keys, mock_transport, monkeypatch):
    mock_transport(lambda request: httpx.Response(500))
    with pytest.raises(AiUnavailableError):
        await clova_chatbot.ask("질문")
    mock_transport(lambda request: httpx.Response(200, json={"nope": 1}))
    with pytest.raises(AiUnavailableError):
        await clova_chatbot.ask("질문")
    monkeypatch.setattr(get_settings(), "clova_chatbot_secret", "")
    with pytest.raises(ServiceNotConfiguredError):
        await clova_chatbot.ask("질문")


# ---------- CLOVA CSR ----------


async def test_csr_success_sample_and_request(keys, mock_transport):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["id"] = request.headers["X-NCP-APIGW-API-KEY-ID"]
        seen["ctype"] = request.headers["Content-Type"]
        seen["body"] = request.read()
        return httpx.Response(200, json=_sample("csr", "response_trim_45s"))

    mock_transport(handler)
    text = await clova_csr.recognize(b"audio-bytes")
    assert text and "근로 계약서" in text
    assert seen["url"].startswith(clova_csr.DEFAULT_URL) and "lang=Kor" in seen["url"]
    assert seen["id"] == "csr-id" and seen["ctype"] == "application/octet-stream"
    assert seen["body"] == b"audio-bytes"


async def test_csr_too_long_sample_is_bad_request(keys, mock_transport):
    mock_transport(lambda request: httpx.Response(500, json=_sample("csr", "response_full_152s")))
    with pytest.raises(BadRequestError):
        await clova_csr.recognize(b"x")


async def test_csr_empty_text_and_failures(keys, mock_transport, monkeypatch):
    mock_transport(lambda request: httpx.Response(200, json={"text": "  "}))
    assert await clova_csr.recognize(b"x") == ""
    mock_transport(lambda request: httpx.Response(500, json={"errorCode": "STT999"}))
    with pytest.raises(AiUnavailableError):
        await clova_csr.recognize(b"x")
    monkeypatch.setattr(get_settings(), "ainaver_client_id", "")
    with pytest.raises(ServiceNotConfiguredError):
        await clova_csr.recognize(b"x")


# ---------- 음성 길이 ----------


def _wav(seconds: float, rate: int = 8000) -> bytes:
    import io

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(rate * seconds))
    return buf.getvalue()


def _mp3(frames: int) -> bytes:
    """MPEG-1 Layer III, 128kbps, 44.1kHz 프레임(417바이트) N개 = N × 1152/44100 초."""
    frame = bytes([0xFF, 0xFB, 0x90, 0x00]) + bytes(413)
    return frame * frames


def test_audio_durations():
    assert audio.wav_seconds(_wav(3)) == pytest.approx(3.0)
    assert audio.mp3_seconds(_mp3(100)) == pytest.approx(100 * 1152 / 44100, rel=0.01)
    assert audio.duration_seconds(_wav(2), "WAV") == pytest.approx(2.0)
    assert audio.duration_seconds(b"junk", "mp3") is None and audio.duration_seconds(b"junk", "wav") is None
    assert audio.duration_seconds(b"x", "ogg") is None


def test_mp3_with_id3_header():
    id3 = b"ID3\x03\x00\x00\x00\x00\x00\x0a" + bytes(10)
    assert audio.mp3_seconds(id3 + _mp3(50)) == pytest.approx(50 * 1152 / 44100, rel=0.01)


# ---------- 주 소정근로시간 읽기 ----------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("주 3일 하루 5시간 일하면 주휴수당 나와?", 15.0),
        ("주 15시간 일해요", 15.0),
        ("주 5일 매일 8시간 일하는데", 40.0),
        ("주 2일 4시간씩 일해요", 8.0),
        ("주휴수당 받을 수 있어?", None),
        ("주 3일 일해요", None),
    ],
)
def test_weekly_hours_from(question, expected):
    got = ask.weekly_hours_from(question)
    assert (got[0] if got else None) == expected


def test_calculation_text_uses_code_values():
    text, numbers = ask.calculation_text("주 3일 하루 5시간 일하면 주휴수당 나와?")
    assert "15시간" in text and "해당해요" in text and 3.0 in numbers
    text2, _ = ask.calculation_text("주 10시간 일해요")
    assert "해당하지 않아요" in text2
    assert ask.calculation_text("주휴수당 받을 수 있어?") is None


# ---------- 질문 라우팅 ----------


@pytest.fixture
def chatbot(monkeypatch):
    """Chatbot 대역. replies[질문] 이 없으면 기본 답변."""
    replies: dict[str, clova_chatbot.ChatbotAnswer] = {}
    calls: list[str] = []

    async def fake_ask(question: str):
        calls.append(question)
        return replies.get(question, clova_chatbot.ChatbotAnswer("기본 답변", None, "model", None, True))

    monkeypatch.setattr(clova_chatbot, "is_configured", lambda: True)
    monkeypatch.setattr(clova_chatbot, "ask", fake_ask)
    return replies, calls


@pytest.fixture
def studio(monkeypatch):
    """Studio 대역. 마지막 사용자 메시지를 prompts 에 쌓는다."""
    state = {
        "reply": "주휴수당은 근로기준법 제55조에서 정해요. 상담은 1350에 문의하세요.",
        "prompts": [],
        "fail": False,
    }

    async def fake_chat(messages, **kwargs):
        state["prompts"].append(messages[-1].content)
        if state["fail"]:
            raise AiUnavailableError()
        return state["reply"]

    monkeypatch.setattr(clova_studio, "is_configured", lambda: True)
    monkeypatch.setattr(clova_studio, "chat", fake_chat)
    return state


def _reply(text, score, matching, scenario="휴게시간"):
    return clova_chatbot.ChatbotAnswer(text, score, matching, scenario, is_fallback=False)


def test_faq_fits_question_exact_match_always_fits():
    assert ask.faq_fits_question("전혀 다른 말", _reply("아무 답", 1.0, "exactMatch"))


def test_faq_fits_question_model_match_needs_a_shared_keyword():
    reply = _reply("휴게시간은 4시간이면 30분 이상 받아야 해요.", 0.8, "model")
    assert ask.faq_fits_question("일하는 중간에 휴게시간 줘야 해?", reply)  # 답변에 나오는 핵심어
    assert ask.faq_fits_question("쉬는 날에 일해요", _reply("답", 0.8, "model", "휴게시간")) is False
    assert ask.faq_fits_question(
        "휴게 얼마나 줘야 돼?", _reply("답", 0.8, "model", "휴게시간")
    )  # 시나리오 이름과 일치
    assert ask.faq_fits_question("사장님이 욕해요", reply) is False  # 엉뚱한 FAQ


async def test_model_match_without_shared_keyword_goes_to_studio(chatbot, studio):
    replies, _ = chatbot
    replies["야근하면 수당은 안 나가?"] = _reply("휴게시간 안내예요.", 0.8, "model", "휴게시간")
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "studio"  # FAQ가 질문과 맞지 않아 근거 기반 설명으로


async def test_low_score_model_match_goes_to_studio(chatbot, studio):
    replies, _ = chatbot
    replies["야근하면 수당은 안 나가?"] = _reply("야근 수당 안내예요.", 0.72, "model", "야간수당")
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "studio"


async def test_faq_route(chatbot):
    replies, _ = chatbot
    replies["주휴수당 받을 수 있어?"] = clova_chatbot.ChatbotAnswer(
        "FAQ 답변이에요.", 1.0, "exactMatch", "주휴수당_조건", False
    )
    r = await ask.answer_question("주휴수당 받을 수 있어?")
    assert r.route == "faq" and r.answer == "FAQ 답변이에요."
    assert r.sources and r.sources[0].id.startswith("manual-")  # 출처도 함께


async def test_unmatched_goes_to_studio_with_evidence(chatbot, studio):
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "studio" and "제55조" in r.answer
    assert r.sources
    prompt = studio["prompts"][0]
    assert "[질문]" in prompt and "[근거 원문]" in prompt and "[계산 결과]" not in prompt


async def test_personal_hours_skip_chatbot_and_add_calculation(chatbot, studio):
    _, calls = chatbot
    r = await ask.answer_question("주 3일 하루 5시간 일하면 주휴수당 나와?")
    assert calls == []  # 일반 FAQ 대신 계산을 붙여 설명한다
    assert r.route == "studio"
    prompt = studio["prompts"][0]
    assert "[계산 결과]" in prompt and "주 소정근로시간: 15시간" in prompt and "해당해요" in prompt


async def test_number_guard_removes_unverified_sentences(chatbot, studio):
    studio["reply"] = (
        "주휴수당은 근로기준법 제55조에서 정해요. 한 달에 777,777원을 받아요. 상담은 1350이에요."
    )
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert "777,777" not in r.answer and "제55조" in r.answer


async def test_markdown_bold_is_stripped(chatbot, studio):
    studio["reply"] = "주휴수당은 **15시간 이상**이면 받아요. 상담은 1350이에요."
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert "**" not in r.answer and "15시간 이상" in r.answer


def test_prompt_forbids_assertive_conclusions():
    from app.prompts import load

    prompt = load("ask_explain_system")
    assert "단정하지 않는다" in prompt and "받을 수 없어요" in prompt and "확인이 필요해요" in prompt


async def test_all_sentences_unverified_falls_back(chatbot, studio):
    studio["reply"] = "월 987,654원을 받아요."
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "none" and r.answer == ask.NO_EXPLANATION and r.sources


async def test_studio_failure_keeps_sources(chatbot, studio):
    studio["fail"] = True
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "none" and r.answer == ask.NO_EXPLANATION and r.sources


async def test_no_evidence_gives_counseling_message(chatbot, studio):
    r = await ask.answer_question("zzzz없는단어qqq")
    assert r.route == "none" and r.answer == ask.NO_EVIDENCE and r.sources == [] and studio["prompts"] == []


async def test_chatbot_failure_falls_back_to_studio(monkeypatch, studio):
    async def boom(question):
        raise AiUnavailableError()

    monkeypatch.setattr(clova_chatbot, "is_configured", lambda: True)
    monkeypatch.setattr(clova_chatbot, "ask", boom)
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "studio"


async def test_blank_question_means_heard_nothing(chatbot):
    r = await ask.answer_question("   ")
    assert r.route == "none" and r.answer == ask.HEARD_NOTHING and r.question == ""


async def test_studio_unconfigured(monkeypatch, chatbot):
    monkeypatch.setattr(clova_studio, "is_configured", lambda: False)
    r = await ask.answer_question("야근하면 수당은 안 나가?")
    assert r.route == "none" and r.sources


# ---------- 라우트 ----------

app = FastAPI()
register_exception_handlers(app)
app.include_router(ask_route.router, prefix="/api")
client = TestClient(app)


def test_route_text_ok(chatbot, studio):
    res = client.post("/api/ask/text", json={"question": "야근하면 수당은 안 나가?"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["route"] == "studio" and data["question"] == "야근하면 수당은 안 나가?" and data["sources"]


@pytest.mark.parametrize("body", [{}, {"question": "a"}, {"question": "가" * 301}])
def test_route_text_validation(body):
    res = client.post("/api/ask/text", json=body)
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"


def _voice(data: bytes, name: str = "q.wav"):
    return client.post("/api/ask/voice", files={"file": (name, data, "application/octet-stream")})


def test_route_voice_ok(chatbot, studio, monkeypatch):
    replies, _ = chatbot
    replies["주휴수당 받을 수 있어?"] = clova_chatbot.ChatbotAnswer(
        "FAQ 답변이에요.", 1.0, "exactMatch", "s", False
    )
    seen = {}

    async def fake_recognize(data: bytes) -> str:
        seen["size"] = len(data)
        return "주휴수당 받을 수 있어?"

    monkeypatch.setattr(clova_csr, "recognize", fake_recognize)
    wav = _wav(2)
    res = _voice(wav)
    assert res.status_code == 200
    assert res.json()["data"]["route"] == "faq" and res.json()["data"]["question"] == "주휴수당 받을 수 있어?"
    assert seen["size"] == len(wav)


def test_route_voice_nothing_heard(chatbot, monkeypatch):
    async def fake_recognize(data: bytes) -> str:
        return ""

    monkeypatch.setattr(clova_csr, "recognize", fake_recognize)
    res = _voice(_wav(1))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["route"] == "none" and data["answer"] == ask.HEARD_NOTHING  # BR-13


def test_route_voice_rejects_long_audio_without_calling_csr(monkeypatch):
    async def must_not_call(data: bytes) -> str:
        raise AssertionError("CSR 을 부르면 안 된다")

    monkeypatch.setattr(clova_csr, "recognize", must_not_call)
    res = _voice(_wav(61 + 1, rate=1000), "long.wav")  # 62초
    assert res.status_code == 400 and res.json()["error"]["code"] == "BAD_REQUEST"
    res = _voice(_mp3(2400), "long.mp3")  # 약 62.7초
    assert res.status_code == 400


def test_route_voice_accepts_boundary_length(chatbot, studio, monkeypatch):
    async def fake_recognize(data: bytes) -> str:
        return "야근하면 수당은 안 나가?"

    monkeypatch.setattr(clova_csr, "recognize", fake_recognize)
    assert _voice(_wav(60, rate=1000)).status_code == 200


def test_route_voice_file_validation():
    assert _voice(b"x", "q.txt").status_code == 400
    assert _voice(b"x", "q.txt").json()["error"]["code"] == "UNSUPPORTED_FILE"
    assert _voice(b"", "q.wav").status_code == 400
    assert _voice(b"x" * (ask_route.MAX_AUDIO_BYTES + 1), "q.mp3").status_code == 413
    assert client.post("/api/ask/voice").status_code == 422


def test_route_voice_csr_failure_is_502(keys, mock_transport):
    mock_transport(lambda request: httpx.Response(500, json={"errorCode": "STT999"}))
    res = _voice(_wav(1))
    assert res.status_code == 502 and res.json()["error"]["code"] == "AI_UNAVAILABLE"
