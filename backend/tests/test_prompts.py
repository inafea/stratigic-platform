from backend import prompts
from backend.schemas import AnalysisRequest, QAPair

REQ = AnalysisRequest(idea="مطعم صحي {مميز} للطلاب", goals="ربح خلال سنة")


def test_system_prompts_load():
    assert "مستشار" in prompts.strategy_system()
    assert "أسئلة" in prompts.clarify_system()


def test_render_keeps_literal_braces():
    assert prompts.render("a {{x}} {y}", x="1") == "a 1 {y}"


def test_idea_message_includes_inputs():
    msg = prompts.idea_message(REQ)
    assert "مطعم صحي {مميز} للطلاب" in msg
    assert "ربح خلال سنة" in msg
    assert "إجابات" not in msg


def test_idea_message_with_answers():
    req = REQ.model_copy(update={"answers": [QAPair(question="أين؟", answer="الرياض")]})
    msg = prompts.idea_message(req)
    assert "أين؟" in msg and "الرياض" in msg


def test_section_message():
    msg = prompts.section_message(REQ, "swot", previous={"market": {"market_size": "كبير"}})
    assert "تحليل SWOT" in msg
    assert "كبير" in msg
    assert "{{" not in msg
