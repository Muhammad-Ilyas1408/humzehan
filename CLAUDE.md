# HumZehan — guide for Claude Code
AI study companion that rewrites study material into a learning style the student CHOOSES
(focus, easyread, literal), with optional simple Urdu. Never diagnose; say "learning style".

## Rules
- Python: uv only (uv add, uv add --dev, uv run). Never pip or requirements.txt.
- Backend code in backend/src/humzehan/; tests in backend/tests/ (unit/, integration/).
- Layers: api routes -> services -> agents / db. Routes never call the agent or DB directly.
- Settings only via core/config.py (pydantic-settings); secrets only from .env.
- The agent must never add facts that are not in the source.
- After each task run: uv run ruff check . ; uv run mypy src ; uv run pytest — and fix failures.
- Do only what I ask in each prompt, then stop and tell me how to check it.