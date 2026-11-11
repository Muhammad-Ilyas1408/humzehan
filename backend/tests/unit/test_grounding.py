"""Deterministic grounding pre-check and how suspect judgments become fix_fact flags."""

import pytest

from fakes import FakeLLM
from humzehan.agents.nodes import make_checker_node
from humzehan.agents.state import AgentState, CheckerOutput, ChunkReview, SuspectJudgment
from humzehan.agents.verification import (
    GROUNDING_THRESHOLD,
    SuspectSentence,
    apply_suspect_judgments,
    content_words,
    find_suspect_sentences,
    grounding_share,
    split_sentences,
    stem,
)
from humzehan.schemas.lesson import Chunk, GlossaryItem, LearningMode

# Sample-like source text (same style as backend/sample.txt).
SOURCE = (
    "The water cycle, also known as the hydrological cycle, describes the continuous movement "
    "of water between the Earth's surface and the atmosphere, a process driven primarily by "
    "solar energy and gravity. When the sun heats oceans, rivers and lakes, water molecules "
    "gain sufficient energy to escape into the air as water vapour, a process called "
    "evaporation. Some of this water flows over the land as surface runoff into streams and "
    "rivers, while the rest seeps into the soil through infiltration and is stored "
    "underground as groundwater."
)
SOURCE_WORDS = content_words(SOURCE)


# --- grounding share -----------------------------------------------------------------


def test_unsupported_importance_claim_is_suspect() -> None:
    sentence = "The cycle is continuous and important for life."
    assert grounding_share(sentence, SOURCE_WORDS) < GROUNDING_THRESHOLD


def test_invented_conclusion_from_real_run_is_suspect() -> None:
    sentence = "This continuous process is essential for maintaining the Earth's water supply."
    assert grounding_share(sentence, SOURCE_WORDS) < GROUNDING_THRESHOLD


@pytest.mark.parametrize(
    "sentence",
    [
        "Solar energy and gravity drive the water cycle.",
        "The sun heats oceans, rivers and lakes.",
        "Water molecules escape into the air as water vapour.",
        "Some water seeps into the soil and is stored as groundwater.",
    ],
)
def test_plain_paraphrase_is_not_suspect(sentence: str) -> None:
    assert grounding_share(sentence, SOURCE_WORDS) >= GROUNDING_THRESHOLD


def test_stemming_matches_simple_word_forms() -> None:
    assert stem("rivers") == stem("river")
    assert stem("driven") == stem("drive")
    assert stem("evaporation") == stem("evaporates")
    assert stem("process") == stem("processes")
    assert stem("supply") == "supply"


def test_split_sentences_skips_subheadings_and_bullets() -> None:
    body = (
        "**What it is**  \nThe water cycle moves water. It is driven by the sun!\n"
        "**How it works**\n- Water evaporates.\n## Heading line"
    )
    assert split_sentences(body) == [
        "The water cycle moves water.",
        "It is driven by the sun!",
        "Water evaporates.",
    ]


def test_find_suspects_checks_hook_and_body_but_not_glossary() -> None:
    chunks = [
        Chunk(
            heading="Overview",
            hook="This is the most important cycle for life on Earth.",
            body="Solar energy and gravity drive the water cycle.",
            glossary=[GlossaryItem(term="ocean", meaning="A huge body of salty water.")],
        ),
        Chunk(
            heading="Groundwater",
            body="Water seeps into the soil. The cycle is continuous and important for life.",
        ),
    ]
    suspects = find_suspect_sentences(chunks, SOURCE)
    assert [(s.chunk_index, s.sentence) for s in suspects] == [
        (0, "This is the most important cycle for life on Earth."),
        (1, "The cycle is continuous and important for life."),
    ]
    assert all(0 <= s.share < GROUNDING_THRESHOLD for s in suspects)


# --- applying the checker's judgments ------------------------------------------------


def approve(index: int) -> ChunkReview:
    return ChunkReview(chunk_index=index, action="approve", reason="ok", quote=None)


