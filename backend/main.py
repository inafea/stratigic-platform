"""FastAPI entry point. Run with: uvicorn backend.main:app --reload"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, select

from backend import db
from backend.config import get_settings
from backend.llm.client import LLMClient, LLMError
from backend.schemas import SECTIONS, AnalysisRequest, IdeaInput
from backend.services.analyzer import Analyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mustashar")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"



@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Mustashar — مستشار", version="0.1.0", lifespan=lifespan)


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
    """Stream the report as server-sent events: `report` (id), `section` per section, then `done` or `error`.

    The report is saved as it is generated, so a partial report survives an error.
    """
    with Session(db.get_engine()) as s:
        report = db.Report(idea=req.idea, goals=req.goals, answers=[a.model_dump() for a in req.answers])
        s.add(report)
        s.commit()
        report_id = report.id

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
            yield sse("error", {"message": e.user_message})
        except Exception:
            log.exception("unexpected failure in analysis %s", report_id)
            db.set_status(report_id, "error")
            yield sse("error", {"message": "حدث خطأ غير متوقع أثناء التحليل."})

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


# ---- frontend (mounted last so /api routes win) ---------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
