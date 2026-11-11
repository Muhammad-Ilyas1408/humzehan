"""Run the real agent on a text file and print the lesson and trace.

Usage (from backend/):
    uv run python scripts/try_agent.py sample.txt focus
    uv run python scripts/try_agent.py sample.txt all     # focus, easyread, literal in parallel
Needs OPENAI_API_KEY in backend/.env.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from humzehan.agents.graph import AgentGraph, build_graph, build_lesson
from humzehan.core.config import get_settings
from humzehan.llm.client import get_chat_model
from humzehan.schemas.lesson import LearningMode, Lesson

MODE_NAMES = [m.value for m in LearningMode]
CHOICES = ", ".join([*MODE_NAMES, "all"])


@dataclass
class Run:
    lesson: Lesson
    rewrite_rounds: int
    seconds: float


def run_mode(graph: AgentGraph, source_text: str, mode: LearningMode) -> Run:
    started = time.perf_counter()
    state = graph.invoke(
        {"source_text": source_text, "mode": mode, "urdu": False, "trace": []},
    )
    seconds = time.perf_counter() - started
    lesson = build_lesson(state, student="try_agent")
    return Run(lesson=lesson, rewrite_rounds=state.get("loops", 0), seconds=seconds)


def print_run(run: Run) -> None:
    lesson = run.lesson
    print(f"\n{'=' * 78}\n# {lesson.title}  ({lesson.mode.value})\n")
    for index, chunk in enumerate(lesson.chunks):
        print(f"## {index}. {chunk.heading}")
        if chunk.hook:
            print(f"Key idea: {chunk.hook}")
        print(f"\n{chunk.body}\n")
        for item in chunk.glossary:
            print(f"  - {item.term}: {item.meaning}")
        for q_number, quiz in enumerate(chunk.quiz, start=1):
            print(f"  Q{q_number}. {quiz.question}")
            for o_index, option in enumerate(quiz.options):
                mark = "✓" if o_index == quiz.answer_index else " "
                print(f"     [{mark}] {option}")
        print()

    print("Trace")
    print(f"{'node':<20} {'ms':>7}  note")
    for step in lesson.trace:
        print(f"{step.node:<20} {step.ms:>7}  {step.note}")
    print(f"rewrite rounds: {run.rewrite_rounds}   total time: {run.seconds:.1f} s")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: uv run python scripts/try_agent.py <file.txt> <mode>  ({CHOICES})")
        return 2
    path, choice = Path(argv[1]), argv[2]
    if choice not in [*MODE_NAMES, "all"]:
        print(f"Unknown mode {choice!r}. Choose one of: {CHOICES}")
        return 2
    if not path.is_file():
        print(f"File not found: {path}")
        return 2

    settings = get_settings()
    if not settings.openai_api_key.get_secret_value():
        print("OPENAI_API_KEY is not set. Add it to backend/.env (see .env.example).")
        return 1

    graph = build_graph(get_chat_model(settings), settings)
    source_text = path.read_text(encoding="utf-8")
    modes = list(LearningMode) if choice == "all" else [LearningMode(choice)]

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(modes)) as pool:
        runs = list(pool.map(lambda mode: run_mode(graph, source_text, mode), modes))
    wall = time.perf_counter() - started

    for run in runs:
        print_run(run)

    if len(runs) > 1:
        print(f"\n{'=' * 78}\nSummary (modes ran in parallel, wall time {wall:.1f} s)")
        print(f"{'mode':<10} {'chunks':>6} {'rewrite rounds':>15} {'time':>8}")
        for run in runs:
            print(
                f"{run.lesson.mode.value:<10} {len(run.lesson.chunks):>6} "
                f"{run.rewrite_rounds:>15} {run.seconds:>7.1f}s"
            )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    raise SystemExit(main(sys.argv))
