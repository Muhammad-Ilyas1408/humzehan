"""Quiz node: questions for all chunks that need them, generated in one parallel batch."""

from fakes import FakeLLM
from humzehan.agents.nodes import make_quiz_node
from humzehan.agents.state import AgentState, QuizSet
from humzehan.schemas.lesson import Chunk, LearningMode, QuizItem


def quiz_for(user: str) -> QuizSet:
    """Each question names the chunk heading it was asked about, to check order."""
    heading = user.split("## ", 1)[1].split("\n", 1)[0]
    item = QuizItem(question=f"About {heading}?", options=["a", "b", "c"], answer_index=1)
    return QuizSet(questions=[item, item, item])


def test_quiz_node_fills_every_chunk_in_order() -> None:
    existing = QuizItem(question="Kept?", options=["x", "y", "z"], answer_index=0)
    chunks = [
        Chunk(heading="A", body="a"),
        Chunk(heading="B", body="b", quiz=[existing] * 3),
        Chunk(heading="C", body="c"),
        Chunk(heading="D", body="d"),
    ]
    llm = FakeLLM(handlers={QuizSet: quiz_for})
    state: AgentState = {"mode": LearningMode.FOCUS, "chunks": chunks, "trace": []}

    result = make_quiz_node(llm)(state)

    assert all(len(chunk.quiz) == 3 for chunk in result["chunks"])
    assert [chunk.quiz[0].question for chunk in result["chunks"]] == [
        "About A?",
        "Kept?",
        "About C?",
        "About D?",
    ]
    assert llm.batch_sizes(QuizSet) == [3]  # one parallel batch, existing quiz untouched
    assert [step.node for step in result["trace"]] == ["quiz"]
    assert "0, 2, 3" in result["trace"][0].note


def test_quiz_node_makes_no_calls_when_all_chunks_have_quizzes() -> None:
    existing = QuizItem(question="Kept?", options=["x", "y", "z"], answer_index=0)
    llm = FakeLLM(handlers={QuizSet: quiz_for})
    state: AgentState = {"chunks": [Chunk(heading="A", body="a", quiz=[existing] * 3)], "trace": []}

    result = make_quiz_node(llm)(state)

    assert llm.calls == []
    assert result["chunks"][0].quiz[0].question == "Kept?"