SUSPECTS = [
    SuspectSentence(0, "It is vital for all life.", 0.2),
    SuspectSentence(1, "Oceans provide most vapour.", 0.5),
    SuspectSentence(1, "This keeps Earth healthy.", 0.0),
]


def test_confirmed_suspects_become_fix_fact_with_sentence_as_quote() -> None:
    reviews = [
        approve(0),
        ChunkReview(chunk_index=1, action="simplify", reason="Too long.", quote=None),
    ]
    judgments = [
        SuspectJudgment(suspect_id=0, supported=False, reason="Source says nothing about life."),
        SuspectJudgment(suspect_id=1, supported=True, reason="Paraphrase."),
        SuspectJudgment(suspect_id=2, supported=False, reason="Not in source."),
    ]
    outcome = apply_suspect_judgments(reviews, SUSPECTS, judgments)

    assert [(r.chunk_index, r.action, r.quote) for r in outcome.reviews] == [
        (0, "fix_fact", "It is vital for all life."),
        (1, "fix_fact", "This keeps Earth healthy."),  # replaces the lower-priority simplify
    ]
    assert (
        outcome.reviews[0].reason == "Not supported by the SOURCE: Source says nothing about life."
    )
    assert outcome.supported == [SUSPECTS[1]]
    assert outcome.unsupported == [SUSPECTS[0], SUSPECTS[2]]
    assert outcome.unjudged == []


def test_supported_and_unjudged_suspects_change_nothing() -> None:
    reviews = [approve(0), approve(1)]
    judgments = [
        SuspectJudgment(suspect_id=1, supported=True, reason="ok"),
        SuspectJudgment(suspect_id=9, supported=False, reason="bad id is ignored"),
    ]
    outcome = apply_suspect_judgments(reviews, SUSPECTS, judgments)
    assert outcome.reviews == reviews
    assert outcome.unjudged == [SUSPECTS[0], SUSPECTS[2]]


def test_confirmed_suspect_merges_into_existing_fix_fact() -> None:
    reviews = [
        ChunkReview(chunk_index=0, action="fix_fact", reason="Wrong.", quote="Rain is green."),
        approve(1),
    ]
    judgments = [SuspectJudgment(suspect_id=0, supported=False, reason="Not in source.")]
    outcome = apply_suspect_judgments(reviews, SUSPECTS, judgments)
    assert outcome.reviews[0].quote == "Rain is green.\nIt is vital for all life."


# --- checker node end to end with the fake LLM --------------------------------------


def test_checker_passes_suspects_and_turns_confirmed_ones_into_fix_fact() -> None:
    chunks = [
        Chunk(heading="Drivers", body="Solar energy and gravity drive the water cycle."),
        Chunk(
            heading="Groundwater",
            body="Water is stored as groundwater. The cycle is continuous and important for life.",
        ),
    ]

    def checker(_: str) -> CheckerOutput:
        return CheckerOutput(
            reviews=[approve(0), approve(1)],
            suspect_judgments=[
                SuspectJudgment(suspect_id=0, supported=False, reason="No importance in source.")
            ],
        )

    llm = FakeLLM(handlers={CheckerOutput: checker})
    state: AgentState = {
        "source_text": SOURCE,
        "mode": LearningMode.FOCUS,
        "chunks": chunks,
        "trace": [],
    }
    result = make_checker_node(llm)(state)

    call = llm.calls_for(CheckerOutput)[0]
    assert "SUSPECT SENTENCES" in call.user
    assert '[0] chunk 1: "The cycle is continuous and important for life."' in call.user
    assert "Judge every one in" in call.system
    assert [(r.chunk_index, r.action) for r in result["reviews"]] == [
        (0, "approve"),
        (1, "fix_fact"),
    ]
    assert result["reviews"][1].quote == "The cycle is continuous and important for life."
    assert "suspects: 1 (1 unsupported, 0 supported)" in result["trace"][-1].note
