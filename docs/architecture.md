# HumZehan — Architecture

How HumZehan is built. Product requirements are in [`PRD.md`](PRD.md). Update this file in the same pull request whenever the design changes.

_Last updated: 2026-11-10_

## 1. System overview

```
Browser (Next.js frontend)
    │  HTTP/JSON  (multipart for photos)
    ▼
FastAPI backend  ──►  services  ──►  LangGraph agent  ──►  LLM provider (OpenAI)
                          │
                          └──────►  repositories  ──►  SQLite
```

| Part | Technology | Responsibility |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS | Study page, agent trace, quiz, dashboard |
| Backend | Python 3.12, FastAPI, uv | Versioned REST API, runs the agent, stores data |
| Agent | LangGraph, LangChain OpenAI | Multi-step rewrite → quiz → self-check loop |
| Storage | SQLite | Lessons and quiz progress |
| Quality | Ruff, mypy (strict), pytest, ESLint, GitHub Actions | Checks on every pull request |

## 2. Repository layout

```
humzehan/
├── CLAUDE.md               # rules for Claude Code
├── docs/                   # PRD.md, architecture.md
├── .github/workflows/      # CI
├── backend/
│   ├── pyproject.toml, uv.lock, .env.example
│   ├── src/humzehan/
│   │   ├── main.py         # create_app() factory
│   │   ├── core/           # config.py (Settings), logging.py
│   │   ├── api/v1/         # router.py + one module per resource (health.py, lessons.py, ...)
│   │   ├── schemas/        # Pydantic models: the API contract
│   │   ├── services/       # business logic
│   │   ├── agents/         # LangGraph: state.py, graph.py, nodes/, prompts/
│   │   ├── llm/            # LLM client factory
│   │   └── db/             # SQLite connection + repositories
│   └── tests/
│       ├── unit/           # fast, no network (fake LLM)
│       └── integration/    # API-level tests
└── frontend/
    └── src/
        ├── app/            # routes: page.tsx, dashboard/page.tsx
        ├── features/       # lessons/, dashboard/
        ├── components/ui/  # shared primitives
        ├── lib/            # api client, config
        └── types/          # API types mirroring backend schemas
```

## 3. Backend layers

```
api/v1 (routes)  →  services  →  agents  →  llm
                        └──────→  db (repositories)
```

Rules:
- **Routes** validate input with `schemas/` and call one service method. No business logic.
- **Services** orchestrate: run the agent, save results, build summaries.
- **Agents** never touch the database or HTTP.
- **Repositories** are the only code that writes SQL.
- **Settings** come only from `core/config.py` (`get_settings()`); secrets only from `.env`.

## 4. Configuration

Loaded from environment variables / `backend/.env` by `core/config.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` / `test` / `production` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins (comma-separated) |
| `OPENAI_API_KEY` | — | LLM provider key (secret) |
| `LLM_MODEL` | `gpt-4o-mini` | Model used by all agent nodes |
| `AGENT_MAX_LOOPS` | `2` | Maximum checker → rewrite loops |
| `DATABASE_PATH` | `humzehan.db` | SQLite file location |

## 5. Data models (`schemas/`)

```python
class LearningMode(StrEnum):      # "focus" | "easyread" | "literal"

class GlossaryItem(BaseModel):
    term: str
    meaning: str

class QuizItem(BaseModel):
    question: str
    options: list[str]            # 3 options
    answer_index: int             # 0-based index into options

class Chunk(BaseModel):
    heading: str
    body: str                     # Markdown
    hook: str | None              # Focus mode: "why this matters"
    glossary: list[GlossaryItem]
    quiz: list[QuizItem]          # 3 per chunk

class TraceStep(BaseModel):
    node: str                     # e.g. "checker"
    note: str                     # e.g. "Chunk 2: simplify (sentence over 12 words)"
    ms: int

class Lesson(BaseModel):
    lesson_id: str                # UUID
    student: str
    mode: LearningMode
    urdu: bool
    title: str
    chunks: list[Chunk]
    trace: list[TraceStep]
    created_at: datetime

class ProgressCreate(BaseModel):
    lesson_id: str
    chunk_index: int              # >= 0
    score: int                    # 0–3

class StudentSummary(BaseModel):
    student: str
    lessons: int
    chunks_completed: int
    average_score: float | None

class DashboardSummary(BaseModel):
    students: list[StudentSummary]
```

## 6. The agent (`agents/`)

### 6.1 Graph

```
ingest → router → focus_transform    ┐
                → easyread_transform ┼→ urdu (if urdu) → quiz → checker ─┬→ END
                → literal_transform  ┘                                   │
                         ▲                                               │
                         └──────── non-approved chunks + notes ◄─────────┘
                                   (while loops < AGENT_MAX_LOOPS)
```

### 6.2 State (`agents/state.py`)

