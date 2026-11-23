# Rebuild Plan & Task Tracker

Status legend: [ ] todo · [x] done. Work happens on `enhancement`, one commit per task.


## Context
Right now the app takes a business idea and goals, sends one large Arabic prompt to GPT-4.1-mini, and shows a single block of Markdown. In practice it doesn't work. The Flask template never renders `result` or `error`. The browser-only copy sends an empty API key. The AI output goes into `innerHTML` without sanitizing, which is an XSS hole. The prompt is copied in two places. The output is unstructured text that can't be saved, compared or exported.

Goal: keep the idea (an Arabic-first AI strategy consultant) and rebuild it so it works, is secure, returns structured results, and grows from a one-shot answer into an interactive strategy workspace.

## Better implementation (core design)
| Concern | Today | New |
|---|---|---|
| Architecture | 2 duplicate apps (browser + Flask) | One backend in **FastAPI** plus one frontend; the API key stays on the server only |
| AI call | One giant prompt, free-text reply | **Structured JSON output** from a Pydantic schema; system prompt kept separately; the prompt lives in one file under `prompts/` |
| Analysis | One pass | **Multi-step pipeline**: (1) clarifying questions → (2) section-by-section analysis (SWOT, market, competitors, finance, roadmap) → (3) executive summary |
| UX | Spinner then a text dump | **Streaming** (SSE) so sections appear as they're generated; RTL cards per section |
| Rendering | Hand-written regex Markdown into innerHTML | Structured JSON rendered into components; any Markdown passed through `marked` + `DOMPurify` |
| Provider | Hard-coded GitHub Models | A small `LLMClient` interface (Claude / OpenAI-compatible / GitHub Models), chosen through `.env` |
| Persistence | None | SQLite via SQLModel: saved analyses and their history |
| Ops | `debug=True`, no timeout | Timeouts, retries, rate limiting, logging, pinned dependencies, Dockerfile, tests |

## Ideas to enhance it (by phase)
**Phase A (MVP+):** SWOT, PESTEL, Business Model Canvas and Lean Canvas generated as visual cards; risk matrix; KPI suggestions; a 30/60/90-day roadmap.
**Phase B (Interactive):** follow-up chat about the analysis ("اشرح أكثر", "ماذا لو خفضت السعر؟"); regenerate a single section; what-if scenarios for the financial model.
**Phase C (Data & output):** export to PDF/Word/PowerPoint (Arabic RTL); simple financial projections with charts (revenue, break-even); comparison of two ideas side by side; a score out of 100 for viability.
**Phase D (Market grounding):** optional web search for real competitors and market sizes, with sources cited; local context for Arabic/Gulf/Egypt markets (regulations, payment methods, Vision 2030 alignment).
**Phase E (Platform):** user accounts, a project workspace, sharing links, industry templates (restaurant, e-commerce, SaaS…), bilingual Arabic/English toggle, and token-cost tracking.

## Target structure
```
backend/
  main.py              # FastAPI app, routes
  config.py            # pydantic-settings (.env)
  llm/client.py        # LLMClient interface + providers
  prompts/strategy_ar.md
  schemas.py           # Pydantic: StrategyReport, SWOT, Roadmap, Financials...
  services/analyzer.py # pipeline: clarify → sections → summary
  db.py, models.py     # SQLModel / SQLite
  tests/
frontend/
  index.html, app.js, styles.css   # RTL, section cards, SSE consumer
.env.example  requirements.txt  Dockerfile  README.md (ar + en)
```

