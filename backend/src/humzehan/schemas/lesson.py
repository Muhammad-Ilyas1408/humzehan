"""Lesson data models: the contract between the agent, the API and the frontend."""

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class LearningMode(StrEnum):
    """The learning style the student chooses."""

    FOCUS = "focus"
    EASYREAD = "easyread"
    LITERAL = "literal"


class GlossaryItem(BaseModel):
    term: str
    meaning: str


class QuizItem(BaseModel):
    question: str
    options: list[str] = Field(min_length=3, max_length=3)
    answer_index: int = Field(description="0-based index into options")

    @model_validator(mode="after")
    def _answer_in_range(self) -> Self:
        if not 0 <= self.answer_index < len(self.options):
            raise ValueError(
                f"answer_index {self.answer_index} is out of range for {len(self.options)} options"
            )
        return self


class Chunk(BaseModel):
    heading: str
    body: str = Field(description="Markdown")
    hook: str | None = Field(default=None, description='Focus mode: "why this matters"')
    glossary: list[GlossaryItem] = Field(default_factory=list)
    quiz: list[QuizItem] = Field(default_factory=list, max_length=3)


class TraceStep(BaseModel):
    node: str
    note: str
    ms: int = Field(ge=0)


class Lesson(BaseModel):
    lesson_id: str
    student: str
    mode: LearningMode
    urdu: bool
    title: str
    chunks: list[Chunk]
    trace: list[TraceStep]
    created_at: datetime
