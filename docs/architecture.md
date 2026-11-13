# HumZehan — Architecture

How HumZehan is built. Product requirements are in [`PRD.md`](PRD.md). Update this file in the same pull request whenever the design changes.

_Last updated: 2026-11-13_

## 1. System overview

```
Browser (Next.js frontend)
    │  HTTP/JSON  (multipart for photos)
    ▼
FastAPI backend  ──►  services  ──►  LangGraph agent  ──►  LLM provider (OpenAI)
                          │  └─────►  vision model (photo → text) ──┘
                          └──────►  repositories  ──►  SQLite
```

A photo is read in a **separate step before transforming**: `POST /extract` returns the text, the
student checks and fixes it in the text box, then `POST /lessons` transforms it. The agent only
ever receives text.

| Part | Technology | Responsibility |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS | Study page, agent trace, quiz, dashboard |
| Backend | Python 3.12, FastAPI, uv | Versioned REST API, runs the agent, stores data |
| Agent | LangGraph, LangChain OpenAI | Multi-step rewrite → quiz → self-check loop |
| Storage | SQLite | Lessons and quiz progress |
| Quality | Ruff, mypy (strict), pytest, ESLint, Vitest, GitHub Actions | Checks on every pull request |

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
│   │   ├── core/           # config.py (Settings), logging.py, exceptions.py (domain errors)
│   │   ├── api/            # deps.py (FastAPI dependencies: settings, agent graph, services)
│   │   ├── api/v1/         # router.py + one module per resource (health.py, lessons.py, ...)
│   │   ├── schemas/        # Pydantic models: the API contract
│   │   ├── services/       # business logic; images.py (photo prep), prompts/extract.md
│   │   ├── agents/         # LangGraph: state.py, graph.py, nodes/, prompts/
│   │   ├── llm/            # LLM client factory
│   │   └── db/             # session.py (connect, init_db) + repositories.py
│   └── tests/
│       ├── conftest.py     # temp SQLite file per test; agent graph on the fake LLM
│       ├── fakes.py        # FakeLLM + make_lesson_llm(), shared by unit and integration tests
│       ├── unit/           # fast, no network (fake LLM)
│       └── integration/    # API-level tests
└── frontend/
    ├── package.json, vitest.config.mts, .env.example
    └── src/
        ├── app/            # routes: page.tsx (study page); dashboard/page.tsx in F7
        ├── features/
        │   └── lessons/    # modes.ts, components/ (study page UI), lib/ (pure helpers + tests)
        ├── lib/            # api.ts (typed API client), config.ts
        └── types/          # api.ts: API types mirroring backend schemas
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
- **Errors:** services raise domain exceptions from `core/exceptions.py` (`InvalidInputError`,
  `NotFoundError`, `LLMFailureError`); `main.py` maps them to 400 / 404 / 502 with `{"detail": ...}`.

Wiring (`api/deps.py`):
- `create_app(settings)` stores the settings on `app.state`; `get_app_settings` reads them back,
  so tests' settings reach every dependency.
- `get_agent_graph` builds the graph once with `get_chat_model(settings)`, lazily on first use, and
  caches it on `app.state` (behind a lock). Tests override it via `app.dependency_overrides` with a
  graph on the fake LLM, so no OpenAI client is ever built in tests.
- `get_vision_llm` builds the vision model the same way (once, lazily, cached on `app.state`
  behind a lock); tests override it with `FakeVisionLLM`.
- `get_*_service` dependencies build the repositories and services; routes receive a service only.
- The agent call is blocking: `POST /lessons` runs `LessonService.create` with
  `run_in_threadpool`, and `POST /extract` runs `ExtractService.extract` the same way; other
  routes are plain `def` (FastAPI runs them in its threadpool).
- Repositories open a short-lived SQLite connection per operation, so no connection is shared
  between threads.

## 4. Configuration

