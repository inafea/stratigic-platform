"""English versions of the user-facing error messages.

Messages are written in Arabic throughout the backend; `tr` swaps in the English text when the
browser asks for English (header `X-Lang: en`). Unknown messages are returned unchanged.
"""
from __future__ import annotations

from fastapi import Request

EN: dict[str, str] = {
    # API
    "عدد كبير من الطلبات. يرجى الانتظار قليلاً ثم المحاولة.": "Too many requests. Please wait a moment and try again.",
    "لم يتم إعداد مفتاح خدمة الذكاء الاصطناعي على الخادم.": "The AI service key is not configured on the server.",
    "حدث خطأ غير متوقع أثناء التحليل.": "An unexpected error occurred during the analysis.",
    "التقرير غير موجود.": "Report not found.",
    "القسم غير موجود.": "Section not found.",
    "حدث خطأ غير متوقع.": "An unexpected error occurred.",
    # accounts
    "البريد الإلكتروني أو كلمة المرور غير صحيحة.": "Incorrect email or password.",
    "هذا البريد الإلكتروني مسجل مسبقاً. سجّل الدخول بدلاً من ذلك.":
        "This email is already registered. Please log in instead.",
    "يرجى تسجيل الدخول أولاً.": "Please log in first.",
    "انتهت صلاحية الصفحة. يرجى تحديثها ثم المحاولة مرة أخرى.":
        "This page has expired. Please refresh it and try again.",
    "الرابط غير صالح أو منتهي الصلاحية. يرجى طلب رابط جديد.":
        "This link is invalid or has expired. Please request a new one.",
    # LLM (shared)
    "انتهت مهلة الاتصال بخدمة الذكاء الاصطناعي.": "The connection to the AI service timed out.",
    "تعذر الاتصال بخدمة الذكاء الاصطناعي.": "Could not connect to the AI service.",
    "حدث خطأ في خدمة الذكاء الاصطناعي. يرجى المحاولة لاحقاً.": "The AI service returned an error. Please try again later.",
    "لم يتمكن النموذج من إنتاج نتيجة منظمة. يرجى المحاولة مرة أخرى.":
        "The model could not produce a structured result. Please try again.",
    # OpenAI-compatible client
    "مفتاح الوصول غير صالح. يرجى التحقق من الإعدادات.": "The access key is invalid. Please check the settings.",
    "تم تجاوز حد الطلبات. يرجى المحاولة بعد قليل.":
        "The AI service's request limit was reached. Please try again shortly.",
    "استجابة غير متوقعة من خدمة الذكاء الاصطناعي. قد يكون هناك وكيل شبكة (proxy) يعترض الاتصال.":
        "Unexpected response from the AI service. A network proxy may be intercepting the connection.",
    "استجابة غير متوقعة من خدمة الذكاء الاصطناعي.": "Unexpected response from the AI service.",
    # Claude client
    "اعتذر النموذج عن الإجابة على هذا الطلب. يرجى إعادة صياغة الفكرة.":
        "The model declined to answer this request. Please rephrase the idea.",
    "كانت الإجابة أطول من الحد المسموح. يرجى المحاولة مرة أخرى.":
        "The answer was longer than the allowed limit. Please try again.",
    "مفتاح Claude غير صالح. يرجى التحقق من LLM_API_KEY.": "The Claude key is invalid. Please check LLM_API_KEY.",
    "تم تجاوز حد الطلبات لدى Claude. يرجى المحاولة بعد قليل.": "Claude's rate limit was reached. Please try again shortly.",
    "اسم النموذج غير صحيح. تحقق من LLM_MODEL.": "The model name is incorrect. Check LLM_MODEL.",
    "رصيد حساب Anthropic غير كافٍ. يرجى شحن الرصيد من Plans & Billing في console.anthropic.com.":
        "The Anthropic account has insufficient credit. Add credit under Plans & Billing at console.anthropic.com.",
    "رفضت خدمة Claude الطلب. يرجى المحاولة لاحقاً.": "Claude rejected the request. Please try again later.",
    "حدث خطأ غير متوقع في خدمة الذكاء الاصطناعي.": "An unexpected error occurred in the AI service.",
}


def request_lang(request: Request) -> str:
    return "en" if request.headers.get("x-lang", "").lower().startswith("en") else "ar"


def tr(message: str, lang: str) -> str:
    return EN.get(message, message) if lang == "en" else message
