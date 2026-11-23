"""Strategy analysis pipeline: clarify → section-by-section analysis."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from backend import prompts
from backend.llm.client import LLMClient
from backend.schemas import SECTIONS, AnalysisRequest, ClarifyingQuestions, IdeaInput

log = logging.getLogger(__name__)


class Analyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def clarify(self, data: IdeaInput) -> list[str]:
        """Return 3-5 clarifying questions for the idea."""
        result = await self.llm.complete_json(prompts.clarify_system(), prompts.idea_message(data), ClarifyingQuestions)
        return [q.strip() for q in result.questions if q.strip()][:5]

    async def generate_section(self, req: AnalysisRequest, key: str, context: dict[str, dict]) -> dict:
        model, _title = SECTIONS[key]
        result = await self.llm.complete_json(
            prompts.strategy_system(), prompts.section_message(req, key, context or None), model
        )
        return result.model_dump()

    async def analyze(self, req: AnalysisRequest) -> AsyncIterator[tuple[str, dict]]:
        """Generate every section in order, yielding (key, data) as each completes.

        Each section sees the previously generated sections for consistency.
        """
        done: dict[str, dict] = {}
        for key in SECTIONS:
            log.info("generating section %s", key)
            data = await self.generate_section(req, key, done)
            done[key] = data
            yield key, data
