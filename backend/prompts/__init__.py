"""Prompt templates (Arabic) and helpers to render them.

Templates use `{{name}}` placeholders so literal braces in user text are safe.
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from backend.schemas import SECTIONS, AnalysisRequest, IdeaInput

PROMPTS_DIR = Path(__file__).parent


@cache
def load(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def render(template: str, **values: str) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def idea_message(data: IdeaInput) -> str:
    """User message describing the idea, goals and any clarifying answers."""
    parts = [f"فكرة العمل:\n{data.idea}", f"الأهداف:\n{data.goals}"]
    answers = getattr(data, "answers", None) or []
    if answers:
        qa = "\n".join(f"- س: {a.question}\n  ج: {a.answer}" for a in answers)
        parts.append(f"إجابات الأسئلة التوضيحية:\n{qa}")
    return "\n\n".join(parts)


def section_message(
    req: AnalysisRequest, key: str, previous: dict[str, dict] | None = None, instructions: str | None = None
) -> str:
    _model, title = SECTIONS[key]
    prev_text = ""
    if previous:
        prev_text = "\nالأقسام التي تم إعدادها سابقاً (للاتساق):\n" + json.dumps(previous, ensure_ascii=False)
    msg = idea_message(req) + "\n\n" + render(load("section_ar"), title=title, previous=prev_text).strip()
    if instructions:
        msg += f"\n\nتعليمات إضافية من المستخدم لهذا القسم:\n{instructions}"
    return msg


def chat_system(report_sections: dict[str, dict]) -> str:
    report_json = json.dumps(report_sections, ensure_ascii=False)
    return strategy_system() + "\n\n" + render(load("chat_ar"), report=report_json)


def chat_message(req: IdeaInput, history: list[tuple[str, str]], question: str) -> str:
    parts = [idea_message(req)]
    if history:
        names = {"user": "المستخدم", "assistant": "مستشار"}
        parts.append("المحادثة السابقة:\n" + "\n".join(f"{names.get(r, r)}: {c}" for r, c in history))
    parts.append(f"السؤال الجديد:\n{question}")
    return "\n\n".join(parts)


def strategy_system() -> str:
    return load("strategy_ar")


def clarify_system() -> str:
    return load("clarify_ar")
