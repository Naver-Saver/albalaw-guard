import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import translate as translate_route
from app.core.config import get_settings
from app.core.errors import AiUnavailableError, BadRequestError, ServiceNotConfiguredError
from app.core.response import register_exception_handlers
from app.services import papago, translate

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "raw" / "papago"


def _sample(name: str) -> dict:
    return json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def _ok(text: str, target: str = "en") -> httpx.Response:
    """실제 응답 샘플(samples/raw/papago/ok_en.json)과 같은 구조."""
    return httpx.Response(
        200,
        json={"message": {"result": {"srcLangType": "ko", "tarLangType": target, "translatedText": text}}},
    )


@pytest.fixture(autouse=True)
def _fresh_cache():
    translate.clear_cache()
    yield
    translate.clear_cache()


@pytest.fixture
def papago_keys(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "papago_client_id", "test-id")
    monkeypatch.setattr(s, "papago_client_secret", "test-secret")
    return s


@pytest.fixture
def fake_papago(papago_keys, mock_transport):
    """'[타깃]원문' 으로 번역하는 가짜 Papago. calls 에 요청 본문을 쌓는다."""
    calls: list[dict] = []

    def handler(request: httpx.Request):
        body = json.loads(request.read())
        calls.append(body)
        return _ok(f"[{body['target']}]{body['text']}", body["target"])

    mock_transport(handler)
    return calls


# ---------- papago.translate_one ----------


async def test_translate_one_request_and_parsing(papago_keys, mock_transport):
    seen = {}
    sample = _sample("ok_en")

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["id"] = request.headers["X-NCP-APIGW-API-KEY-ID"]
        seen["key"] = request.headers["X-NCP-APIGW-API-KEY"]
        seen["body"] = json.loads(request.read())
        return httpx.Response(200, json=sample)

    mock_transport(handler)
    out = await papago.translate_one("시급이 최저임금보다 낮을 수 있어요.", "en")
    assert out == sample["message"]["result"]["translatedText"]
    assert seen["url"] == papago.DEFAULT_URL
    assert (seen["id"], seen["key"]) == ("test-id", "test-secret")
    assert seen["body"] == {"source": "ko", "target": "en", "text": "시급이 최저임금보다 낮을 수 있어요."}


async def test_translate_one_error_response(papago_keys, mock_transport):
    mock_transport(lambda request: httpx.Response(400, json=_sample("bad_target")))
    with pytest.raises(AiUnavailableError):
        await papago.translate_one("안녕하세요", "xx")


async def test_translate_one_unexpected_shape(papago_keys, mock_transport):
    mock_transport(lambda request: httpx.Response(200, json={"message": {}}))
    with pytest.raises(AiUnavailableError):
        await papago.translate_one("안녕", "en")


async def test_translate_one_not_configured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "papago_client_id", "")
    monkeypatch.setattr(s, "papago_client_secret", "")
    with pytest.raises(ServiceNotConfiguredError):
        await papago.translate_one("안녕", "en")


async def test_translate_one_retries_5xx_once(papago_keys, mock_transport):
    attempts = []

    def handler(request: httpx.Request):
        attempts.append(1)
        return httpx.Response(503) if len(attempts) == 1 else _ok("Hello")

    mock_transport(handler)
    assert await papago.translate_one("안녕", "en") == "Hello"
    assert len(attempts) == 2


async def test_translate_one_gives_up_after_retry(papago_keys, mock_transport):
    mock_transport(lambda request: httpx.Response(500))
    with pytest.raises(AiUnavailableError):
        await papago.translate_one("안녕", "en")


# ---------- translate.translate_texts ----------


async def test_korean_target_passthrough_without_calls(fake_papago):
    assert await translate.translate_texts(["가", "나"], "ko") == ["가", "나"]
    assert fake_papago == []


async def test_unsupported_target(fake_papago):
    with pytest.raises(BadRequestError):
        await translate.translate_texts(["가"], "xx")
    assert fake_papago == []


async def test_order_dedupe_and_blank(fake_papago):
    out = await translate.translate_texts(["가", "", "나", "가", "  "], "vi")
    assert out == ["[vi]가", "", "[vi]나", "[vi]가", "  "]
    assert sorted(c["text"] for c in fake_papago) == ["가", "나"]  # 같은 문장은 한 번만, 빈 문장은 호출 안 함


async def test_cache_reuses_translations(fake_papago):
    await translate.translate_texts(["가"], "en")
    await translate.translate_texts(["가", "나"], "en")
    assert [c["text"] for c in fake_papago] == ["가", "나"]
    await translate.translate_texts(["가"], "vi")  # 언어가 다르면 다시 번역
    assert len(fake_papago) == 3


async def test_failure_returns_original_by_default(papago_keys, mock_transport):
    def handler(request: httpx.Request):
        body = json.loads(request.read())
        return httpx.Response(500) if body["text"] == "실패" else _ok("ok")

    mock_transport(handler)
    out = await translate.translate_texts(["성공", "실패"], "en")
    assert out == ["ok", "실패"]


async def test_failure_is_not_cached(papago_keys, mock_transport):
    state = {"fail": True}

    def handler(request: httpx.Request):
        return httpx.Response(500) if state["fail"] else _ok("fixed")

    mock_transport(handler)
    assert await translate.translate_texts(["가"], "en") == ["가"]
    state["fail"] = False
    assert await translate.translate_texts(["가"], "en") == ["fixed"]


