"""Urdu node: batched translation, structure validation, one retry, English fallback."""

from collections.abc import Callable

import pytest
from pydantic import BaseModel

from fakes import URDU, FakeLLM, english_chunk_in, translate_chunk, translate_title
from humzehan.agents.nodes import make_urdu_node
from humzehan.agents.nodes.urdu import validate_translation
from humzehan.agents.state import AgentState, ChunkTranslation, TitleTranslation
from humzehan.schemas.lesson import Chunk, GlossaryItem, LearningMode, QuizItem

QUIZ = [
    QuizItem(question="What do plants make?", options=["Food", "Rocks", "Air"], answer_index=0),
    QuizItem(question="Where is chlorophyll?", options=["Roots", "Leaves", "Soil"], answer_index=1),
    QuizItem(question="What is F = ma?", options=["A law", "A leaf", "A year"], answer_index=2),
]


def make_chunks() -> list[Chunk]:
    return [
        Chunk(
            heading="Food from light",
            body="Plants make **food**.",
            hook="Plants make food.",
            glossary=[GlossaryItem(term="photosynthesis", meaning="making food from light")],
            quiz=QUIZ,
        ),
        Chunk(heading="Leaves", body="Leaves hold chlorophyll.", quiz=QUIZ),
        Chunk(heading="Newton", body="F = ma was published in 1687.", quiz=QUIZ),
    ]


def make_state(mode: LearningMode = LearningMode.EASYREAD) -> AgentState:
    return {
        "mode": mode,
        "urdu": True,
        "title": "Photosynthesis",
        "chunks": make_chunks(),
        "trace": [],
    }


def make_llm(chunk_handler: Callable[[str], BaseModel] = translate_chunk) -> FakeLLM:
    return FakeLLM(handlers={ChunkTranslation: chunk_handler, TitleTranslation: translate_title})


def broken_on(
    heading: str, times: int, breaker: Callable[[ChunkTranslation], ChunkTranslation]
) -> Callable[[str], BaseModel]:
    """A handler that breaks the translation of the chunk ``heading`` the first ``times`` calls."""
    calls = {"n": 0}

    def respond(user: str) -> BaseModel:
        good = translate_chunk(user)
        if english_chunk_in(user).heading == heading and calls["n"] < times:
            calls["n"] += 1
            return breaker(good)
        return good

    return respond


def drop_glossary(t: ChunkTranslation) -> ChunkTranslation:
    return t.model_copy(update={"glossary": []})


def drop_question(t: ChunkTranslation) -> ChunkTranslation:
    return t.model_copy(update={"quiz": t.quiz[:2]})


def change_answer(t: ChunkTranslation) -> ChunkTranslation:
    first = t.quiz[0].model_copy(update={"answer_index": (t.quiz[0].answer_index + 1) % 3})
    return t.model_copy(update={"quiz": [first, *t.quiz[1:]]})


def test_translates_every_chunk_in_one_batch_and_keeps_english() -> None:
    llm = make_llm()
    state = make_state()

    result = make_urdu_node(llm)(state)

    assert llm.batch_sizes(ChunkTranslation) == [3]
    assert len(llm.calls_for(TitleTranslation)) == 1
    assert result["title"] == f"{URDU} Photosynthesis"
    assert [c.heading for c in result["chunks"]] == [f"{URDU} {c.heading}" for c in make_chunks()]
    assert result["chunks"][0].hook == f"{URDU} Plants make food."
    assert result["chunks"][1].hook is None
    assert [q.answer_index for q in result["chunks"][0].quiz] == [0, 1, 2]
    english = result["english"]
    assert english is not None
    assert english.title == "Photosynthesis"
    assert english.chunks == make_chunks()
    assert [s.node for s in result["trace"]] == ["urdu"]
    assert "Translated 3 chunks to Urdu (retried: 0)" in result["trace"][0].note


