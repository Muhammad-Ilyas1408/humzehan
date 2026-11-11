"""Repositories: the only code that writes SQL."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from humzehan.db.session import connect
from humzehan.schemas.dashboard import StudentSummary
from humzehan.schemas.lesson import Lesson


class _Repository:
    """Opens a short-lived connection per operation, so nothing is shared across threads."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with closing(connect(self._db_path)) as conn, conn:
            yield conn


class LessonRepository(_Repository):
    def save(self, lesson: Lesson) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO lessons (id, student, mode, title, payload, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    lesson.lesson_id,
                    lesson.student,
                    lesson.mode.value,
                    lesson.title,
                    lesson.model_dump_json(),
                    lesson.created_at.isoformat(),
                ),
            )

    def get(self, lesson_id: str) -> Lesson | None:
        with self._transaction() as conn:
            row = conn.execute("SELECT payload FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
        return None if row is None else Lesson.model_validate_json(row["payload"])


# Latest score per (lesson, chunk), then totals per student. Students with lessons but no
# scores still appear (LEFT JOIN), with chunks_completed 0 and average_score NULL.
_SUMMARY_SQL = """
WITH latest AS (
    SELECT lesson_id, chunk_index, score,
           ROW_NUMBER() OVER (PARTITION BY lesson_id, chunk_index ORDER BY id DESC) AS rn
    FROM progress
)
SELECT l.student                AS student,
       COUNT(DISTINCT l.id)     AS lessons,
       COUNT(latest.score)      AS chunks_completed,
       AVG(latest.score)        AS average_score
FROM lessons AS l
LEFT JOIN latest ON latest.lesson_id = l.id AND latest.rn = 1
GROUP BY l.student
ORDER BY l.student
"""


class ProgressRepository(_Repository):
    def record(self, lesson_id: str, chunk_index: int, score: int) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO progress (lesson_id, chunk_index, score, created_at) "
                "VALUES (?, ?, ?, ?)",
                (lesson_id, chunk_index, score, datetime.now(UTC).isoformat()),
            )

    def summary_by_student(self) -> list[StudentSummary]:
        with self._transaction() as conn:
            rows = conn.execute(_SUMMARY_SQL).fetchall()
        return [
            StudentSummary(
                student=row["student"],
                lessons=row["lessons"],
                chunks_completed=row["chunks_completed"],
                average_score=row["average_score"],
            )
            for row in rows
        ]
