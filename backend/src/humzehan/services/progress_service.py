"""Record quiz scores."""

from humzehan.core.exceptions import InvalidInputError, NotFoundError
from humzehan.db.repositories import LessonRepository, ProgressRepository
from humzehan.schemas.progress import ProgressCreate


class ProgressService:
    def __init__(self, lessons: LessonRepository, progress: ProgressRepository) -> None:
        self._lessons = lessons
        self._progress = progress

    def record(self, progress: ProgressCreate) -> None:
        lesson = self._lessons.get(progress.lesson_id)
        if lesson is None:
            raise NotFoundError(f"Lesson {progress.lesson_id} not found.")
        if progress.chunk_index >= len(lesson.chunks):
            raise InvalidInputError(
                f"chunk_index {progress.chunk_index} is out of range "
                f"(the lesson has {len(lesson.chunks)} chunks)."
            )
        self._progress.record(progress.lesson_id, progress.chunk_index, progress.score)
