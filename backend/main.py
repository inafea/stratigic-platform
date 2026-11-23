"""FastAPI entry point. Run with: uvicorn backend.main:app --reload"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.llm.client import LLMClient, LLMError
from backend.schemas import SECTIONS, AnalysisRequest, IdeaInput
from backend.services.analyzer import Analyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mustashar")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Mustashar — مستشار", version="0.1.0")


# ---- dependencies --------------------------------------------------------------

def get_analyzer() -> Analyzer:
    settings = get_settings()
    if not settings.llm_api_key:
        raise HTTPException(503, "لم يتم إعداد مفتاح خدمة الذكاء الاصطناعي على الخادم.")
    return Analyzer(LLMClient(settings))


# ---- error handling ---------------------------------------------------------------

@app.exception_handler(LLMError)
async def llm_error_handler(_req: Request, exc: LLMError):
    log.error("LLM error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": exc.user_message})


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---- routes ------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/clarify")
async def clarify(data: IdeaInput, analyzer: Analyzer = Depends(get_analyzer)):
    return {"questions": await analyzer.clarify(data)}


@app.post("/api/analyze")
async def analyze(req: AnalysisRequest, analyzer: Analyzer = Depends(get_analyzer)):
    """Stream the report as server-sent events: `section` per section, then `done` (or `error`)."""

    async def events() -> AsyncIterator[str]:
        report: dict[str, dict] = {}
        try:
            async for key, data in analyzer.analyze(req):
                report[key] = data
                yield sse("section", {"key": key, "title": SECTIONS[key][1], "data": data})
            yield sse("done", {"sections": list(report)})
        except LLMError as e:
            log.error("analysis failed: %s", e)
            yield sse("error", {"message": e.user_message})
        except Exception:
            log.exception("unexpected analysis failure")
            yield sse("error", {"message": "حدث خطأ غير متوقع أثناء التحليل."})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- frontend (mounted last so /api routes win) ---------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
