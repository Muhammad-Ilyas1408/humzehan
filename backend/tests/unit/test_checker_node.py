"""Checker node: one call over the whole lesson, with the whole-lesson missing-fact rule."""

from fakes import FakeLLM
from humzehan.agents.nodes import make_checker_node
from humzehan.agents.state import AgentState, CheckerOutput, ChunkReview
from humzehan.schemas.lesson import Chunk, GlossaryItem, LearningMode

SOURCE = "Plants make food from sunlight. Leaves hold chlorophyll. Oxygen is released."
CHUNKS = [
    Chunk(heading="Food from light", body="Plants make **food** from sunlight."),
    Chunk(
        heading="Leaves",
        body="Leaves hold chlorophyll.",
        glossary=[GlossaryItem(term="chlorophyll", meaning="green pigment")],
    ),
    Chunk(heading="Oxygen", body="Oxygen is released."),
]


def approve_all(_: str) -> CheckerOutput:
    return CheckerOutput(
        suspect_judgments=[],
        reviews=[
            ChunkReview(chunk_index=i, action="approve", reason="ok", quote=None) for i in range(3)
        ],
    )


def run_checker(llm: FakeLLM) -> AgentState:
    state: AgentState = {
        "source_text": SOURCE,
        "mode": LearningMode.FOCUS,
        "chunks": CHUNKS,
        "trace": [],
    }
    return make_checker_node(llm)(state)


def test_checker_sees_every_chunk_in_one_call() -> None:
    llm = FakeLLM(handlers={CheckerOutput: approve_all})
    result = run_checker(llm)

    calls = llm.calls_for(CheckerOutput)
    assert len(calls) == 1
    user = calls[0].user
    assert SOURCE in user
    assert "all 3 chunks" in user
    for index, chunk in enumerate(CHUNKS):
        assert f"--- chunk {index} ---" in user
        assert chunk.heading in user
        assert chunk.body in user
    assert "chlorophyll: green pigment" in user
    assert [r.action for r in result["reviews"]] == ["approve"] * 3
    assert result["trace"][-1].note == "All 3 chunks approved; suspects: 0"


def test_checker_prompt_has_fact_and_whole_lesson_rules() -> None:
    llm = FakeLLM(handlers={CheckerOutput: approve_all})
    run_checker(llm)
    system = llm.calls_for(CheckerOutput)[0].system

    # fix_fact = added or changed facts, with the chunk sentence as evidence
    assert "states something that is NOT in the SOURCE" in system
    assert "changes a fact" in system
    assert "the exact sentence from the chunk that the SOURCE does not support" in system
    # missing_fact quotes the SOURCE sentence
    assert "`missing_fact`" in system
    assert "the exact SOURCE sentence" in system
    # missing facts are judged across the whole lesson
    assert "Each chunk covers only part of the SOURCE" in system
    assert "Never flag a chunk for leaving out a fact that another chunk already covers" in system
    assert "appears in no chunk at all" in system
    assert "where that fact fits best" in system
    assert "Flag each missing SOURCE sentence at most once" in system
    # the old per-chunk "drops a fact" rule is gone
    assert "drops a fact" not in system


def test_checker_normalizes_reviews_to_one_per_chunk() -> None:
    def messy(_: str) -> CheckerOutput:
        return CheckerOutput(
            suspect_judgments=[],
            reviews=[
                ChunkReview(
                    chunk_index=2,
                    action="fix_fact",
                    reason="Adds a fact.",
                    quote="Oxygen is released.",
                ),
                ChunkReview(chunk_index=2, action="approve", reason="duplicate", quote=None),
                ChunkReview(chunk_index=7, action="simplify", reason="out of range", quote=None),
                ChunkReview(
                    chunk_index=0,
                    action="fix_fact",
                    reason="Invented.",
                    quote="Plants are essential for life.",
                ),
            ],
        )

    result = run_checker(FakeLLM(handlers={CheckerOutput: messy}))
    assert [(r.chunk_index, r.action) for r in result["reviews"]] == [
        (0, "approve"),
        (1, "approve"),
        (2, "fix_fact"),
    ]
    note = result["trace"][-1].note
    assert 'Chunk 2: fix_fact (Adds a fact.) quote="Oxygen is released."' in note
    assert "dropped 2 unverified flags" in note
    assert "chunk 0 fix_fact: quoted sentence is not in the chunk" in note
