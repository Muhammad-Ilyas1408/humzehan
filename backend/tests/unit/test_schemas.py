import pytest
from pydantic import ValidationError

from humzehan.schemas.lesson import Chunk, LearningMode, QuizItem


def test_quiz_item_valid() -> None:
    item = QuizItem(question="Q?", options=["a", "b", "c"], answer_index=2)
    assert item.options[item.answer_index] == "c"


@pytest.mark.parametrize("options", [["a", "b"], ["a", "b", "c", "d"]])
def test_quiz_item_needs_exactly_three_options(options: list[str]) -> None:
    with pytest.raises(ValidationError):
        QuizItem(question="Q?", options=options, answer_index=0)


@pytest.mark.parametrize("answer_index", [-1, 3])
def test_quiz_item_answer_index_in_range(answer_index: int) -> None:
    with pytest.raises(ValidationError):
        QuizItem(question="Q?", options=["a", "b", "c"], answer_index=answer_index)


def test_chunk_allows_at_most_three_questions() -> None:
    item = QuizItem(question="Q?", options=["a", "b", "c"], answer_index=0)
    with pytest.raises(ValidationError):
        Chunk(heading="h", body="b", quiz=[item] * 4)


def test_learning_mode_values() -> None:
    assert [m.value for m in LearningMode] == ["focus", "easyread", "literal"]
