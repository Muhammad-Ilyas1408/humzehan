"""Agent graph tests with a fake LLM (no network)."""

import re
from collections.abc import Callable

import pytest
from pydantic import BaseModel

from fakes import URDU, FakeLLM, translate_chunk, translate_title
from humzehan.agents.graph import build_graph, build_lesson
from humzehan.agents.state import (
    AgentState,
    CheckerAction,
    CheckerOutput,
    ChunkDraft,
    ChunkReview,
    ChunkTranslation,
    QuizSet,
    TitleTranslation,
    TransformOutput,
)
from humzehan.core.config import Settings
from humzehan.schemas.lesson import LearningMode, QuizItem

STYLE_NAMES = {"focus": "Focus", "easyread": "Easy-read", "literal": "Literal"}
SOURCE = "Plants make food from sunlight. This is called photosynthesis. Leaves hold chlorophyll."


def transform_output(_: str) -> TransformOutput:
    return TransformOutput(
        title="Photosynthesis",
        chunks=[
            ChunkDraft(
                heading="Food from light", body="Plants make **food**.", hook=None, glossary=[]
            ),
            ChunkDraft(
                heading="Leaves", body="Leaves hold **chlorophyll**.", hook=None, glossary=[]
            ),
        ],
    )


def rewrite_draft(user: str) -> ChunkDraft:
    match = re.search(r"PREVIOUS CHUNK \(chunk (\d+)\)", user)
    assert match, "rewrite prompt must name the chunk"
    return ChunkDraft(heading=f"Rewritten {match.group(1)}", body="Short.", hook=None, glossary=[])


def quiz_set(_: str) -> QuizSet:
    item = QuizItem(
        question="What do plants make?", options=["Food", "Rocks", "Air"], answer_index=0
    )
    return QuizSet(questions=[item, item, item])


def checker_sequence(rounds: list[dict[int, CheckerAction]]) -> Callable[[str], CheckerOutput]:
    """Checker returns rounds[n] on its n-th call (last round repeats); unlisted chunks approve."""
    calls = {"n": 0}

    def respond(_: str) -> CheckerOutput:
        flagged = rounds[min(calls["n"], len(rounds) - 1)]
        calls["n"] += 1
        reviews = [
            ChunkReview(
                chunk_index=i,
                action=flagged.get(i, "approve"),
                reason=f"reason for chunk {i}" if i in flagged else "ok",
                quote=None,
            )
            for i in range(2)
        ]
        return CheckerOutput(reviews=reviews, suspect_judgments=[])

    return respond


def make_llm(rounds: list[dict[int, CheckerAction]] | None = None) -> FakeLLM:
    handlers: dict[type[BaseModel], Callable[[str], BaseModel]] = {
        TransformOutput: transform_output,
        ChunkDraft: rewrite_draft,
        QuizSet: quiz_set,
        CheckerOutput: checker_sequence(rounds or [{}]),
        ChunkTranslation: translate_chunk,
        TitleTranslation: translate_title,
    }
    return FakeLLM(handlers=handlers)


def run(
    llm: FakeLLM,
    settings: Settings,
    mode: LearningMode = LearningMode.FOCUS,
    urdu: bool = False,
) -> AgentState:
    graph = build_graph(llm, settings)
    return graph.invoke({"source_text": SOURCE, "mode": mode, "urdu": urdu, "trace": []})


@pytest.mark.parametrize("mode", list(LearningMode))
def test_each_mode_returns_valid_lesson(mode: LearningMode, settings: Settings) -> None:
    llm = make_llm()
    state = run(llm, settings, mode)
    lesson = build_lesson(state, student="Ali")

    assert lesson.mode == mode
    assert lesson.title == "Photosynthesis"
    assert len(lesson.chunks) == 2
    assert all(len(chunk.quiz) == 3 for chunk in lesson.chunks)
    transform_call = llm.calls_for(TransformOutput)[0]
    assert f"**{STYLE_NAMES[mode]}**" in transform_call.system
    assert "Use only facts from the SOURCE" in transform_call.system


