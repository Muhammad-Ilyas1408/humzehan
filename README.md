# HumZehan (ہم ذہن)

**Study the way your mind works.**

HumZehan is an agentic AI study companion. Give it any textbook page (as text or a photo), choose a learning style, and it rewrites the material to fit how you learn, then checks its own work before showing it to you.

> 🚧 **Status:** in active development. The backend foundation is in place; the agent and frontend are being built.

## What it will do

- **Three learning styles you choose:**
  - **Focus:** short chunks, one step at a time, with a "key idea" hook that restates a fact from the page.
  - **Easy-read:** short sentences, simple words, and read-aloud audio.
  - **Literal:** clear, exact language with a fixed structure and idioms explained.
- **Simple Urdu:** optional Urdu version of any lesson.
- **Self-checking agent:** a checker reviews every chunk against the source and sends weak ones back to be improved, so the content stays accurate and easy to follow.
- **Live agent trace:** see each step the agent takes and every decision it makes.
- **Quizzes and progress:** 3 questions per chunk and a simple progress dashboard.

HumZehan never diagnoses anything. Students choose a learning style.

## How it works

```
ingest → router → focus | easyread | literal → urdu (optional) → quiz → checker
                                                                   │
                                     weak chunks loop back ◄───────┘ (max 2 times)
```

## Tech stack

**Backend:** Python 3.12, FastAPI, LangGraph, LangChain OpenAI, Pydantic, SQLite, managed with [uv](https://docs.astral.sh/uv/)
**Frontend:** Next.js, TypeScript, Tailwind CSS *(in progress)*
**Quality:** Ruff, mypy (strict), pytest

## Project structure

```
humzehan/
├── backend/            # FastAPI + LangGraph agent
│   ├── src/humzehan/   # app code: api, core, schemas, services, agents, db
│   └── tests/
└── frontend/           # Next.js app (in progress)
```

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/) and an OpenAI API key.

```bash
cd backend
cp .env.example .env     # then add your OPENAI_API_KEY
uv sync
uv run uvicorn humzehan.main:app --reload
```

Open http://127.0.0.1:8000/docs.

Run the checks:

```bash
uv run ruff check . && uv run mypy src && uv run pytest
```

## Roadmap

- [x] Backend foundation: settings, logging, health endpoint, tests
- [ ] LangGraph agent with the three learning styles and the checker loop
- [ ] Lessons, progress and dashboard API
- [ ] Frontend: study page, agent trace, quizzes, dashboard
- [ ] Photo upload and simple Urdu
- [ ] Evals, deployment and user testing

## Author

**Muhammad Ilyas** · [LinkedIn](https://linkedin.com/in/muhammad-ilyas-ds) · [GitHub](https://github.com/Muhammad-Ilyas1408)