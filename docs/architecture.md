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
| `AGENT_MAX_LOOPS` | `2` | Maximum rewrite rounds sent back by the checker |
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
CheckerAction = Literal["approve", "simplify", "add_glossary", "fix_fact", "missing_fact"]

class ChunkReview(BaseModel):
    chunk_index: int
    action: CheckerAction
    reason: str
    quote: str | None              # evidence: see 6.4 (null for approve/simplify/add_glossary)

class AgentState(TypedDict, total=False):
    source_text: str
    image_b64: str | None          # F4
    mode: LearningMode
    urdu: bool                     # F5
    title: str
    chunks: list[Chunk]
    reviews: list[ChunkReview]
    loops: int                     # rewrite rounds done
    trace: list[TraceStep]
```

The LLM's structured-output models live in the same file: `ChunkDraft` (one chunk without quiz),
`TransformOutput` (title + chunks), `QuizSet` (exactly 3 questions), `CheckerOutput` (`reviews`
plus `suspect_judgments: list[SuspectJudgment]`, where `SuspectJudgment` is
`{suspect_id, supported, reason}`; see 6.4).

### 6.3 Nodes (`agents/nodes/`)

| Node | Input → output | Notes |
| --- | --- | --- |
| `ingest` | `source_text` / `image_b64` → `source_text` | Photo text extraction added in F4 |
| `router` | `mode` → next node name | No LLM call. The node records the decision in the trace; the pure function `route_by_mode(state)` drives the conditional edges |
| `*_transform` | `source_text` (+ reviews) → `title`, `chunks`, `loops` | One prompt per mode (one factory builds all three nodes); on a re-run, only non-approved chunks are rewritten using the checker's notes, their quiz is cleared, and `loops` += 1 |
| `urdu` | `chunks` → `chunks` | Runs only when `urdu=True` (F5) |
| `quiz` | `chunks` → `chunks[i].quiz` | Answers only from the chunk; only chunks with an empty quiz (new or rewritten) get questions |
| `checker` | `source_text`, `chunks`, `mode` → `reviews` | Grounding pre-check first (6.4), then one call over the whole lesson with the suspect sentences. Structured output with quoted evidence and one judgment per suspect; flags are verified in code (6.4) and normalised to exactly one `ChunkReview` per chunk (missing → approve). The trace note lists kept flags, "suspects: N (x unsupported, y supported)" and "dropped N unverified flags" |

Every node appends a `TraceStep` and is a function of `(state) -> partial state`.

### 6.4 Checker loop logic

```
after checker:
    if all reviews are "approve"        → END
    elif loops >= AGENT_MAX_LOOPS       → END (keep latest version)
    else                                → back to the mode's transform node
```

Before routing, the checker's flags are verified by the pure function
`verify_reviews()` in `agents/verification.py`; a flag whose evidence does not hold up is dropped:

| Action | Meaning | `quote` | Kept only if |
| --- | --- | --- | --- |
| `fix_fact` | The chunk states something not in the SOURCE, or changes a fact | Exact sentence from the chunk | The quote is really in that chunk (case, whitespace, Markdown and curly quotes ignored) |
| `missing_fact` | An important SOURCE fact appears in no chunk at all | Exact SOURCE sentence | The quote is in the SOURCE, at most half of its key words (stopwords ignored, words compared by their first 5 letters) appear anywhere in the lesson, and it is the first flag for that sentence |
| `simplify`, `add_glossary` | Style rule broken / glossary needed | null | The reason is not empty |

**Grounding pre-check** (deterministic, `find_suspect_sentences()` in `agents/verification.py`),
run before the checker's LLM call:

1. Split each chunk's hook and body into sentences (bold-only sub-heading lines such as
   `**What it is**`, Markdown headings and list bullets are skipped). Glossary text is excluded.
2. For each sentence, take its content words (lowercase, stopwords removed, simple suffix
   stripping: plurals, `-ed`, `-ing`, `-ation`, `-en`, ...) and compute the share found in
   the SOURCE.
3. Sentences with a share below `GROUNDING_THRESHOLD` (0.6) are *suspect*. On the sample,
   invented claims scored 0.50–0.57 and paraphrases 0.67 or more; a false suspect only costs
   one checker judgment, not a rewrite.

The suspects are listed in the checker's user message with ids; the checker must return one
`SuspectJudgment` per id. `apply_suspect_judgments()` turns every suspect judged unsupported
into a `fix_fact` on its chunk, with that sentence as the quote (it replaces a lower-priority
flag, or is merged into an existing `fix_fact`). Supported and unjudged suspects change nothing.

Rewrites receive the action, reason and quote, and must fix only the quoted problem without adding
any sentence that the SOURCE does not support.

`loops` counts rewrite rounds. With the default of 2:
check → rewrite → check → rewrite → check → END (at most 3 checker passes).

### 6.5 Prompts (`agents/prompts/`)

One Markdown file per node: `focus.md`, `easyread.md`, `literal.md`, `urdu.md`, `quiz.md`, `checker.md`. Every transform prompt includes: "Use only facts from the SOURCE. Do not add information."
Each transform prompt has a `## <Style> style rules` section; the checker prompt receives only
the chosen style's section (via `load_prompt` / `style_rules` in `agents/prompts/__init__.py`),
so it never judges a lesson by another style's rules.
Focus hooks may only restate a SOURCE fact; Literal chunks use "What it is" / "How it works"
sections, plus "Example" only when the SOURCE gives one, and keep the SOURCE's wording for vague
quantities (never invent numbers); quiz answers must be stated in the chunk and the other options
clearly wrong according to it. No transform may add concluding sentences about importance, value
or effects the SOURCE does not state. Glossary meanings (all styles) may use plain, accurate
everyday definitions but must not add facts about the lesson topic.

### 6.6 LLM usage (`llm/`)

- One factory creates the chat model from settings (`LLM_MODEL`, low temperature, e.g. 0.2).
- All nodes use **structured outputs** (`with_structured_output(PydanticModel)`), so responses are validated models, not free text.
- Tests inject a **fake LLM** that returns fixed models, so unit tests are fast, free and offline.
- `agents/graph.py`: `build_graph(llm, settings=None)` compiles the graph (the LLM is injected;
  settings default to `get_settings()`); `build_lesson(state, student, urdu)` turns the final state
  into a `Lesson`. `scripts/try_agent.py <file> <mode|all>` runs the real agent from the command line (`all` runs
  the three modes in parallel).

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
