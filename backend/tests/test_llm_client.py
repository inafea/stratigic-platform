import json

import httpx
import pytest
from pydantic import BaseModel

from backend.config import Settings
from backend.llm.client import LLMClient, LLMError


class Thing(BaseModel):
    name: str
    score: int


def settings(**kw) -> Settings:
    return Settings(_env_file=None, llm_api_key="k", llm_max_retries=2, **kw)


def ok(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def make_client(handler, **kw) -> LLMClient:
    return LLMClient(settings(**kw), transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _sleep(_):
        return None
    monkeypatch.setattr("backend.llm.client.asyncio.sleep", _sleep)


async def test_complete_sends_auth_and_model():
    seen = {}

    def handler(req: httpx.Request):
        seen["auth"] = req.headers["authorization"]
        seen["body"] = json.loads(req.content)
        return ok("مرحبا")

    out = await make_client(handler).complete("sys", "user")
    assert out == "مرحبا"
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["model"] == "openai/gpt-4.1-mini"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}


async def test_complete_json_validates():
    def handler(req):
        assert json.loads(req.content)["response_format"] == {"type": "json_object"}
        return ok('{"name": "x", "score": 7}')

    out = await make_client(handler).complete_json("s", "u", Thing)
    assert out == Thing(name="x", score=7)


async def test_complete_json_invalid_raises():
    out = make_client(lambda r: ok('{"name": "x"}'))
    with pytest.raises(LLMError):
        await out.complete_json("s", "u", Thing)


async def test_retries_then_succeeds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else ok("done")

    assert await make_client(handler).complete("s", "u") == "done"
    assert calls["n"] == 3


async def test_retries_exhausted():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(429, text="slow down")

    with pytest.raises(LLMError) as e:
        await make_client(handler).complete("s", "u")
    assert e.value.status == 429
    assert calls["n"] == 3


async def test_auth_error_not_retried():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(401)

    with pytest.raises(LLMError) as e:
        await make_client(handler).complete("s", "u")
    assert calls["n"] == 1
    assert "مفتاح" in e.value.user_message


async def test_timeout_is_retried():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("t", request=req)
        return ok("ok")

    assert await make_client(handler).complete("s", "u") == "ok"


def sse(*deltas: str, done: bool = True) -> bytes:
    lines = [": keep-alive", ""]
    for d in deltas:
        lines.append("data: " + json.dumps({"choices": [{"delta": {"content": d}}]}, ensure_ascii=False))
        lines.append("")
    lines.append("data: {not json}")
    if done:
        lines.append("data: [DONE]")
    return ("\n".join(lines) + "\n").encode("utf-8")


async def test_stream_yields_deltas():
    def handler(req):
        assert json.loads(req.content)["stream"] is True
        return httpx.Response(200, content=sse("تحليل", " ", "السوق"))

    parts = [p async for p in make_client(handler).stream("s", "u")]
    assert parts == ["تحليل", " ", "السوق"]


async def test_stream_error_status():
    with pytest.raises(LLMError) as e:
        [p async for p in make_client(lambda r: httpx.Response(401)).stream("s", "u")]
    assert e.value.status == 401


async def test_non_json_200_raises_llm_error():
    client = make_client(lambda r: httpx.Response(200, text="OK", headers={"content-type": "text/plain"}))
    with pytest.raises(LLMError) as e:
        await client.complete("s", "u")
    assert "proxy" in e.value.user_message
