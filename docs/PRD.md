# HumZehan — Product Requirements Document (PRD)

| | |
| --- | --- |
| **Product** | HumZehan (ہم ذہن, "like-minded") |
| **Tagline** | Study the way your mind works. |
| **Owner** | Muhammad Ilyas |
| **Status** | v1.0 in development |
| **Last updated** | 2026-11-10 |

## 1. Overview

HumZehan is an agentic AI study companion. A student gives it a textbook page (pasted text or a photo) and chooses a learning style. HumZehan rewrites the page to fit that style, checks its own work against the source, and helps the student study it with audio and short quizzes. A teacher or parent can see progress on a simple dashboard.

## 2. Problem

Textbooks are written one way for everyone: long paragraphs, difficult words and figures of speech. Many students struggle with this format:

- Students who lose focus easily give up on walls of text.
- Students who find reading hard (for example, with dyslexia) struggle with long sentences and difficult vocabulary.
- Students who take language literally (common for autistic students) are confused by idioms and vague wording.
- Many students in Pakistan understand better in simple Urdu than in textbook English.

Teachers rarely have time to adapt every lesson for every student.

## 3. Users

| User | Need |
| --- | --- |
| **Student** (primary) | Understand a textbook page faster, in a format that suits them |
| **Teacher / parent** (secondary) | See what students studied and how they scored |

## 4. Goals and non-goals

**Goals (v1.0)**
1. Rewrite any textbook page into one of three learning styles in under 30 seconds.
2. Never add facts that are not in the source.
3. Make the agent's work visible, so users can trust it.
4. Be used by 20–30 real students, with feedback collected.

**Non-goals (v1.0)**
- Diagnosing or screening for any condition.
- User accounts, logins or payments.
- Teacher-managed classes or assignments.
- A mobile app (the web app should still work on phones).
- Integration with school systems or WhatsApp.

## 5. Product principles

1. **Choose, never diagnose.** The student picks a learning style. UI copy says "learning style," never condition names.
2. **Faithful to the source.** Rewrite and simplify; never invent.
3. **Show the work.** Every agent step and decision appears in the trace.
4. **Calm by design.** Large touch targets, soft colors, no distracting animation.

## 6. Learning styles

| Style | Rules |
| --- | --- |
| **Focus** | Chunks of about 100 words; a one-line "why this matters" hook; the key term in bold; a tick box per chunk |
| **Easy-read** | Sentences under 12 words; everyday words; one idea per sentence; a mini glossary per chunk; readability font; read-aloud |
| **Literal** | No idioms or metaphors (any in the source are explained); inside each chunk: What it is / How it works, plus Example only when the source gives one; keep the source's wording when it is vague, never invent numbers |
| **Simple Urdu** (optional, combines with any style) | Everyday Urdu in Urdu script; science terms kept in English brackets |

**All styles:** lessons contain only facts from the source, with no concluding sentences about importance, value or effects that the source does not state. The one exception is the glossary: meanings may use plain, accurate everyday definitions of a word, but must not add facts about the lesson topic.

## 7. Features and acceptance criteria

Each feature is built in its own branch and pull request.

### F1 — Lesson data models and LangGraph agent (text input)
- Pydantic models exist for Lesson, Chunk, GlossaryItem, QuizItem, TraceStep and checker reviews.
- Given source text and a learning style, the agent returns a Lesson with chunks and 3 quiz questions per chunk.
- The checker reviews every chunk and decides `approve`, `simplify`, `add_glossary`, `fix_fact` or `missing_fact`, with a reason.
- `fix_fact` and `missing_fact` are evidence-based: each quotes the unsupported chunk sentence or the missing source sentence, and flags whose evidence does not hold up are dropped in code.
- A deterministic grounding pre-check marks chunk sentences with little word overlap with the source as suspect; the checker must judge each one, and confirmed ones become `fix_fact`.
- Non-approved chunks are rewritten; the loop stops when all chunks are approved or after `AGENT_MAX_LOOPS` (default 2).
- Every node appends a trace step (node, note, milliseconds).
- Nodes are unit-tested with a fake LLM (no network in tests).

### F2 — Lessons API and storage
- `POST /api/v1/lessons` creates a lesson from text and returns it.
- `GET /api/v1/lessons/{lesson_id}` returns a saved lesson, or 404.
- `POST /api/v1/progress` saves a quiz score for a chunk.
- `GET /api/v1/dashboard` returns per-student totals.
- Lessons and progress are stored in SQLite; integration tests cover each endpoint.

### F3 — Study page (frontend)
- Student enters a name, pastes text, chooses a style and transforms it.
- The agent trace is shown while and after the lesson is created.
- Chunks are displayed with each style's visual rules; Focus shows a progress bar.
- Each chunk has a 3-question quiz; scores are saved through the API.
- Clear loading and error states.

### F4 — Photo upload
- Student can upload a photo of a page (JPG/PNG, size-limited).
- The ingest step extracts the text with a vision model before transforming.

### F5 — Simple Urdu
- An "Urdu" toggle produces the lesson in simple Urdu, with correct right-to-left display.

### F6 — Read aloud
- Each chunk has a "Listen" button using the browser's speech engine (Urdu voice when available).

### F7 — Dashboard
- Shows per student: lessons, chunks completed, average quiz score, recent lessons.

### F8 — Evals and tracing
- An eval set of 15–20 real textbook pages.
- An eval script scores faithfulness, style-rule compliance, readability, quiz answerability, cost and time.
- Results are saved and the summary is in the README.
- Agent runs are traced (LangSmith or Langfuse).

### F9 — Deploy and launch
- Frontend on Vercel, backend on Railway or Render (Docker).
- Rate limiting, input size limits and an API spending cap.
- Tested with 20–30 students; top feedback fixed.
- Final README, demo video, `v1.0.0` release.

## 8. Success metrics

| Metric | Target for v1.0 |
| --- | --- |
| Faithfulness (no added facts, per eval) | ≥ 95% of chunks |
| Style rules followed (per eval) | ≥ 90% of chunks |
| Time to create a lesson | < 30 seconds (p90) |
| Real students who used it | 20–30 |
| Students who found it helpful (feedback form) | ≥ 70% |

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| The model adds or changes facts | Checker with `fix_fact`; faithfulness evals; low temperature |
| Poor text extraction from photos | Clear photo tips in the UI; allow editing extracted text |
| API costs grow | Small default model, input limits, rate limiting, spending cap |
| Weak Urdu quality | Dedicated Urdu prompt; review by native speakers during user testing |
| Misunderstood as a medical tool | "Learning style" language only; no diagnosis anywhere |

## 10. Future ideas (after v1.0)

Student accounts and saved libraries; teacher classes and shared lessons; WhatsApp delivery; more languages (Pashto, Sindhi); offline support.