Loaded from environment variables / `backend/.env` by `core/config.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` / `test` / `production` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins (comma-separated) |
| `OPENAI_API_KEY` | — | LLM provider key (secret) |
| `LLM_MODEL` | `gpt-4o-mini` | Model used by all agent nodes |
| `VISION_MODEL` | same as `LLM_MODEL` | Model that reads text from photos (must accept images); empty → `LLM_MODEL` |
| `AGENT_MAX_LOOPS` | `2` | Maximum rewrite rounds sent back by the checker |
| `DATABASE_PATH` | `humzehan.db` | SQLite file location |
| `MAX_SOURCE_CHARS` | `8000` | Maximum source text length (characters); longer → 400 |
| `MAX_IMAGE_BYTES` | `10485760` (10 MB) | Maximum photo upload size; larger → 400 |

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
    hook: str | None              # Focus mode: the "key idea"
    glossary: list[GlossaryItem]
    quiz: list[QuizItem]          # 3 per chunk

class TraceStep(BaseModel):
    node: str                     # e.g. "checker"
    note: str                     # e.g. "Chunk 2: simplify (sentence over 12 words)"
    ms: int

class EnglishVersion(BaseModel):  # F5
    title: str
    chunks: list[Chunk]

class Lesson(BaseModel):
    lesson_id: str                # UUID
    student: str
    mode: LearningMode
    urdu: bool                    # True only when title/chunks are in Urdu
    title: str                    # Urdu for Urdu lessons
    chunks: list[Chunk]           # Urdu for Urdu lessons
    english: EnglishVersion | None  # Urdu lessons: the original English (same structure)
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

class ExtractResponse(BaseModel):  # schemas/extract.py
    text: str                     # text read from the photo
```

## 6. The agent (`agents/`)

### 6.1 Graph

```
ingest → router → focus_transform    ┐
                → easyread_transform ┼→ quiz → checker ─┬→ urdu (if urdu) → END
                → literal_transform  ┘                  ├→ END (if not urdu)
                         ▲                              │
                         └─ non-approved chunks + notes ┘
                            (while loops < AGENT_MAX_LOOPS)
```

The whole pipeline runs and is checked **in English**: the checker and the grounding pre-check
compare chunks with the English SOURCE, so they cannot verify Urdu. Translation is the last
node, reached only when the checker is done (all approved, or out of rewrite rounds) and
`urdu=True`.

### 6.2 State (`agents/state.py`)

```python
CheckerAction = Literal["approve", "simplify", "add_glossary", "fix_fact", "missing_fact"]

class ChunkReview(BaseModel):
    chunk_index: int
    action: CheckerAction
    reason: str
    quote: str | None              # evidence: see 6.4 (null for approve/simplify/add_glossary)

class AgentState(TypedDict, total=False):
    source_text: str               # always text: photos are read before the agent (7.1)
    mode: LearningMode
    urdu: bool                     # F5: translate after the checker
    title: str
    chunks: list[Chunk]
    english: EnglishVersion | None # set by the urdu node on success
    reviews: list[ChunkReview]
    loops: int                     # rewrite rounds done
    trace: list[TraceStep]
