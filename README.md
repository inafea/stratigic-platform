# مستشار — Mustashar

**محلل استراتيجية الأعمال بالذكاء الاصطناعي** · An Arabic-first AI business-strategy advisor.

---

## بالعربية

اكتب فكرتك التجارية وأهدافك، وأجب عن بضعة أسئلة توضيحية، ليُعدّ لك "مستشار" تقريراً استراتيجياً منظماً يظهر قسماً تلو الآخر:

- **الملخص التنفيذي** مع درجة جدوى من 100
- **تحليل السوق** و**تحليل SWOT** و**المنافسة**
- **مصفوفة المخاطر** (الاحتمال / الأثر / التخفيف)
- **خطة 30/60/90 يوماً**، و**الاعتبارات المالية**، و**مؤشرات الأداء**

بعد ذلك يمكنك **محاورة المستشار** حول التقرير ("ماذا لو...؟")، و**إعادة توليد أي قسم** بتعليمات إضافية، و**تصدير التقرير PDF**، والرجوع إلى **التقارير السابقة** في أي وقت.

### التشغيل السريع

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # ثم ضع مفتاح Claude (أو رمز GitHub) في LLM_API_KEY
uvicorn backend.main:app --reload
```

افتح <http://localhost:8000>.

> للتجربة بدون مفتاح: ضع `LLM_PROVIDER=fake` في `.env` لتحصل على بيانات تجريبية.

---

## English

### Features
- Step flow: idea & goals → AI clarifying questions → analysis
- Structured report (validated JSON) streamed section by section over SSE
- Follow-up chat about the report, single-section regeneration with instructions
- Saved reports (SQLite locally, PostgreSQL/Neon in staging) with a history sidebar; print-to-PDF with an RTL print stylesheet
- Per-IP rate limiting, request logging, retries with backoff, timeouts, Arabic error messages
- XSS-safe rendering (text nodes only; chat Markdown sanitized with DOMPurify)

### Configuration (`.env`)
| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `github` | `anthropic` (Claude, official SDK), `github` (any OpenAI-compatible API) or `fake` (offline sample data) |
| `LLM_API_KEY` | – | Anthropic API key (`sk-ant-…`), GitHub token with *Models* access, or your provider's key |
| `LLM_BASE_URL` | `https://models.github.ai/inference` | Any OpenAI-compatible `/chat/completions` base URL |
| `LLM_MODEL` | `openai/gpt-4.1-mini` | For Claude: `claude-opus-5-5`, `claude-sonnet-5-5` or `claude-haiku-5-5` |
| `LLM_TIMEOUT_SECONDS` | `60` | |
| `DATABASE_URL` | `sqlite:///./mustashar.db` | SQLite, or a PostgreSQL URL such as Neon's (`postgresql://...?sslmode=require`) |
| `RATE_LIMIT` | `10/minute` | Applies to endpoints that call the LLM |

### Run with Docker
```bash
docker build -t mustashar .
docker run -p 8000:8000 --env-file .env -v mustashar-data:/data mustashar
```

### Tests
```bash
pytest
```
All tests use a fake LLM; no network or API key needed.

### API
| Method | Path | Description |
|---|---|---|
| POST | `/api/clarify` | `{idea, goals}` → `{questions[]}` |
| POST | `/api/analyze` | `{idea, goals, answers[]}` → SSE: `report`, `section`×8, `done` / `error` |
| GET | `/api/reports` | List saved reports |
| GET/DELETE | `/api/reports/{id}` | Full report with sections and chat messages / delete |
| POST | `/api/reports/{id}/chat` | `{message}` → SSE: `delta`…, `done` |
| POST | `/api/reports/{id}/sections/{key}/regenerate` | `{instructions?}` → new section |

### Project layout
```
backend/
  main.py            FastAPI app & routes
  config.py          settings (.env)
  db.py              database models (users, reports, billing) for SQLite or PostgreSQL
  schemas.py         request & report models
  llm/client.py      OpenAI-compatible client (JSON output, streaming, retries)
  llm/anthropic_client.py  Claude client (structured outputs, streaming, refusal fallbacks)
  llm/fake.py        offline fake LLM
  prompts/           Arabic prompt templates
  services/analyzer.py  clarify → section-by-section analysis, chat, regenerate
  tests/
frontend/            index.html, app.js, styles.css (RTL, no build step)
docs/PLAN.md         roadmap & task tracker
```

## Moving data from SQLite to PostgreSQL

```bash
python -m backend.tools.copy_sqlite_to_postgres --source sqlite:///./mustashar.db --target "postgresql://..."
```

The target must be empty. The script creates the tables, copies every table in order and moves the id counters forward.
