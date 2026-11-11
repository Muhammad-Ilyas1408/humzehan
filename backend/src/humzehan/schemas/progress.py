"""Quiz progress models."""

from pydantic import BaseModel, Field


class ProgressCreate(BaseModel):
    """A quiz score for one chunk of a lesson."""

    lesson_id: str
    chunk_index: int = Field(ge=0)
    score: int = Field(ge=0, le=3, description="Correct answers out of 3")