def test_checker_loop_reruns_only_non_approved_chunks(settings: Settings) -> None:
    llm = make_llm(rounds=[{1: "simplify"}, {}])
    state = run(llm, settings)

    rewrites = llm.calls_for(ChunkDraft)
    assert len(rewrites) == 1
    assert llm.batch_sizes(ChunkDraft) == [1]
    assert llm.batch_sizes(QuizSet) == [2, 1]  # first pass batched, then only the rewrite
    assert "PREVIOUS CHUNK (chunk 1)" in rewrites[0].user
    assert "simplify - reason for chunk 1" in rewrites[0].user
    assert "Fix only the quoted problem" in rewrites[0].user
    assert state["chunks"][0].heading == "Food from light"
    assert state["chunks"][1].heading == "Rewritten 1"
    assert all(len(chunk.quiz) == 3 for chunk in state["chunks"])
    assert len(llm.calls_for(QuizSet)) == 3  # 2 first pass + 1 for the rewritten chunk
    assert state["loops"] == 1
    assert len(llm.calls_for(CheckerOutput)) == 2


@pytest.mark.parametrize("max_loops", [0, 1, 2, 3])
def test_loop_stops_at_max_rewrite_rounds(max_loops: int) -> None:
    settings = Settings(_env_file=None, app_env="test", agent_max_loops=max_loops)
    llm = make_llm(rounds=[{0: "simplify", 1: "add_glossary"}])
    state = run(llm, settings)

    assert state["loops"] == max_loops
    assert len(llm.calls_for(CheckerOutput)) == max_loops + 1
    assert len(llm.calls_for(ChunkDraft)) == 2 * max_loops
    transform_steps = [s for s in state["trace"] if s.node == "focus_transform"]
    assert len(transform_steps) == 1 + max_loops


def test_default_max_loops_is_two_rewrite_rounds() -> None:
    settings = Settings(_env_file=None, app_env="test")
    llm = make_llm(rounds=[{0: "add_glossary"}])
    state = run(llm, settings)
    assert settings.agent_max_loops == 2
    assert state["loops"] == 2


def test_trace_contains_every_node(settings: Settings) -> None:
    llm = make_llm(rounds=[{0: "simplify"}, {}])
    state = run(llm, settings, LearningMode.EASYREAD)

    nodes = [step.node for step in state["trace"]]
    assert nodes == [
        "ingest",
        "router",
        "easyread_transform",
        "quiz",
        "checker",
        "easyread_transform",
        "quiz",
        "checker",
    ]
    assert all(step.ms >= 0 and step.note for step in state["trace"])
    assert "Chunk 0: simplify" in state["trace"][4].note


def test_empty_source_text_is_rejected(settings: Settings) -> None:
    graph = build_graph(make_llm(), settings)
    with pytest.raises(ValueError, match="empty"):
        graph.invoke({"source_text": "   ", "mode": LearningMode.FOCUS, "trace": []})


@pytest.mark.parametrize("mode", list(LearningMode))
def test_checker_sees_only_the_chosen_style_rules(mode: LearningMode, settings: Settings) -> None:
    llm = make_llm()
    run(llm, settings, mode)
    system = llm.calls_for(CheckerOutput)[0].system
    for other in LearningMode:
        assert (f"## {STYLE_NAMES[other]} style rules" in system) == (other == mode)
    assert "{style_rules}" not in system


def test_parallel_rewrites_keep_chunk_order(settings: Settings) -> None:
    llm = make_llm(rounds=[{0: "simplify", 1: "add_glossary"}, {}])
    state = run(llm, settings)

    assert llm.batch_sizes(ChunkDraft) == [2]
    assert [chunk.heading for chunk in state["chunks"]] == ["Rewritten 0", "Rewritten 1"]
    assert all(len(chunk.quiz) == 3 for chunk in state["chunks"])


