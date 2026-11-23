"""Test doubles: a fake LLM that returns valid sample data for any schema."""
from __future__ import annotations

from pydantic import BaseModel

from backend.llm.client import LLMError
from backend.schemas import SECTIONS, ClarifyingQuestions

PHASE = {"goals": ["هدف"], "actions": ["إجراء"]}

SAMPLE_SECTIONS: dict[str, dict] = {
    "market": {"target_customers": ["طلاب"], "market_size": "كبير", "trends": ["صحة"], "unique_value_proposition": "سعر"},
    "swot": {"strengths": ["قوة"], "weaknesses": ["ضعف"], "opportunities": ["فرصة"], "threats": ["تهديد"]},
    "competition": {"competitors": [{"name": "أ", "description": "د", "our_advantage": "م"}], "positioning": "تموضع"},
    "risks": {"risks": [{"risk": "خطر", "likelihood": "متوسط", "impact": "مرتفع", "mitigation": "تخفيف"}]},
    "roadmap": {"days_30": PHASE, "days_60": PHASE, "days_90": PHASE},
    "financials": {"estimated_investment": "100 ألف", "revenue_streams": ["مبيعات"], "cost_structure": ["إيجار"],
                   "break_even_estimate": "12 شهراً", "pricing_strategy": "تنافسي"},
    "kpis": {"kpis": [{"name": "العملاء", "target": "500", "why": "نمو"}]},
    "summary": {"summary": "فكرة جيدة", "viability_score": 72, "verdict": "قابلة للتنفيذ"},
}

MODEL_TO_KEY = {model: key for key, (model, _t) in SECTIONS.items()}


class FakeLLM:
    def __init__(self, fail_on: str | None = None, chunks: list[str] | None = None):
        self.calls: list[tuple[str, str, str]] = []
        self.fail_on = fail_on
        self.chunks = chunks or ["إجابة ", "تجريبية"]

    async def complete_json(self, system: str, user: str, schema: type[BaseModel]):
        name = schema.__name__
        self.calls.append((name, system, user))
        if name == self.fail_on:
            raise LLMError("boom", "خطأ تجريبي")
        if schema is ClarifyingQuestions:
            return ClarifyingQuestions(questions=["ما هي ميزانيتك؟", "أين الموقع؟", "من فريقك؟"])
        return schema.model_validate(SAMPLE_SECTIONS[MODEL_TO_KEY[schema]])

    async def complete(self, system: str, user: str) -> str:
        self.calls.append(("complete", system, user))
        return "".join(self.chunks)

    async def stream(self, system: str, user: str):
        self.calls.append(("stream", system, user))
        for c in self.chunks:
            yield c