```

The LLM's structured-output models live in the same file: `ChunkDraft` (one chunk without quiz),
`TransformOutput` (title + chunks), `QuizSet` (exactly 3 questions), `CheckerOutput` (`reviews`
plus `suspect_judgments: list[SuspectJudgment]`, where `SuspectJudgment` is
`{suspect_id, supported, reason}`; see 6.4), `ChunkTranslation` (one translated chunk: heading,
body, hook, glossary, quiz with `answer_index`) and `TitleTranslation`.

### 6.3 Nodes (`agents/nodes/`)

| Node | Input → output | Notes |
| --- | --- | --- |
| `ingest` | `source_text` → `source_text` | Text only. Photos are read before the agent by `POST /extract` (7.1), so the student can fix the text first |
| `router` | `mode` → next node name | No LLM call. The node records the decision in the trace; the pure function `route_by_mode(state)` drives the conditional edges |
| `*_transform` | `source_text` (+ reviews) → `title`, `chunks`, `loops` | One prompt per mode (one factory builds all three nodes); on a re-run, only non-approved chunks are rewritten using the checker's notes, their quiz is cleared, and `loops` += 1 |
| `quiz` | `chunks` → `chunks[i].quiz` | Answers only from the chunk; only chunks with an empty quiz (new or rewritten) get questions |
| `checker` | `source_text`, `chunks`, `mode` → `reviews` | Grounding pre-check first (6.4), then one call over the whole lesson with the suspect sentences. Structured output with quoted evidence and one judgment per suspect; flags are verified in code (6.4) and normalised to exactly one `ChunkReview` per chunk (missing → approve). The trace note lists kept flags, "suspects: N (x unsupported, y supported)" and "dropped N unverified flags" |
| `urdu` | `title`, `chunks`, `mode` → `title`, `chunks`, `english` | Last node, only when `urdu=True` (F5); see 6.7 |

### 6.7 Urdu translation (`agents/nodes/urdu.py`)

1. One `ChunkTranslation` prompt per chunk (the chunk as JSON, including quiz answers, plus the
   chosen style's notes from `urdu_styles.md`), all sent in one parallel batch with
   `ask_many_or_errors()` (like `ask_many`, but a provider error or schema-invalid output becomes
   that chunk's failure instead of failing the batch); then one `TitleTranslation` call.
2. `validate_translation(english, urdu)` (pure) checks each chunk: hook present in both or
   neither; same number of glossary items, questions and options per question; every
   `answer_index` unchanged (options keep their order); no empty text. Chunks are translated
   one-to-one, so the chunk count cannot change.
3. Failed chunks are retried once, in one batch. If any chunk still fails (or the title is
   empty), the node leaves `title`/`chunks` in English, sets `english=None` and the trace note
   says why ("Urdu translation failed validation for chunk 0 (question 1: answer_index changed);
   showing English").
4. **Key-term check** (lighter, never causes the English fallback): `key_terms(chunk)` takes the
   bold terms of the English body and hook (bold-only lines such as Literal section labels and
   bold text without Latin letters are skipped); they are listed as KEY TERMS in the prompt.
   `missing_terms(terms, urdu)` returns those that appear nowhere in the Urdu heading, body, hook
   or glossary (case-insensitive; "forces" also matches "force"). A structurally valid chunk with
   missing terms is retried once in the same retry batch, with a hint naming them; the retry is
   kept if it is valid and misses no more terms, otherwise the first translation stays. Terms
   still missing after the retry are accepted and listed in the trace note.
5. On success, `title`/`chunks` become Urdu and `english` keeps the checked English version; the
   note says "Translated N chunks to Urdu (retried: k)", plus "English terms still missing
   (chunk i: …)" when any remain.

Prompt rules (`urdu.md`): the everyday spoken Urdu of a Class 9 student in Pakistan, in Urdu
script, avoiding heavy academic Arabic/Persian words when a common word exists ("ایک دوسرے پر اثر
ڈالنا", not "تعامل"); one consistent term per concept across the chunk, glossary and quiz;
translate faithfully, never add, drop or change facts; the first time a key term appears, the
Urdu followed by the English in brackets ("قوت (force)", "کلاسیکی میکانکس (classical
mechanics)", "بخارات بننا (evaporation)"); numbers, formulas and symbols unchanged in Western
digits; Markdown kept; Literal labels **یہ کیا ہے** / **یہ کیسے کام کرتا ہے** / **مثال**. Same
low temperature as the other nodes.

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

One Markdown file per node: `focus.md`, `easyread.md`, `literal.md`, `urdu.md`, `quiz.md`, `checker.md`
(plus `urdu_styles.md`, the per-style notes for the translation: the urdu node sends only the
chosen style's `## <Style> style` section, via `prompt_section()`). Every transform prompt includes: "Use only facts from the SOURCE. Do not add information."
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
  settings default to `get_settings()`); `build_lesson(state, student)` turns the final state
  into a `Lesson` (`urdu` is true only when the urdu node set `english`). `scripts/try_agent.py <file> <mode|all>` runs the real agent from the command line (`all` runs
  the three modes in parallel).