def test_unverified_fix_fact_is_dropped_and_not_rewritten(settings: Settings) -> None:
    def checker(_: str) -> CheckerOutput:
        return CheckerOutput(
            suspect_judgments=[],
            reviews=[
                ChunkReview(
                    chunk_index=0,
                    action="fix_fact",
                    reason="Unsupported claim.",
                    quote="Plants are essential for life.",  # not in chunk 0
                )
            ],
        )

    llm = make_llm()
    llm.handlers[CheckerOutput] = checker
    state = run(llm, settings)

    assert state["loops"] == 0
    assert llm.calls_for(ChunkDraft) == []
    assert "dropped 1 unverified flag" in state["trace"][-1].note


def test_verified_missing_fact_is_rewritten_with_quote(settings: Settings) -> None:
    def checker(_: str) -> CheckerOutput:
        return CheckerOutput(
            suspect_judgments=[],
            reviews=[
                ChunkReview(
                    chunk_index=0,
                    action="missing_fact",
                    reason="Photosynthesis is not named.",
                    quote="This is called photosynthesis.",
                )
            ],
        )

    llm = make_llm()
    llm.handlers[CheckerOutput] = checker
    state = run(llm, settings)

    rewrites = llm.calls_for(ChunkDraft)
    assert len(rewrites) == 2  # flagged again each round until max loops (fake keeps flagging)
    assert "QUOTE: This is called photosynthesis." in rewrites[0].user
    assert state["loops"] == settings.agent_max_loops


# --- F5: simple Urdu (translation runs after the checker) ---


@pytest.mark.parametrize("mode", list(LearningMode))
def test_urdu_false_never_calls_translation(mode: LearningMode, settings: Settings) -> None:
    llm = make_llm()
    state = run(llm, settings, mode, urdu=False)
    lesson = build_lesson(state, student="Ali")

    assert llm.calls_for(ChunkTranslation) == []
    assert llm.calls_for(TitleTranslation) == []
    assert state["trace"][-1].node == "checker"
    assert lesson.urdu is False
    assert lesson.english is None


@pytest.mark.parametrize("mode", list(LearningMode))
def test_urdu_true_translates_after_the_checker(mode: LearningMode, settings: Settings) -> None:
    llm = make_llm(rounds=[{1: "simplify"}, {}])
    state = run(llm, settings, mode, urdu=True)
    lesson = build_lesson(state, student="Ali")

    nodes = [step.node for step in state["trace"]]
    assert nodes[-2:] == ["checker", "urdu"]
    assert nodes.count("urdu") == 1
    assert llm.batch_sizes(ChunkTranslation) == [2]  # every chunk, once, after the loop
    # The checker only ever saw English chunks.
    assert all(URDU not in call.user for call in llm.calls_for(CheckerOutput))
    assert lesson.urdu is True
    assert lesson.title == f"{URDU} Photosynthesis"
    assert [c.heading for c in lesson.chunks] == [f"{URDU} Food from light", f"{URDU} Rewritten 1"]
    assert lesson.english is not None
    assert lesson.english.title == "Photosynthesis"
    assert [c.heading for c in lesson.english.chunks] == ["Food from light", "Rewritten 1"]
    assert all(len(c.quiz) == 3 for c in lesson.chunks + lesson.english.chunks)


def test_urdu_runs_when_the_loop_limit_is_reached() -> None:
    settings = Settings(_env_file=None, app_env="test", agent_max_loops=1)
    llm = make_llm(rounds=[{0: "simplify"}])  # never approved
    state = run(llm, settings, urdu=True)

    assert state["loops"] == 1
    assert [s.node for s in state["trace"]][-2:] == ["checker", "urdu"]
    assert state["english"] is not None


def test_failed_translation_returns_english_lesson(settings: Settings) -> None:
    llm = make_llm()
    llm.handlers[ChunkTranslation] = lambda user: translate_chunk(user).model_copy(
        update={"quiz": []}
    )
    state = run(llm, settings, urdu=True)
    lesson = build_lesson(state, student="Ali")

    assert llm.batch_sizes(ChunkTranslation) == [2, 2]  # first try + one retry
    assert lesson.urdu is False
    assert lesson.english is None
    assert lesson.title == "Photosynthesis"
    assert all(len(c.quiz) == 3 for c in lesson.chunks)
    assert "showing English" in state["trace"][-1].note