## Execution steps
1. **Clean up:** delete root `index.html`, `app.js`, `app.py` and `templates/` (the old code stays in git history). Add `.gitignore` and `.env.example`, and pin `requirements.txt` (fastapi, uvicorn, pydantic-settings, httpx, sqlmodel, slowapi, pytest).
2. **Config + LLM client:** `config.py` reads `LLM_PROVIDER`, `LLM_API_KEY` and `LLM_MODEL`. `llm/client.py` exposes `complete_json(system, user, schema)` and `stream(...)`, with a timeout and retries.
3. **Schemas + prompt:** define a Pydantic `StrategyReport` (summary, market, swot, competitors, risks[], roadmap{30,60,90}, financials, kpis[], score). Move the Arabic prompt from [app.py](app.py) into `prompts/strategy_ar.md` as a system prompt.
4. **Analyzer service:** `clarify(idea, goals)` returns 3–5 questions; `analyze(...)` generates the report one section at a time and yields each section as it completes.
5. **API routes:** `POST /api/clarify`, `POST /api/analyze` (SSE stream), `GET/POST /api/reports`, `POST /api/reports/{id}/chat`. Add input-length validation and rate limiting.
6. **Persistence:** SQLite tables for `Report` and `Message`, and save each completed report.
7. **Frontend:** RTL layout (Tajawal/Cairo font) with a step form (idea → goals → clarifying answers), section cards that fill in live, a SWOT grid, a roadmap timeline, a report history sidebar, and DOMPurify for any Markdown.
8. **Follow-up chat + regenerate section** (Phase B).
9. **Export:** PDF export via WeasyPrint (supports RTL) at `GET /api/reports/{id}/pdf`.
10. **Quality:** pytest with a mocked LLM client (schema validation, routes, SSE), a Dockerfile, and a bilingual README.
11. **Later:** Phases C–E as separate iterations.

## Task list (one task = one commit on `enhancement`)
| # | Task | Done when |
|---|---|---|
| [x] T1 | Project skeleton: `backend/`, `frontend/`, `.gitignore`, `.env.example`, pinned `requirements.txt`; remove old files | `pip install -r requirements.txt` works |
| [x] T2 | `config.py` (pydantic-settings) | Settings load from `.env` |
| [x] T3 | `llm/client.py`: GitHub Models provider, timeout, retries, `complete_json` | Unit test with mocked HTTP passes |
| [x] T4 | Streaming support in the client (`stream`) | Mocked stream test passes |
| [x] T5 | `schemas.py`: StrategyReport + section models | Schema tests pass |
| [x] T6 | `prompts/strategy_ar.md` (system prompt) + prompt loader | Prompt renders with idea/goals |
| [x] T7 | `services/analyzer.py`: `clarify()` | Returns 3–5 questions (mocked) |
| [x] T8 | `services/analyzer.py`: `analyze()` section by section, yielding each section | Yields all sections (mocked) |
| [x] T9 | FastAPI `main.py`: `/api/clarify`, `/api/analyze` (SSE), input validation, error handling | Requests to both endpoints succeed |
| [ ] T10 | Frontend base: RTL layout, step form (idea → goals → questions) | Form submits to the API |
| [ ] T11 | Frontend: SSE consumer + section cards, SWOT grid, roadmap timeline, DOMPurify | Live analysis shows in the browser |
| [x] T12 | SQLite persistence (`Report`, `Message`) + `GET/POST /api/reports` | Reports survive a restart |
| [ ] T13 | Frontend history sidebar | Old reports reopen |
| [x] T14 | Rate limiting + logging | 429 after the limit; logs written |
| [ ] T15 | Follow-up chat `/api/reports/{id}/chat` + UI | Chat answers in context |
| [ ] T16 | Regenerate a single section | One card refreshes |
| [ ] T17 | PDF export (WeasyPrint, RTL) | PDF opens with correct Arabic |
| [ ] T18 | Dockerfile + bilingual README | `docker run` serves the app |
| [ ] T19 | Merge `enhancement` → `develop` (PR), then to `main` | Merged |
| Later | Phases C–E as their own task lists | — |

## Verification
- `pytest backend/tests` passes, with the LLM mocked.
- `uvicorn backend.main:app --reload`, then open `http://localhost:8000`: submit a sample Arabic idea and confirm clarifying questions appear, sections stream into cards, and the report is saved and shows in history.
- XSS check: an idea containing `<img src=x onerror=alert(1)>` renders as text.
- With a missing or invalid key, the app shows a clear Arabic error message, with no hang and no stack trace.
- The PDF export opens with correct RTL Arabic text.