## 7. API (`/api/v1`)

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/health` | — | `{status, version}` |
| POST | `/extract` | multipart: `image` (JPEG/PNG/WEBP) | `ExtractResponse` |
| POST | `/lessons` | multipart: `student`, `mode`, `urdu`, `text` | `201` `Lesson` |
| GET | `/lessons/{lesson_id}` | — | `Lesson` or `404` |
| POST | `/progress` | JSON `ProgressCreate` | `204` |
| GET | `/dashboard` | — | `DashboardSummary` |

Errors return `{"detail": "<message>"}` with a suitable status code (400 bad input, 404 not found, 502 LLM failure).
Request bodies that fail schema validation (unknown `mode`, `score` outside 0–3, negative
`chunk_index`, missing fields) get FastAPI's standard `422` (`detail` is a list of errors).

`POST /lessons` takes `student`, `mode`, `text` and optional `urdu` (bool, default `false`;
anything other than a boolean → 422); photos go through `POST /extract` first. 400 for: blank student, empty text, text longer than
`MAX_SOURCE_CHARS`, `chunk_index` beyond the lesson's chunks. 404 for an unknown lesson id
(GET lesson or progress).

### 7.1 Photo text extraction (`POST /extract`)

The route reads at most `MAX_IMAGE_BYTES + 1` bytes and calls `ExtractService.extract`
(`services/extract_service.py`) in a worker thread:

1. Empty or missing file → 400; more than `MAX_IMAGE_BYTES` → 400.
2. `prepare_image()` (`services/images.py`, pure): Pillow detects the format **from the file's
   bytes** (not the name or content type); only JPEG, PNG and WEBP are accepted, anything else
   or an unreadable/truncated file → 400 "Please upload a JPG, PNG or WEBP photo." Then: rotate
   using the EXIF orientation, convert to RGB (transparency → white), shrink so the longest side
   is at most 2048 px (never enlarge), re-encode as JPEG (quality 85).
3. One vision call (`get_vision_model`, `VISION_MODEL`, temperature 0) with the system prompt
   `services/prompts/extract.md` and the JPEG as a base64 data URL, structured output
   `PageText {text, legible}`. The prompt: copy the printed text exactly, keep paragraph breaks
   and headings (as Markdown headings), skip page numbers and running headers/footers, never
   summarize, translate, correct or add anything.
4. Provider error → 502 "The AI service could not read the photo." `legible=false` or empty
   text → 400 "We couldn't read text in this photo. Try a clearer, well-lit photo of one page."
5. Returns `{"text": ...}` (stripped). The text is not length-checked here: the student edits it
   and `POST /lessons` applies `MAX_SOURCE_CHARS`.

The image is **never stored or logged**; a provider failure is logged with the error type only.

## 8. Database (SQLite)

```sql
CREATE TABLE IF NOT EXISTS lessons (
    id          TEXT PRIMARY KEY,
    student     TEXT NOT NULL,
    mode        TEXT NOT NULL,
    title       TEXT NOT NULL,
    payload     TEXT NOT NULL,      -- full Lesson as JSON
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id    TEXT NOT NULL REFERENCES lessons(id),
    chunk_index  INTEGER NOT NULL,
    score        INTEGER NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lessons_student ON lessons(student);
```

`db/session.py` creates the schema at app startup (FastAPI lifespan) from `DATABASE_PATH`.
`progress` keeps every attempt. The dashboard (`ProgressRepository.summary_by_student()`, one query)
counts per student: lessons, chunks completed (distinct `(lesson_id, chunk_index)` with a score)
and the average of the **latest** score per chunk (`null` when there are no scores).

The payload of an Urdu lesson includes `english` (the original English title and chunks); lessons
stored before F5 have no `english` field and load with `english=None`.

Storing the full lesson as JSON keeps v1 simple; the repository layer allows moving to PostgreSQL later without touching services.

## 9. Frontend (`frontend/`)

Next.js (App Router) + TypeScript + Tailwind CSS. The study page (`app/page.tsx`) is a server
page that renders one client component, `features/lessons/components/StudyPage.tsx`.

**API client** (`lib/api.ts`): `createLesson()` (multipart `POST /lessons`),
`extractText()` (multipart `POST /extract`, returns the text) and `recordProgress()`
(JSON `POST /progress`), typed with `types/api.ts`. The base URL is
`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`, see `frontend/.env.example`). Errors become
an `ApiError` whose message is the backend's `detail` (string, or the first message of a 422
list); a network failure gives a friendly "couldn't reach the server" message.

**Study page states:** `idle → loading → ready | error`.
- *Form:* student name (remembered in `localStorage`, all access in try/catch), a "Paste text" /
  "Upload a photo" choice, study text with a character counter (`MAX_SOURCE_CHARS` = 8000,
  mirrored in `lib/config.ts`), learning-style radio cards, a "Get this lesson in simple Urdu"
  checkbox (sent as `urdu` by `createLesson()`), Transform button (only in the text
  view, and not while a photo is being read).
- *Photo* (`PhotoInput.tsx`): file input accepting JPEG/PNG/WEBP (no `capture` attribute, so
  phones offer the camera and the photo library), checked in the browser first with
  `checkPhoto()` (`features/lessons/lib/photo.ts`; type and `MAX_IMAGE_BYTES` = 10 MB, mirrored in
  `lib/config.ts`), a preview (`URL.createObjectURL`, released when replaced or unmounted), photo
  tips, and "Read text from photo". While reading: a calm "Reading your photo…" status. On success
  the text replaces the text box, the view switches to "Paste text" and a note says "Check the text
  below and fix any mistakes before you transform." Errors (client checks, backend `detail`,
  unreachable server) are shown inline. Both views stay mounted, so the photo is kept when
  switching.
- *Loading:* the API answers only when the lesson is finished, so the page lists the pipeline
  steps with an elapsed-time counter (plus the translation step when Urdu was requested); no step
  is marked done and no checker decision is shown.
- *Ready:* a collapsible **Agent trace** (`<details>`) with the real `trace` (node, note, ms,
  total), then the lesson. Chunk bodies are rendered as Markdown with `react-markdown`
  (raw HTML is not rendered). Every style shows a chunk's glossary under it when it is not
  empty.
- *Error:* the message plus "Try again"; the form keeps its input.

**Per-style display:**

| Style | Display |
| --- | --- |
| Focus | Hook ("Key idea") at the top of each chunk, a tick box per chunk, sticky progress bar of chunks done |
| Easy-read | Lexend font (`next/font/google`), larger text, line height 1.8, cream background |
| Literal | Body split into "What it is / How it works / Example" sections on bold-only lines (`splitLiteralSections`); each section's `kind` is recognised from the English or the Urdu label (`literalSectionKind`, `LITERAL_LABELS`) |

**Simple Urdu (F5):**
- Urdu lessons (`urdu: true`) render the title and lesson content with `lang="ur"`, `dir="rtl"`
  and the `.lesson-urdu` class: Noto Nastaliq Urdu (`next/font/google`, Arabic subset, so English
  words fall back to the sans font), chunk text 1.2rem, line height 2.2, no letter spacing
  (it breaks joined Urdu letters). List indents use logical (`inline-start`) padding and the
  Focus hook border is `border-s`, so both mirror in RTL.
- Mixed text: `isolateLtr()` (`features/lessons/lib/bidi.ts`) wraps every run of Latin letters,
  digits and formula symbols in Unicode isolates (LRI … PDI), so `F = ma`, `9.8 m/s²` and
  `(evaporation)` read left-to-right inside Urdu (brackets stay in the Urdu text and mirror).
  It is applied to headings, hooks, glossary and quiz text, and to Markdown bodies through the
  `rehypeIsolateLtr` plugin (after parsing, so Markdown syntax is untouched; code is skipped).
- Lesson labels (key idea, quick quiz, check answers, score line, glossary, chunk done,
  chunks-done progress, quiz feedback) come from `lessonLabels("en" | "ur")`
  (`features/lessons/lib/labels.ts`); the rest of the page, including save messages, stays
  English. The score and progress lines are whole phrases with Urdu words between the numbers
  ("اسکور: 3 میں سے 1" = 1 out of 3), so right-to-left display can never swap the numbers (a bare
  "1 / 3" can show as "3 / 1").
- A "Show English" / "Show Urdu" button switches the content to `lesson.english` and back. The
  same elements are rendered in both languages (only attributes change), so ticks and quiz
  answers are kept; this relies on the backend's guarantee of identical structure and answers.
- If Urdu was requested but the lesson came back in English (translation failed validation),
  the page says so and points to the agent trace.

**Quiz:** 3 questions per chunk; Check reveals correct and incorrect answers and the score
(0–3), which is sent once per chunk with `recordProgress()`. If saving fails, the result stays
visible with a "Retry saving" button.

**Accessibility:** native form controls (radio groups in `fieldset`/`legend`, labels on every
input), visible focus ring, touch targets at least 44px, single column on phones, the only
animation is a slow pulse that stops under `prefers-reduced-motion`.

**Tests:** Vitest (`npm test`) for pure helpers in `features/lessons/lib/` and `lib/api.ts`
(quiz scoring, character limit, Literal sections in English and Urdu, photo file checks, error
messages, the `urdu` form field, Urdu label dictionary, `isolateLtr`).

## 10. Testing strategy

| Level | What | Tools |
| --- | --- | --- |
| Unit | Each agent node, router and loop logic, Urdu translation validation / retry / English fallback, schemas, photo prep (`prepare_image`) | pytest + fake LLM (fake translator keeps the structure), images generated with Pillow |
| Integration | Each endpoint with a temporary SQLite file, the fake-LLM graph and `FakeVisionLLM` | pytest + FastAPI `TestClient` |
| Evals (F8) | Real pages through the real model; quality scores | `evals/run.py` |
| Frontend unit | Pure helpers (quiz scoring, character limit, Literal sections, photo checks, API errors, Urdu labels, bidi isolation) | Vitest |
| CI | Ruff, mypy, pytest; ESLint, type-check, Vitest, build | GitHub Actions on every PR |

## 11. Observability, security and privacy

- **Logging:** standard logging via `core/logging.py`; never log students' raw text in production.
  Photos are never logged or stored.
- **Tracing (F8):** LangSmith or Langfuse, enabled by environment variables.
- **Limits:** maximum text length (`MAX_SOURCE_CHARS`) and photo size (`MAX_IMAGE_BYTES`, real
  file type checked); rate limiting per client and API spending cap in F9.
- **Privacy:** no diagnosis or health data is collected; only names, chosen style, lessons and scores.

## 12. Deployment (F9)

| Part | Platform |
| --- | --- |
| Frontend | Vercel (root directory `frontend`) |
| Backend | Railway or Render, from a Dockerfile in `backend/` |
| Database | SQLite on a persistent volume |

## 13. Key decisions

| Decision | Reason |
| --- | --- |
| Monorepo (backend + frontend) | One place for issues, CI and docs; solo developer |
| uv for Python | Fast, one tool, reproducible lockfile |
| LangGraph for the agent | Explicit state, branching and loops for the checker |
| Structured outputs everywhere | Validated data instead of parsing free text |
| SQLite for v1 | Zero setup; repository layer allows a later move to PostgreSQL |
| Browser speech for audio | Free, no extra API key |
| Urdu translation is the last node, after the checker | The checker and grounding pre-check compare with the English SOURCE and cannot verify Urdu; translating the checked lesson keeps every fact check, and code-level structure validation (with English fallback) protects the quiz answers |
| Photo extraction is a separate step before the agent | The student can check and fix the text (photos are often imperfect); the agent stays text-only and works on text the student has seen |
