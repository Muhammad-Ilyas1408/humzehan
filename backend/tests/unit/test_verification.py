"""verify_reviews: keep only checker flags whose evidence holds up."""

from humzehan.agents.state import CheckerAction, ChunkReview
from humzehan.agents.verification import contains_quote, is_covered, verify_reviews
from humzehan.schemas.lesson import Chunk, GlossaryItem

SOURCE = (
    "The water cycle is driven primarily by solar energy and gravity. "
    "Water evaporates from oceans, rivers and lakes. "
    "Some water seeps into the soil through infiltration and is stored as groundwater."
)
CHUNKS = [
    Chunk(
        heading="What the water cycle is",
        hook="The sun powers it.",
        body="The water cycle is driven mainly by **solar energy** and gravity.",
    ),
    Chunk(
        heading="Evaporation",
        body="Water *evaporates* from oceans, rivers and lakes. It is essential for all life.",
        glossary=[GlossaryItem(term="evaporation", meaning="water turning into vapour")],
    ),
]


def review(index: int, action: CheckerAction, quote: str | None, reason: str = "r") -> ChunkReview:
    return ChunkReview(chunk_index=index, action=action, reason=reason, quote=quote)


def actions(reviews: list[ChunkReview]) -> list[tuple[int, str]]:
    return [(r.chunk_index, r.action) for r in reviews]


# --- fix_fact ---


def test_fix_fact_quote_not_in_chunk_is_dropped() -> None:
    # The sentence exists, but in chunk 1, not chunk 0.
    result = verify_reviews(
        [review(0, "fix_fact", "It is essential for all life.")], CHUNKS, SOURCE
    )
    assert actions(result.reviews) == [(0, "approve"), (1, "approve")]
    assert [d.why for d in result.dropped] == ["quoted sentence is not in the chunk"]


def test_fix_fact_real_quote_is_kept() -> None:
    result = verify_reviews(
        [review(1, "fix_fact", "It is essential for all life.")], CHUNKS, SOURCE
    )
    assert actions(result.reviews) == [(0, "approve"), (1, "fix_fact")]
    assert result.dropped == []


def test_fix_fact_quote_matches_despite_markdown_case_and_spacing() -> None:
    quote = '"water   EVAPORATES from oceans, rivers and lakes"'
    result = verify_reviews([review(1, "fix_fact", quote)], CHUNKS, SOURCE)
    assert actions(result.reviews)[1] == (1, "fix_fact")


def test_fix_fact_without_quote_is_dropped() -> None:
    result = verify_reviews([review(1, "fix_fact", None)], CHUNKS, SOURCE)
    assert actions(result.reviews)[1] == (1, "approve")
    assert len(result.dropped) == 1


# --- missing_fact ---


def test_missing_fact_already_covered_elsewhere_is_dropped() -> None:
    # Flagged on chunk 1, but chunk 0 already says it (in slightly different words).
    quote = "The water cycle is driven primarily by solar energy and gravity."
    result = verify_reviews([review(1, "missing_fact", quote)], CHUNKS, SOURCE)
    assert actions(result.reviews) == [(0, "approve"), (1, "approve")]
    assert [d.why for d in result.dropped] == ["fact is already covered in the lesson"]


def test_missing_fact_really_missing_is_kept() -> None:
    quote = "Some water seeps into the soil through infiltration and is stored as groundwater."
    result = verify_reviews([review(1, "missing_fact", quote)], CHUNKS, SOURCE)
    assert actions(result.reviews) == [(0, "approve"), (1, "missing_fact")]
    assert result.dropped == []


def test_missing_fact_not_in_source_is_dropped() -> None:
    quote = "Clouds are made of cotton candy and rainbows."
    result = verify_reviews([review(0, "missing_fact", quote)], CHUNKS, SOURCE)
    assert actions(result.reviews)[0] == (0, "approve")
    assert [d.why for d in result.dropped] == ["quoted sentence is not in the SOURCE"]


def test_only_one_missing_fact_flag_per_source_sentence() -> None:
    quote = "stored as groundwater"
    result = verify_reviews(
        [review(0, "missing_fact", quote), review(1, "missing_fact", quote)], CHUNKS, SOURCE
    )
    assert actions(result.reviews) == [(0, "missing_fact"), (1, "approve")]
    assert [d.why for d in result.dropped] == ["same missing fact already flagged"]


# --- other actions and normalisation ---


def test_simplify_and_add_glossary_keep_their_reason() -> None:
    reviews = [
        review(0, "simplify", None, reason="Sentence 1 has 14 words."),
        review(1, "add_glossary", None, reason="Explain 'vapour'."),
    ]
    result = verify_reviews(reviews, CHUNKS, SOURCE)
    assert actions(result.reviews) == [(0, "simplify"), (1, "add_glossary")]
    assert result.reviews[0].reason == "Sentence 1 has 14 words."


def test_simplify_without_reason_is_dropped() -> None:
    result = verify_reviews([review(0, "simplify", None, reason="  ")], CHUNKS, SOURCE)
    assert actions(result.reviews)[0] == (0, "approve")
    assert len(result.dropped) == 1


def test_invalid_index_and_duplicates_are_dropped_missing_chunks_approved() -> None:
    reviews = [
        review(5, "simplify", None),
        review(1, "simplify", None, reason="first"),
        review(1, "add_glossary", None, reason="second"),
    ]
    result = verify_reviews(reviews, CHUNKS, SOURCE)
    assert actions(result.reviews) == [(0, "approve"), (1, "simplify")]
    assert result.reviews[1].reason == "first"
    assert len(result.dropped) == 2


def test_helpers() -> None:
    assert contains_quote("Water **evaporates** fast.", "water evaporates fast.")
    assert not contains_quote("Water evaporates.", "")
    assert is_covered("Driven by solar energy and gravity.", "solar energy and gravity drive it")
    assert not is_covered("Stored underground as groundwater.", "The sun heats the oceans.")
