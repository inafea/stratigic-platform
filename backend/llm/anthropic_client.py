"""Claude provider (LLM_PROVIDER=anthropic) using the official Anthropic SDK.

Same interface as `LLMClient`: complete(), complete_json(), stream(); errors are raised as LLMError.
Structured output uses the SDK's `messages.parse(output_format=Model)`.
Server-side refusal fallbacks are enabled on the models that support them.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.llm.client import LLMError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

MAX_TOKENS_JSON = 16000
MAX_TOKENS_STREAM = 16000

REFUSAL_MSG = "اعتذر النموذج عن الإجابة على هذا الطلب. يرجى إعادة صياغة الفكرة."
TRUNCATED_MSG = "كانت الإجابة أطول من الحد المسموح. يرجى المحاولة مرة أخرى."


class AnthropicLLMClient:
    def __init__(self, settings: Settings | None = None, client: anthropic.AsyncAnthropic | None = None):
        self.settings = settings or get_settings()
        self.model = self.settings.llm_model
        self.client = client or anthropic.AsyncAnthropic(
            api_key=self.settings.llm_api_key or None,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )

    # ---- helpers ---------------------------------------------------------------
    def _extra(self) -> dict[str, Any]:
        """Beta flags + fallbacks for models that support server-side refusal fallback."""
        if self.model in FALLBACK_MODELS:
            return {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return {"betas": []}

    @staticmethod
    def _translate(e: Exception) -> LLMError:
        if isinstance(e, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
            return LLMError(f"auth: {e}", "مفتاح Claude غير صالح. يرجى التحقق من LLM_API_KEY.", e.status_code)
        if isinstance(e, anthropic.RateLimitError):
            return LLMError(f"rate limited: {e}", "تم تجاوز حد الطلبات لدى Claude. يرجى المحاولة بعد قليل.", 429)
        if isinstance(e, anthropic.NotFoundError):
            return LLMError(f"not found: {e}", "اسم النموذج غير صحيح. تحقق من LLM_MODEL.", 404)
        if isinstance(e, anthropic.BadRequestError):
            return LLMError(f"bad request: {e}", "رفضت خدمة Claude الطلب. يرجى المحاولة لاحقاً.", 400)
        if isinstance(e, anthropic.APITimeoutError):
            return LLMError(f"timeout: {e}", "انتهت مهلة الاتصال بخدمة الذكاء الاصطناعي.")
        if isinstance(e, anthropic.APIConnectionError):
            return LLMError(f"connection: {e}", "تعذر الاتصال بخدمة الذكاء الاصطناعي.")
        if isinstance(e, anthropic.APIStatusError):
            return LLMError(f"HTTP {e.status_code}: {e}", "حدث خطأ في خدمة الذكاء الاصطناعي. يرجى المحاولة لاحقاً.",
                            e.status_code)
        return LLMError(f"unexpected: {e!r}", "حدث خطأ غير متوقع في خدمة الذكاء الاصطناعي.")

    @staticmethod
    def _check_stop(response) -> None:
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise LLMError(f"refusal: {details}", REFUSAL_MSG)
        if response.stop_reason == "max_tokens":
            raise LLMError("hit max_tokens", TRUNCATED_MSG)

    # ---- public API --------------------------------------------------------------
    async def complete(self, system: str, user: str) -> str:
        try:
            response = await self.client.beta.messages.create(
                model=self.model, max_tokens=MAX_TOKENS_JSON, system=system,
                messages=[{"role": "user", "content": user}], **self._extra(),
            )
        except anthropic.APIError as e:
            raise self._translate(e) from e
        self._check_stop(response)
        return "".join(b.text for b in response.content if b.type == "text")

    async def complete_json(self, system: str, user: str, schema: type[T]) -> T:
        try:
            response = await self.client.beta.messages.parse(
                model=self.model, max_tokens=MAX_TOKENS_JSON, system=system,
                messages=[{"role": "user", "content": user}], output_format=schema, **self._extra(),
            )
        except anthropic.APIError as e:
            raise self._translate(e) from e
        except Exception as e:  # validation of the parsed output
            raise LLMError(f"invalid structured output: {e}",
                           "لم يتمكن النموذج من إنتاج نتيجة منظمة. يرجى المحاولة مرة أخرى.") from e
        self._check_stop(response)
        parsed = response.parsed_output
        if parsed is None:
            raise LLMError("no parsed output", "لم يتمكن النموذج من إنتاج نتيجة منظمة. يرجى المحاولة مرة أخرى.")
        return parsed

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        try:
            async with self.client.beta.messages.stream(
                model=self.model, max_tokens=MAX_TOKENS_STREAM, system=system,
                messages=[{"role": "user", "content": user}], **self._extra(),
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
        except anthropic.APIError as e:
            raise self._translate(e) from e
        if final.stop_reason == "refusal":
            raise LLMError("refusal mid-stream", REFUSAL_MSG)
