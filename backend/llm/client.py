"""LLM client for OpenAI-compatible chat-completions APIs (GitHub Models by default)."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from backend.config import Settings, get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when the LLM call fails. `user_message` is safe to show to end users (Arabic)."""

    def __init__(self, message: str, user_message: str, status: int | None = None):
        super().__init__(message)
        self.user_message = user_message
        self.status = status


class LLMClient:
    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings or get_settings()
        self._transport = transport

    # ---- internals -------------------------------------------------------
    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
            transport=self._transport,
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
        )

    def _payload(self, system: str, user: str, **extra) -> dict:
        return {
            "model": self.settings.llm_model,
            "temperature": self.settings.llm_temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **extra,
        }

    @staticmethod
    def _error_for_status(status: int, body: str) -> LLMError:
        if status in (401, 403):
            return LLMError(f"auth failed ({status}): {body}", "مفتاح الوصول غير صالح. يرجى التحقق من الإعدادات.", status)
        if status == 429:
            return LLMError(f"rate limited: {body}", "تم تجاوز حد الطلبات. يرجى المحاولة بعد قليل.", status)
        return LLMError(f"LLM HTTP {status}: {body}", "حدث خطأ في خدمة الذكاء الاصطناعي. يرجى المحاولة لاحقاً.", status)

    async def _post_with_retries(self, payload: dict) -> dict:
        attempts = self.settings.llm_max_retries + 1
        last: LLMError | None = None
        async with self._http() as http:
            for attempt in range(attempts):
                try:
                    resp = await http.post("/chat/completions", json=payload)
                except httpx.TimeoutException as e:
                    last = LLMError(f"timeout: {e}", "انتهت مهلة الاتصال بخدمة الذكاء الاصطناعي.")
                except httpx.HTTPError as e:
                    last = LLMError(f"network error: {e}", "تعذر الاتصال بخدمة الذكاء الاصطناعي.")
                else:
                    if resp.status_code == 200:
                        try:
                            return resp.json()
                        except ValueError as e:
                            raise LLMError(
                                f"non-JSON 200 response ({resp.headers.get('content-type')}): {resp.text[:200]!r}",
                                "استجابة غير متوقعة من خدمة الذكاء الاصطناعي. قد يكون هناك وكيل شبكة (proxy) يعترض الاتصال.",
                            ) from e
                    last = self._error_for_status(resp.status_code, resp.text[:500])
                    if resp.status_code not in RETRYABLE_STATUS:
                        raise last
                log.warning("LLM attempt %d/%d failed: %s", attempt + 1, attempts, last)
                if attempt < attempts - 1:
                    await asyncio.sleep(min(2**attempt, 8) * 0.5)
        assert last is not None
        raise last

    # ---- public API ------------------------------------------------------
    async def complete(self, system: str, user: str) -> str:
        data = await self._post_with_retries(self._payload(system, user))
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"malformed response: {data}", "استجابة غير متوقعة من خدمة الذكاء الاصطناعي.") from e

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        """Yield text deltas as they arrive (server-sent events). No retries once streaming starts."""
        payload = self._payload(system, user, stream=True)
        async with self._http() as http:
            try:
                async with http.stream("POST", "/chat/completions", json=payload) as resp:
                    if resp.status_code != 200:
                        body = (await resp.aread()).decode("utf-8", "replace")[:500]
                        raise self._error_for_status(resp.status_code, body)
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content")
                        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                            log.debug("skipping unparsable stream chunk: %r", data)
                            continue
                        if delta:
                            yield delta
            except httpx.TimeoutException as e:
                raise LLMError(f"timeout: {e}", "انتهت مهلة الاتصال بخدمة الذكاء الاصطناعي.") from e
            except httpx.HTTPError as e:
                raise LLMError(f"network error: {e}", "تعذر الاتصال بخدمة الذكاء الاصطناعي.") from e

    async def complete_json(self, system: str, user: str, schema: type[T]) -> T:
        """Ask for a JSON object matching `schema` and validate it."""
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        system_full = f"{system}\n\nأعد الإجابة ككائن JSON صالح فقط يطابق هذا المخطط:\n{schema_hint}"
        data = await self._post_with_retries(
            self._payload(system_full, user, response_format={"type": "json_object"})
        )
        try:
            content = data["choices"][0]["message"]["content"]
            return schema.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValidationError) as e:
            raise LLMError(f"invalid JSON output: {e}", "لم يتمكن النموذج من إنتاج نتيجة منظمة. يرجى المحاولة مرة أخرى.") from e
