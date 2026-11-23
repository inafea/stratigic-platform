import json

import anthropic
import httpx2
import pytest

from backend.config import Settings
from backend.llm.anthropic_client import FALLBACK_BETA, AnthropicLLMClient
from backend.llm.client import LLMError
from backend.schemas import SWOT


def settings(model="claude-opus-5-5") -> Settings:
    return Settings(_env_file=None, llm_provider="anthropic", llm_api_key="sk-test", llm_model=model,
                    llm_max_retries=0)


def message(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def make(handler, model="claude-opus-5-5") -> AnthropicLLMClient:
    http = anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    client = anthropic.AsyncAnthropic(api_key="sk-test", http_client=http, max_retries=0)
    return AnthropicLLMClient(settings(model), client=client)


SWOT_JSON = json.dumps({"strengths": ["خبرة"], "weaknesses": ["فريق صغير"],
                        "opportunities": ["التحول السحابي"], "threats": ["منافسون كبار"]}, ensure_ascii=False)


async def test_complete_json_parses_and_sends_fallbacks():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        seen["beta"] = req.headers.get("anthropic-beta", "")
        return httpx2.Response(200, json=message(SWOT_JSON))

    out = await make(handler).complete_json("نظام", "مستخدم", SWOT)
    assert out.opportunities == ["التحول السحابي"]
    body = seen["body"]
    assert body["model"] == "claude-opus-5-5"
    assert body["system"] == "نظام"
    assert body["fallbacks"] == "default"
    assert FALLBACK_BETA in seen["beta"]
    assert "temperature" not in body
    assert body["output_config"]["format"]["type"] == "json_schema"


async def test_no_fallbacks_for_haiku():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx2.Response(200, json=message("مرحبا"))

    assert await make(handler, model="claude-haiku-5-5").complete("s", "u") == "مرحبا"
    assert "fallbacks" not in seen["body"]


async def test_refusal_raises_arabic_error():
    with pytest.raises(LLMError) as e:
        await make(lambda r: httpx2.Response(200, json=message("", "refusal"))).complete("s", "u")
    assert "اعتذر" in e.value.user_message


async def test_max_tokens_raises():
    with pytest.raises(LLMError):
        await make(lambda r: httpx2.Response(200, json=message("...", "max_tokens"))).complete("s", "u")


async def test_auth_error_translated():
    err = {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}
    with pytest.raises(LLMError) as e:
        await make(lambda r: httpx2.Response(401, json=err)).complete("s", "u")
    assert e.value.status == 401
    assert "Claude" in e.value.user_message


async def test_invalid_json_output_raises():
    with pytest.raises(LLMError):
        await make(lambda r: httpx2.Response(200, json=message('{"strengths": "oops"}'))).complete_json("s", "u", SWOT)


def sse_body(chunks: list[str]) -> bytes:
    def ev(name, data):
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    start = message("")
    start["content"] = []
    start["stop_reason"] = None
    out = ev("message_start", {"type": "message_start", "message": start})
    out += ev("content_block_start", {"type": "content_block_start", "index": 0,
                                      "content_block": {"type": "text", "text": ""}})
    for c in chunks:
        out += ev("content_block_delta", {"type": "content_block_delta", "index": 0,
                                          "delta": {"type": "text_delta", "text": c}})
    out += ev("content_block_stop", {"type": "content_block_stop", "index": 0})
    out += ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                "usage": {"output_tokens": 5}})
    out += ev("message_stop", {"type": "message_stop"})
    return out.encode("utf-8")


async def test_stream_yields_text():
    def handler(req):
        assert json.loads(req.content)["stream"] is True
        return httpx2.Response(200, content=sse_body(["تحليل ", "السوق"]),
                               headers={"content-type": "text/event-stream"})

    parts = [p async for p in make(handler).stream("s", "u")]
    assert "".join(parts) == "تحليل السوق"


def test_factory_selects_anthropic(monkeypatch):
    from backend import main
    from backend.llm.anthropic_client import AnthropicLLMClient as C
    monkeypatch.setattr(main, "get_settings", lambda: settings())
    assert isinstance(main.get_analyzer().llm, C)
