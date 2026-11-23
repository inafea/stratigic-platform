import pytest
from pydantic import ValidationError

from backend.schemas import (
    SECTIONS,
    AnalysisRequest,
    ClarifyingQuestions,
    ExecutiveSummary,
    Risk,
    StrategyReport,
)

PHASE = {"goals": ["g"], "actions": ["a"]}

SAMPLE = {
    "market": {"target_customers": ["طلاب"], "market_size": "كبير", "trends": ["صحة"], "unique_value_proposition": "سعر"},
    "swot": {"strengths": ["s"], "weaknesses": ["w"], "opportunities": ["o"], "threats": ["t"]},
    "competition": {"competitors": [{"name": "A", "description": "d", "our_advantage": "x"}], "positioning": "p"},
    "risks": {"risks": [{"risk": "r", "likelihood": "متوسط", "impact": "مرتفع", "mitigation": "m"}]},
    "roadmap": {"days_30": PHASE, "days_60": PHASE, "days_90": PHASE},
    "financials": {"estimated_investment": "1", "revenue_streams": ["r"], "cost_structure": ["c"],
                   "break_even_estimate": "12 شهر", "pricing_strategy": "p"},
    "kpis": {"kpis": [{"name": "n", "target": "t", "why": "w"}]},
    "summary": {"summary": "s", "viability_score": 72, "verdict": "v"},
}


def test_full_report_parses():
    r = StrategyReport.model_validate(SAMPLE)
    assert r.summary.viability_score == 72


def test_sections_cover_report():
    assert set(SECTIONS) == set(StrategyReport.model_fields)
    assert list(SECTIONS)[-1] == "summary"
    for key, (model, _title) in SECTIONS.items():
        assert StrategyReport.model_fields[key].annotation is model


def test_score_bounds():
    with pytest.raises(ValidationError):
        ExecutiveSummary(summary="s", viability_score=150, verdict="v")


def test_risk_level_enum():
    with pytest.raises(ValidationError):
        Risk(risk="r", likelihood="huge", impact="مرتفع", mitigation="m")


def test_request_validation():
    with pytest.raises(ValidationError):
        AnalysisRequest(idea="short", goals="goals ok")
    ok = AnalysisRequest(idea="مطعم صحي للطلاب", goals="ربح خلال سنة")
    assert ok.answers == []


def test_questions_limit():
    with pytest.raises(ValidationError):
        ClarifyingQuestions(questions=["q"] * 6)
