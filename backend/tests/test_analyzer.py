import pytest

from backend.llm.client import LLMError
from backend.schemas import SECTIONS, AnalysisRequest, IdeaInput, StrategyReport
from backend.services.analyzer import Analyzer
from backend.llm.fake import FakeLLM

REQ = AnalysisRequest(idea="مطعم صحي للطلاب في الرياض", goals="ربح خلال سنة")


async def test_clarify_returns_questions():
    llm = FakeLLM()
    qs = await Analyzer(llm).clarify(IdeaInput(idea=REQ.idea, goals=REQ.goals))
    assert 3 <= len(qs) <= 5
    assert "مطعم صحي" in llm.calls[0][2]


async def test_analyze_yields_all_sections_in_order():
    llm = FakeLLM()
    got = [item async for item in Analyzer(llm).analyze(REQ)]
    assert [k for k, _ in got] == list(SECTIONS)
    StrategyReport.model_validate(dict(got))


async def test_later_sections_see_earlier_ones():
    llm = FakeLLM()
    _ = [item async for item in Analyzer(llm).analyze(REQ)]
    first_user, last_user = llm.calls[0][2], llm.calls[-1][2]
    assert "الأقسام التي تم إعدادها سابقاً" not in first_user
    assert "الأقسام التي تم إعدادها سابقاً" in last_user


async def test_analyze_propagates_errors_after_partial_output():
    llm = FakeLLM(fail_on="Competition")
    got = []
    with pytest.raises(LLMError):
        async for item in Analyzer(llm).analyze(REQ):
            got.append(item)
    assert [k for k, _ in got] == ["market", "swot"]
