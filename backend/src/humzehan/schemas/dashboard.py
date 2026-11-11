"""Dashboard models: per-student totals."""

from pydantic import BaseModel


class StudentSummary(BaseModel):
    student: str
    lessons: int
    chunks_completed: int
    average_score: float | None


class DashboardSummary(BaseModel):
    students: list[StudentSummary]