```python
CheckerAction = Literal["approve", "simplify", "add_glossary", "fix_fact"]

class ChunkReview(BaseModel):
    chunk_index: int
    action: CheckerAction
    reason: str

class AgentState(TypedDict, total=False):
    source_text: str
    image_b64: str | None          # F4
    mode: LearningMode
    urdu: bool                     # F5
    title: str
    chunks: list[Chunk]
    reviews: list[ChunkReview]
    loops: int
    trace: list[TraceStep]
```

### 6.3 Nodes (`agents/nodes/`)

| Node | Input → output | Notes |
| --- | --- | --- |
| `ingest` | `source_text` / `image_b64` → `source_text` | Photo text extraction added in F4 |
| `router` | `mode` → next node name | Pure function, no LLM call |
| `*_transform` | `source_text` (+ reviews) → `title`, `chunks` | One prompt per mode; on a re-run, only non-approved chunks are rewritten using the checker's notes |
| `urdu` | `chunks` → `chunks` | Runs only when `urdu=True` (F5) |
| `quiz` | `chunks` → `chunks[i].quiz` | Answers only from the chunk |
| `checker` | `source_text`, `chunks`, `mode` → `reviews`, `loops` | Structured output: one `ChunkReview` per chunk |

Every node appends a `TraceStep` and is a function of `(state) -> partial state`.

### 6.4 Checker loop logic

```
after checker:
    if all reviews are "approve"        → END
    elif loops >= AGENT_MAX_LOOPS       → END (keep best version)
    else                                → back to the mode's transform node
```

### 6.5 Prompts (`agents/prompts/`)

One Markdown file per node: `focus.md`, `easyread.md`, `literal.md`, `urdu.md`, `quiz.md`, `checker.md`. Every transform prompt includes: "Use only facts from the SOURCE. Do not add information."

### 6.6 LLM usage (`llm/`)

- One factory creates the chat model from settings (`LLM_MODEL`, low temperature, e.g. 0.2).
- All nodes use **structured outputs** (`with_structured_output(PydanticModel)`), so responses are validated models, not free text.
- Tests inject a **fake LLM** that returns fixed models, so unit tests are fast, free and offline.

## 7. API (`/api/v1`)

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/health` | — | `{status, version}` |
| POST | `/lessons` | multipart: `student`, `mode`, `urdu`, `text` or `image` | `201` `Lesson` |
| GET | `/lessons/{lesson_id}` | — | `Lesson` or `404` |
| POST | `/progress` | JSON `ProgressCreate` | `204` |
| GET | `/dashboard` | — | `DashboardSummary` |

Errors return `{"detail": "<message>"}` with a suitable status code (400 bad input, 404 not found, 502 LLM failure).

## 8. Database (SQLite)

```sql
CREATE TABLE lessons (
    id          TEXT PRIMARY KEY,
    student     TEXT NOT NULL,
    mode        TEXT NOT NULL,
    title       TEXT NOT NULL,
    payload     TEXT NOT NULL,      -- full Lesson as JSON
    created_at  TEXT NOT NULL
);

CREATE TABLE progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id    TEXT NOT NULL REFERENCES lessons(id),
    chunk_index  INTEGER NOT NULL,
    score        INTEGER NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX idx_lessons_student ON lessons(student);
```

Storing the full lesson as JSON keeps v1 simple; the repository layer allows moving to PostgreSQL later without touching services.

## 9. Testing strategy

| Level | What | Tools |
| --- | --- | --- |
| Unit | Each agent node, router and loop logic, schemas | pytest + fake LLM |
| Integration | Each endpoint with a temporary SQLite file | pytest + FastAPI `TestClient` |
| Evals (F8) | Real pages through the real model; quality scores | `evals/run.py` |
| CI | Ruff, mypy, pytest; ESLint, type-check, build | GitHub Actions on every PR |

## 10. Observability, security and privacy

- **Logging:** standard logging via `core/logging.py`; never log students' raw text in production.
- **Tracing (F8):** LangSmith or Langfuse, enabled by environment variables.
- **Limits (F9):** maximum text length and image size; rate limiting per client; API spending cap.
- **Privacy:** no diagnosis or health data is collected; only names, chosen style, lessons and scores.

## 11. Deployment (F9)

| Part | Platform |
| --- | --- |
| Frontend | Vercel (root directory `frontend`) |
| Backend | Railway or Render, from a Dockerfile in `backend/` |
| Database | SQLite on a persistent volume |

## 12. Key decisions

| Decision | Reason |
| --- | --- |
| Monorepo (backend + frontend) | One place for issues, CI and docs; solo developer |
| uv for Python | Fast, one tool, reproducible lockfile |
| LangGraph for the agent | Explicit state, branching and loops for the checker |
| Structured outputs everywhere | Validated data instead of parsing free text |
| SQLite for v1 | Zero setup; repository layer allows a later move to PostgreSQL |
| Browser speech for audio | Free, no extra API key |