@pytest.mark.parametrize(
    ("mode", "section"),
    [
        (LearningMode.FOCUS, "## Focus style"),
        (LearningMode.EASYREAD, "## Easy-read style"),
        (LearningMode.LITERAL, "## Literal style"),
    ],
)
def test_prompt_has_only_the_chosen_style_and_the_rules(mode: LearningMode, section: str) -> None:
    llm = make_llm()

    make_urdu_node(llm)(make_state(mode))

    call = llm.calls_for(ChunkTranslation)[0]
    sections = ["## Focus style", "## Easy-read style", "## Literal style"]
    assert [s in call.user for s in sections] == [s == section for s in sections]
    assert "never add, drop or change" in call.system.lower()
    assert "(evaporation)" in call.system
    assert "**یہ کیا ہے**" in call.system
    assert '"answer_index": 0' in call.user  # the English quiz is sent with its answers


@pytest.mark.parametrize("breaker", [drop_glossary, drop_question, change_answer])
def test_invalid_chunk_is_retried_once_and_then_accepted(
    breaker: Callable[[ChunkTranslation], ChunkTranslation],
) -> None:
    llm = make_llm(broken_on("Food from light", times=1, breaker=breaker))

    result = make_urdu_node(llm)(make_state())

    assert llm.batch_sizes(ChunkTranslation) == [3, 1]  # only the broken chunk is retried
    assert result["english"] is not None
    assert result["chunks"][0].heading == f"{URDU} Food from light"
    assert len(result["chunks"][0].glossary) == 1
    assert [q.answer_index for q in result["chunks"][0].quiz] == [0, 1, 2]
    assert "retried: 1" in result["trace"][0].note


@pytest.mark.parametrize(
    ("breaker", "reason"),
    [
        (drop_glossary, "glossary has 0 items, expected 1"),
        (drop_question, "quiz has 2 questions, expected 3"),
        (change_answer, "question 1: answer_index changed"),
    ],
)
def test_chunk_failing_twice_falls_back_to_english(
    breaker: Callable[[ChunkTranslation], ChunkTranslation], reason: str
) -> None:
    llm = make_llm(broken_on("Food from light", times=2, breaker=breaker))
    state = make_state()

    result = make_urdu_node(llm)(state)

    assert llm.batch_sizes(ChunkTranslation) == [3, 1]
    assert result["english"] is None
    assert "chunks" not in result and "title" not in result  # the English lesson is kept
    note = result["trace"][0].note
    assert "chunk 0" in note and reason in note and "showing English" in note


def test_provider_error_or_invalid_output_counts_as_a_failed_chunk() -> None:
    def fail(_: str) -> BaseModel:
        raise RuntimeError("provider down")

    llm = make_llm(fail)

    result = make_urdu_node(llm)(make_state())

    assert llm.batch_sizes(ChunkTranslation) == [3, 3]
    assert result["english"] is None
    assert "invalid output (RuntimeError)" in result["trace"][0].note


def test_empty_title_falls_back_to_english() -> None:
    llm = make_llm()
    llm.handlers[TitleTranslation] = lambda _: TitleTranslation(title="  ")

    result = make_urdu_node(llm)(make_state())

    assert result["english"] is None
    assert "title" in result["trace"][0].note


def translation_of(chunk: Chunk) -> ChunkTranslation:
    return ChunkTranslation(
        heading="h", body="b", hook=chunk.hook, glossary=chunk.glossary, quiz=chunk.quiz
    )


def test_validate_translation_accepts_same_structure() -> None:
    chunk = make_chunks()[0]
    assert validate_translation(chunk, translation_of(chunk)) == []


def test_validate_translation_reports_every_problem() -> None:
    chunk = make_chunks()[0]
    bad = translation_of(chunk).model_copy(
        update={
            "hook": None,
            "glossary": [],
            "quiz": [QUIZ[0].model_copy(update={"answer_index": 2}), QUIZ[1], QUIZ[2]],
        }
    )
    assert validate_translation(chunk, bad) == [
        "hook missing",
        "glossary has 0 items, expected 1",
        "question 1: answer_index changed",
    ]


def test_validate_translation_rejects_added_hook_and_empty_text() -> None:
    chunk = make_chunks()[1]  # no hook
    bad = translation_of(chunk).model_copy(update={"hook": "extra", "body": "  "})
    assert validate_translation(chunk, bad) == ["hook added", "empty text"]
