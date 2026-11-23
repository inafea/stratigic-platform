"""FastAPI entry point. Run with: uvicorn backend.main:app --reload"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from sqlmodel import Session, select

from backend import auth, db, google_auth
from backend.i18n import request_lang, tr
from backend.config import get_settings
from backend.llm.client import LLMClient, LLMError
from backend.ratelimit import limiter, llm_limit
from backend.schemas import (
    INDUSTRIES,
    SECTIONS,
    STRATEGIES,
    AnalysisRequest,
    ChatRequest,
    IdeaInput,
    RegenerateRequest,
)
from backend.services.analyzer import Analyzer

logging.basicConfig(level=get_settings().log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mustashar")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"



@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Mustashar — مستشار", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.middleware("http")(auth.csrf_middleware)
app.include_router(auth.router)
app.include_router(google_auth.router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, _exc: RateLimitExceeded):
    msg = tr("عدد كبير من الطلبات. يرجى الانتظار قليلاً ثم المحاولة.", request_lang(request))
    return JSONResponse(status_code=429, content={"detail": msg})


@app.exception_handler(HTTPException)
async def translated_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, str):
        exc = HTTPException(exc.status_code, tr(exc.detail, request_lang(request)), exc.headers)
    return await http_exception_handler(request, exc)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - start) * 1000)
    return response


# ---- dependencies --------------------------------------------------------------

def get_analyzer() -> Analyzer:
    settings = get_settings()
    if settings.llm_provider == "fake":
        from backend.llm.fake import FakeLLM
        return Analyzer(FakeLLM())
    if not settings.llm_api_key:
        raise HTTPException(503, "لم يتم إعداد مفتاح خدمة الذكاء الاصطناعي على الخادم.")
    if settings.llm_provider == "anthropic":
        from backend.llm.anthropic_client import AnthropicLLMClient
        return Analyzer(AnthropicLLMClient(settings))
    return Analyzer(LLMClient(settings))


# ---- error handling ---------------------------------------------------------------

@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    log.error("LLM error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": tr(exc.user_message, request_lang(request))})


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---- routes ------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/templates")
async def templates():
    """Industry and strategy-type templates the form can offer."""
    return {
        "industries": [{"key": k, "label": v} for k, v in INDUSTRIES.items()],
        "strategies": [{"key": k, "label": v} for k, v in STRATEGIES.items()],
    }


def _request_of(r: db.Report) -> AnalysisRequest:
    return AnalysisRequest.model_validate(
        {"idea": r.idea, "goals": r.goals, "industry": r.industry, "strategy": r.strategy,
         "language": r.language, "answers": r.answers}
    )


@app.post("/api/clarify")
@llm_limit
async def clarify(request: Request, data: IdeaInput, analyzer: Analyzer = Depends(get_analyzer)):
    return {"questions": await analyzer.clarify(data)}


@app.post("/api/analyze")
@llm_limit
async def analyze(request: Request, req: AnalysisRequest, analyzer: Analyzer = Depends(get_analyzer)):
    """Stream the report as server-sent events: `report` (id), `section` per section, then `done` or `error`.

    The report is saved as it is generated, so a partial report survives an error.
    """
    with Session(db.get_engine()) as s:
        report = db.Report(idea=req.idea, goals=req.goals, industry=req.industry, strategy=req.strategy,
                           language=req.language, answers=[a.model_dump() for a in req.answers])
        s.add(report)
        s.commit()
        report_id = report.id
    lang = request_lang(request)

    async def events() -> AsyncIterator[str]:
        yield sse("report", {"id": report_id})
        try:
            async for key, data in analyzer.analyze(req):
                db.save_section(report_id, key, data)
                yield sse("section", {"key": key, "title": SECTIONS[key][1], "data": data})
            db.set_status(report_id, "done")
            yield sse("done", {"id": report_id})
        except LLMError as e:
            log.error("analysis %s failed: %s", report_id, e)
            db.set_status(report_id, "error")
            yield sse("error", {"message": tr(e.user_message, lang)})
        except Exception:
            log.exception("unexpected failure in analysis %s", report_id)
            db.set_status(report_id, "error")
            yield sse("error", {"message": tr("حدث خطأ غير متوقع أثناء التحليل.", lang)})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- saved reports -------------------------------------------------------------------

def _get_report(session: Session, report_id: int) -> db.Report:
    report = session.get(db.Report, report_id)
    if report is None:
        raise HTTPException(404, "التقرير غير موجود.")
    return report


@app.get("/api/reports")
async def list_reports(session: Session = Depends(db.get_session)):
    rows = session.exec(select(db.Report).order_by(db.Report.id.desc()).limit(100))
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "title": r.idea[:80],
            "status": r.status,
            "score": (r.sections.get("summary") or {}).get("viability_score"),
        }
        for r in rows
    ]


@app.get("/api/reports/{report_id}")
async def get_report(report_id: int, session: Session = Depends(db.get_session)):
    r = _get_report(session, report_id)
    return {
        "id": r.id,
        "created_at": r.created_at.isoformat(),
        "idea": r.idea,
        "goals": r.goals,
        "industry": r.industry,
        "strategy": r.strategy,
        "language": r.language,
        "answers": r.answers,
        "status": r.status,
        "sections": [
            {"key": k, "title": SECTIONS[k][1], "data": r.sections[k]} for k in SECTIONS if k in r.sections
        ],
        "messages": [{"role": m.role, "content": m.content} for m in db.list_messages(session, r.id)],
    }


@app.delete("/api/reports/{report_id}", status_code=204)
async def delete_report(report_id: int, session: Session = Depends(db.get_session)):
    r = _get_report(session, report_id)
    for m in db.list_messages(session, r.id):
        session.delete(m)
    session.delete(r)
    session.commit()


@app.post("/api/reports/{report_id}/sections/{key}/regenerate")
@llm_limit
async def regenerate_section(
    request: Request,
    report_id: int,
    key: str,
    body: RegenerateRequest,
    analyzer: Analyzer = Depends(get_analyzer),
    session: Session = Depends(db.get_session),
):
    if key not in SECTIONS:
        raise HTTPException(404, "القسم غير موجود.")
    r = _get_report(session, report_id)
    req = _request_of(r)
    data = await analyzer.regenerate_section(req, key, r.sections, body.instructions)
    db.save_section(report_id, key, data)
    return {"key": key, "title": SECTIONS[key][1], "data": data}


@app.post("/api/reports/{report_id}/chat")
@llm_limit
async def chat(
    request: Request,
    report_id: int,
    body: ChatRequest,
    analyzer: Analyzer = Depends(get_analyzer),
    session: Session = Depends(db.get_session),
):
    """Stream a follow-up answer as SSE `delta` events, then `done`. Both messages are saved."""
    r = _get_report(session, report_id)
    req = _request_of(r)
    sections = dict(r.sections)
    history = [(m.role, m.content) for m in db.list_messages(session, report_id)][-10:]
    session.add(db.Message(report_id=report_id, role="user", content=body.message))
    session.commit()
    lang = request_lang(request)

    async def events() -> AsyncIterator[str]:
        parts: list[str] = []
        try:
            async for chunk in analyzer.chat(req, sections, history, body.message):
                parts.append(chunk)
                yield sse("delta", {"text": chunk})
        except LLMError as e:
            log.error("chat on report %s failed: %s", report_id, e)
            yield sse("error", {"message": tr(e.user_message, lang)})
            return
        except Exception:
            log.exception("unexpected chat failure on report %s", report_id)
            yield sse("error", {"message": tr("حدث خطأ غير متوقع.", lang)})
            return
        with Session(db.get_engine()) as s:
            s.add(db.Message(report_id=report_id, role="assistant", content="".join(parts)))
            s.commit()
        yield sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- frontend (mounted last so /api routes win) ---------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