async def test_strict_raises(papago_keys, mock_transport):
    mock_transport(lambda request: httpx.Response(500))
    with pytest.raises(AiUnavailableError):
        await translate.translate_texts(["가"], "en", strict=True)


async def test_not_configured_non_strict_returns_original(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "papago_client_id", "")
    monkeypatch.setattr(s, "papago_client_secret", "")
    assert await translate.translate_texts(["가"], "en") == ["가"]


async def test_long_text_is_chunked(fake_papago):
    sentence = "이 문장은 길이를 늘리기 위한 문장이에요. "
    text = sentence * 400  # 4,500자 초과
    out = await translate.translate_texts([text], "en")
    assert len(fake_papago) >= 2
    assert all(len(c["text"]) <= papago.MAX_CHARS for c in fake_papago)
    assert out[0].count("[en]") == len(fake_papago)


def test_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(translate, "CACHE_MAX", 3)
    for i in range(10):
        translate._cache_put(("ko", "en", str(i)), "x")
    assert len(translate._cache) == 3 and ("ko", "en", "9") in translate._cache


# ---------- translate.translate_result ----------


def _review_result() -> dict:
    return {
        "calculation": {"year": 2026, "minimum_hourly": 1000, "meets_minimum": False},
        "items": [{"level": "check", "title": "시급 확인", "description": "최저임금보다 낮아요."}],
        "explanation": "확인이 필요해요.",
        "sources": [{"id": "manual-005", "title": "최저임금보다 적게 받기로 계약하면", "snippet": "원문"}],
        "disclaimer": "법률 자문이 아니에요.",
    }


async def test_translate_result_translates_only_explanations(fake_papago):
    original = _review_result()
    out = await translate.translate_result(original, "en")
    assert out["explanation"] == "[en]확인이 필요해요."
    assert out["disclaimer"] == "[en]법률 자문이 아니에요."
    assert out["items"][0] == {
        "level": "check",
        "title": "[en]시급 확인",
        "description": "[en]최저임금보다 낮아요.",
    }
    assert out["sources"] == original["sources"]  # 출처 제목·원문은 번역하지 않는다
    assert out["calculation"] == original["calculation"]
    assert original == _review_result()  # 입력은 바뀌지 않는다


async def test_translate_result_common_format(fake_papago):
    result = {
        "lang": "ko",
        "findings": [
            {
                "type": "MISSING",
                "item": "휴게시간",
                "evidenceText": "원문 그대로",
                "explanation": "빠져 있어요.",
            }
        ],
        "verbalPromises": [{"segmentIdx": 7, "text": "발언 원문", "advice": "계약서에 적어 달라고 하세요."}],
        "checklistForNextTime": ["휴게시간을 확인하세요."],
        "explanation": None,
    }
    out = await translate.translate_result(result, "zh-CN")
    assert out["lang"] == "zh-CN"
    assert out["findings"][0]["explanation"] == "[zh-CN]빠져 있어요."
    assert out["findings"][0]["evidenceText"] == "원문 그대로"
    assert out["findings"][0]["item"] == "휴게시간"
    assert out["verbalPromises"][0]["text"] == "발언 원문"
    assert out["verbalPromises"][0]["advice"] == "[zh-CN]계약서에 적어 달라고 하세요."
    assert out["checklistForNextTime"] == ["[zh-CN]휴게시간을 확인하세요."]
    assert out["explanation"] is None


async def test_translate_result_korean_is_copy(fake_papago):
    original = _review_result()
    out = await translate.translate_result(original, "ko")
    assert out == original and out is not original
    assert fake_papago == []


async def test_translate_result_keeps_original_on_failure(papago_keys, mock_transport):
    mock_transport(lambda request: httpx.Response(500))
    out = await translate.translate_result(_review_result(), "en")
    assert out == _review_result()


async def test_translate_result_unsupported_target(fake_papago):
    with pytest.raises(BadRequestError):
        await translate.translate_result(_review_result(), "xx")


# ---------- POST /translate ----------

app = FastAPI()
register_exception_handlers(app)
app.include_router(translate_route.router, prefix="/api")
client = TestClient(app)


def test_route_translate(fake_papago):
    res = client.post("/api/translate", json={"texts": ["가", "나"], "target": "en"})
    assert res.status_code == 200
    assert res.json() == {"success": True, "data": {"texts": ["[en]가", "[en]나"], "target": "en"}}


def test_route_korean_passthrough(fake_papago):
    res = client.post("/api/translate", json={"texts": ["가"], "target": "ko"})
    assert res.json()["data"] == {"texts": ["가"], "target": "ko"}
    assert fake_papago == []


def test_route_validation(fake_papago):
    for body in (
        {"texts": ["가"], "target": "xx"},
        {"texts": ["가"] * 31, "target": "en"},
        {"target": "en"},
    ):
        res = client.post("/api/translate", json=body)
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_route_returns_502_on_failure(papago_keys, mock_transport):
    mock_transport(lambda request: httpx.Response(500))
    res = client.post("/api/translate", json={"texts": ["가"], "target": "en"})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "AI_UNAVAILABLE"
