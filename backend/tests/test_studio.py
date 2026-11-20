import json

import httpx
import pytest

from app.core.errors import AiUnavailableError, ServiceNotConfiguredError
from app.prompts import load
from app.services import clova_studio
from app.services.clova_studio import Message
from app.services.number_guard import filter_unverified_sentences


def _ok(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"status": {"code": "20000"}, "result": {"message": {"role": "assistant", "content": content}}},
    )


async def test_chat_headers_and_body(settings, mock_transport):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["rid"] = request.headers["X-NCP-CLOVASTUDIO-REQUEST-ID"]
        seen["body"] = json.loads(request.read())
        return _ok("  설명이에요.  ")

    mock_transport(handler)
    out = await clova_studio.chat([Message("system", "s"), Message("user", "u")], max_tokens=100)
    assert out == "설명이에요."
    assert seen["url"].endswith("/testapp/v3/chat-completions/HCX-005")
    assert seen["auth"] == "Bearer nv-test"
    assert seen["rid"] == "req-test"
    assert seen["body"]["maxTokens"] == 100 and seen["body"]["messages"][1] == {
        "role": "user",
        "content": "u",
    }


async def test_chat_strips_duplicate_bearer(settings, mock_transport, monkeypatch):
    monkeypatch.setattr(settings, "clova_studio_api_key", "Bearer nv-test")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["Authorization"]
        return _ok("ok")

    mock_transport(handler)
    await clova_studio.chat([Message("user", "u")])
    assert seen["auth"] == "Bearer nv-test"


async def test_chat_error_status(settings, mock_transport):
    mock_transport(lambda r: httpx.Response(200, json={"status": {"code": "40001"}, "result": None}))
    with pytest.raises(AiUnavailableError):
        await clova_studio.chat([Message("user", "u")])


async def test_chat_not_configured(settings, monkeypatch):
    monkeypatch.setattr(settings, "clova_studio_api_key", "")
    with pytest.raises(ServiceNotConfiguredError):
        await clova_studio.chat([Message("user", "u")])


def test_number_guard_removes_unverified_numbers():
    text = (
        "시급이 10,000원이라 최저임금 10,320원보다 낮아요. 한 달에 99,999원을 덜 받아요. 1350에 상담하세요."
    )
    kept, removed = filter_unverified_sentences(text, {10_000, 10_320})
    assert "99,999" not in kept
    assert removed == ["한 달에 99,999원을 덜 받아요."]
    assert kept.endswith("1350에 상담하세요.")


def test_prompt_template_loads():
    assert "1350" in load("review_explain_system")
