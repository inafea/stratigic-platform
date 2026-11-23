"""Pydantic models for requests and the structured strategy report.

The report is produced section by section; `SECTIONS` maps each section key to its model and Arabic title.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- requests --------------------------------------------------------------

INDUSTRIES: dict[str, str] = {
    "restaurant": "المطاعم والأغذية",
    "ecommerce": "التجارة الإلكترونية",
    "saas": "البرمجيات والتطبيقات (SaaS)",
    "retail": "تجارة التجزئة",
    "real_estate": "العقارات",
    "education": "التعليم والتدريب",
    "healthcare": "الصحة واللياقة",
    "services": "الخدمات المهنية والاستشارية",
}

STRATEGIES: dict[str, str] = {
    "new_business": "إطلاق مشروع جديد",
    "expansion": "توسع مشروع قائم",
    "market_entry": "دخول سوق جديد",
    "product_launch": "إطلاق منتج جديد",
    "turnaround": "إنقاذ مشروع متعثر",
    "funding": "التحضير للتمويل",
}

Industry = Literal["auto", "restaurant", "ecommerce", "saas", "retail", "real_estate", "education", "healthcare",
                   "services"]
Language = Literal["ar", "en"]
StrategyType = Literal["auto", "new_business", "expansion", "market_entry", "product_launch", "turnaround", "funding"]


class IdeaInput(BaseModel):
    idea: str = Field(min_length=10, max_length=4000)
    goals: str = Field(min_length=5, max_length=2000)
    industry: Industry = "auto"
    strategy: StrategyType = "auto"
    language: Language = "ar"


class ClarifyingQuestions(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=5)


class QAPair(BaseModel):
    question: str = Field(max_length=500)
    answer: str = Field(max_length=1000)


class AnalysisRequest(IdeaInput):
    answers: list[QAPair] = Field(default_factory=list, max_length=5)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class RegenerateRequest(BaseModel):
    instructions: str | None = Field(default=None, max_length=1000)


# ---- report sections ---------------------------------------------------------

Level = Literal["منخفض", "متوسط", "مرتفع"]


class ExecutiveSummary(BaseModel):
    summary: str
    viability_score: int = Field(ge=0, le=100, description="درجة الجدوى من 0 إلى 100")
    verdict: str = Field(description="حكم مختصر في جملة واحدة")


class MarketAnalysis(BaseModel):
    target_customers: list[str]
    market_size: str
    trends: list[str]
    unique_value_proposition: str


class SWOT(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]


class Competitor(BaseModel):
    name: str
    description: str
    our_advantage: str


class Competition(BaseModel):
    competitors: list[Competitor]
    positioning: str


class Risk(BaseModel):
    risk: str
    likelihood: Level
    impact: Level
    mitigation: str


class Risks(BaseModel):
    risks: list[Risk]


class RoadmapPhase(BaseModel):
    goals: list[str]
    actions: list[str]


class Roadmap(BaseModel):
    days_30: RoadmapPhase
    days_60: RoadmapPhase
    days_90: RoadmapPhase


class Financials(BaseModel):
    estimated_investment: str
    revenue_streams: list[str]
    cost_structure: list[str]
    break_even_estimate: str
    pricing_strategy: str


class KPI(BaseModel):
    name: str
    target: str
    why: str


class KPIs(BaseModel):
    kpis: list[KPI]


SECTIONS: dict[str, tuple[type[BaseModel], str]] = {
    "market": (MarketAnalysis, "تحليل السوق"),
    "swot": (SWOT, "تحليل SWOT"),
    "competition": (Competition, "المنافسة"),
    "risks": (Risks, "المخاطر"),
    "roadmap": (Roadmap, "خطة 30/60/90 يوماً"),
    "financials": (Financials, "الاعتبارات المالية"),
    "kpis": (KPIs, "مؤشرات الأداء"),
    "summary": (ExecutiveSummary, "الملخص التنفيذي"),
}
"""Generation order: summary last so it can draw on the other sections."""


class StrategyReport(BaseModel):
    market: MarketAnalysis
    swot: SWOT
    competition: Competition
    risks: Risks
    roadmap: Roadmap
    financials: Financials
    kpis: KPIs
    summary: ExecutiveSummary
