"""Urdu node: bold key terms must appear in English (in brackets) in the Urdu chunk.

A chunk missing a term is retried once and then accepted either way (no English fallback).
"""

from collections.abc import Callable

from pydantic import BaseModel

from fakes import URDU, FakeLLM, english_chunk_in, translate_chunk, translate_title
from humzehan.agents.nodes import make_urdu_node
from humzehan.agents.nodes.urdu import key_terms, missing_terms
from humzehan.agents.state import AgentState, ChunkTranslation, TitleTranslation
from humzehan.schemas.lesson import Chunk, GlossaryItem, LearningMode, QuizItem

QUIZ = [QuizItem(question="Q?", options=["a", "b", "c"], answer_index=1)] * 3

FORCE_CHUNK = Chunk(
    heading="Laws of motion",
    body="A **force** changes motion. Newton described **classical mechanics** in 1687.",
    quiz=QUIZ,
)
PLAIN_CHUNK = Chunk(heading="Leaves", body="Leaves hold chlorophyll.", quiz=QUIZ)


def urdu_chunk(body: str, **update: object) -> ChunkTranslation:
    base = ChunkTranslation(heading="حرکت کے قوانین", body=body, hook=None, glossary=[], quiz=QUIZ)
    return base.model_copy(update=update)


# --- key_terms ---


def test_key_terms_are_the_bold_terms_in_order() -> None:
    assert key_terms(FORCE_CHUNK) == ["force", "classical mechanics"]


def test_key_terms_skip_literal_section_labels_and_duplicates() -> None:
    chunk = Chunk(
        heading="Force",
        body="**What it is**\nA **Force** is a push.\n\n**How it works:**\nA **force** acts.",
        quiz=QUIZ,
    )
    assert key_terms(chunk) == ["Force"]


def test_key_terms_include_the_hook_and_ignore_non_latin_bold() -> None:
    chunk = Chunk(
        heading="h", body="It is **F = ma** and **۱۲**.", hook="A **force** acts.", quiz=QUIZ
    )
    assert key_terms(chunk) == ["force", "F = ma"]


def test_key_terms_empty_without_bold() -> None:
    assert key_terms(PLAIN_CHUNK) == []


# --- missing_terms ---


def test_no_terms_missing_when_each_is_in_brackets() -> None:
    urdu = urdu_chunk("**قوت (force)** حرکت بدلتی ہے کلاسیکی میکانکس (Classical  Mechanics)")
    assert missing_terms(["force", "classical mechanics"], urdu) == []


def test_missing_terms_are_reported_in_order() -> None:
    urdu = urdu_chunk("قوت حرکت بدلتی ہے کلاسیکی میکانکس")
    assert missing_terms(["force", "classical mechanics"], urdu) == ["force", "classical mechanics"]


def test_plural_term_matches_its_singular_and_glossary_counts() -> None:
    urdu = urdu_chunk(
        "قوتیں حرکت بدلتی ہیں",
        glossary=[GlossaryItem(term="قوت (force)", meaning="دھکا یا کھنچاؤ")],
    )
    assert missing_terms(["forces"], urdu) == []


# --- the node: retry once, then accept ---


def make_state(chunks: list[Chunk]) -> AgentState:
    return {
        "mode": LearningMode.FOCUS,
        "urdu": True,
        "title": "Motion",
        "chunks": chunks,
        "trace": [],
    }


def drops_english(times: int) -> tuple[Callable[[str], BaseModel], list[str]]:
    """A translator that leaves out every English bold term for the force chunk ``times`` times.
    Also returns the list of prompts it received for that chunk."""
    seen: list[str] = []

    def respond(user: str) -> BaseModel:
        good = translate_chunk(user)
        if english_chunk_in(user).heading != FORCE_CHUNK.heading:
            return good
        seen.append(user)
        if len(seen) <= times:
            return good.model_copy(update={"body": f"{URDU} قوت حرکت بدلتی ہے"})
        return good

    return respond, seen


def make_llm(handler: Callable[[str], BaseModel]) -> FakeLLM:
    return FakeLLM(handlers={ChunkTranslation: handler, TitleTranslation: translate_title})


def test_prompt_lists_the_key_terms() -> None:
    llm = make_llm(translate_chunk)

    make_urdu_node(llm)(make_state([FORCE_CHUNK, PLAIN_CHUNK]))

    users = [c.user for c in llm.calls_for(ChunkTranslation)]
    assert "KEY TERMS" in users[0] and "force, classical mechanics" in users[0]
    assert "KEY TERMS" not in users[1]  # no bold terms, no list


def test_missing_terms_are_retried_once_with_a_hint() -> None:
    handler, seen = drops_english(times=1)
    llm = make_llm(handler)

    result = make_urdu_node(llm)(make_state([FORCE_CHUNK, PLAIN_CHUNK]))

    assert llm.batch_sizes(ChunkTranslation) == [2, 1]  # only the force chunk is retried
    assert "left out the English for: force, classical mechanics" in seen[1]
    assert result["english"] is not None
    assert "**force**" in result["chunks"][0].body  # the retry kept the English terms
    note = result["trace"][0].note
    assert "retried: 1" in note and "still missing" not in note


def test_terms_still_missing_after_retry_are_accepted() -> None:
    handler, _ = drops_english(times=2)
    llm = make_llm(handler)

    result = make_urdu_node(llm)(make_state([FORCE_CHUNK, PLAIN_CHUNK]))

    assert llm.batch_sizes(ChunkTranslation) == [2, 1]  # one retry only
    assert result["english"] is not None  # no English fallback for missing terms
    assert result["chunks"][0].body == f"{URDU} قوت حرکت بدلتی ہے"
    assert "English terms still missing (chunk 0: force, classical mechanics)" in (
        result["trace"][0].note
    )


def test_invalid_retry_keeps_the_valid_first_translation() -> None:
    calls = {"n": 0}

    def respond(user: str) -> BaseModel:
        calls["n"] += 1
        good = translate_chunk(user)
        if calls["n"] == 1:
            return good.model_copy(update={"body": "قوت"})  # valid, but terms missing
        return good.model_copy(update={"quiz": good.quiz[:2]})  # retry breaks the structure

    llm = make_llm(respond)

    result = make_urdu_node(llm)(make_state([FORCE_CHUNK]))

    assert llm.batch_sizes(ChunkTranslation) == [1, 1]
    assert result["english"] is not None
    assert result["chunks"][0].body == "قوت"
    assert len(result["chunks"][0].quiz) == 3
    assert "still missing" in result["trace"][0].note
