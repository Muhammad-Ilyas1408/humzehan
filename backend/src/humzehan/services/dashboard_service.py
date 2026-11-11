"""Per-student totals for the dashboard."""

from humzehan.db.repositories import ProgressRepository
from humzehan.schemas.dashboard import DashboardSummary


class DashboardService:
    def __init__(self, progress: ProgressRepository) -> None:
        self._progress = progress

    def summary(self) -> DashboardSummary:
        """Lessons, distinct chunks scored and average of the latest score per chunk."""
        return DashboardSummary(students=self._progress.summary_by_student())
