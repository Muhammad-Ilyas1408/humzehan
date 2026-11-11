"""Create lessons with the agent and store them."""

import logging
from typing import cast

from humzehan.agents.graph import AgentGraph, build_lesson
from humzehan.agents.state import AgentState
from humzehan.core.exceptions import InvalidInputError, LLMFailureError, NotFoundError
from humzehan.db.repositories import LessonRepository
from humzehan.schemas.lesson import LearningMode, Lesson

logger = logging.getLogger(__name__)


class LessonService:
    def __init__(self, repo: LessonRepository, graph: AgentGraph, max_source_chars: int) -> None:
        self._repo = repo
        self._graph = graph
        self._max_source_chars = max_source_chars

    def create(self, student: str, mode: LearningMode, text: str) -> Lesson:
        """Run the agent on ``text`` and save the resulting lesson. Blocking: call from a thread."""
        student = student.strip()
        text = text.strip()
        if not student:
            raise InvalidInputError("Student name must not be empty.")
        if not text:
            raise InvalidInputError("Text must not be empty.")
        if len(text) > self._max_source_chars:
            raise InvalidInputError(
                f"Text is too long ({len(text)} characters; "
                f"the maximum is {self._max_source_chars})."
            )

        try:
            state = cast(
                AgentState,
                self._graph.invoke({"source_text": text, "mode": mode, "urdu": False, "trace": []}),
            )
        except Exception as exc:
            logger.exception("Agent failed to create a lesson (mode=%s)", mode.value)
            raise LLMFailureError("The AI service could not create the lesson.") from exc

        lesson = build_lesson(state, student=student)
        self._repo.save(lesson)
        return lesson

    def get(self, lesson_id: str) -> Lesson:
        lesson = self._repo.get(lesson_id)
        if lesson is None:
            raise NotFoundError(f"Lesson {lesson_id} not found.")
        return lesson
