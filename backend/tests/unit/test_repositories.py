"""Repository tests on a temporary SQLite file."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from humzehan.db.repositories import LessonRepository, ProgressRepository
from humzehan.db.session import connect, init_db
from humzehan.schemas.dashboard import StudentSummary
from humzehan.schemas.lesson import (
    Chunk,
    EnglishVersion,
    GlossaryItem,
    LearningMode,
    Lesson,
    QuizItem,
    TraceStep,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "repo.db"
    init_db(path)
    return path


def make_lesson(lesson_id: str, student: str, chunks: int = 2) -> Lesson:
    quiz = QuizItem(question="Q?", options=["a", "b", "c"], answer_index=1)
    return Lesson(
        lesson_id=lesson_id,
        student=student,
        mode=LearningMode.FOCUS,
        urdu=False,
        title=f"Lesson {lesson_id}",
        chunks=[
            Chunk(
                heading=f"Chunk {i}",
                body="**Body**",
                hook="Why it matters",
                glossary=[GlossaryItem(term="t", meaning="m")],
                quiz=[quiz, quiz, quiz],
            )
            for i in range(chunks)
        ],
        trace=[TraceStep(node="ingest", note="Received text", ms=3)],
        created_at=datetime(2026, 11, 11, 9, 30, tzinfo=UTC),
    )


def test_lesson_round_trip(db_path: Path) -> None:
    repo = LessonRepository(db_path)
    lesson = make_lesson("l1", "Ali")

    repo.save(lesson)

    assert repo.get("l1") == lesson


def test_urdu_lesson_round_trip_keeps_english(db_path: Path) -> None:
    repo = LessonRepository(db_path)
    english = make_lesson("en", "Ali")
    lesson = make_lesson("l1", "Ali").model_copy(
        update={
            "urdu": True,
            "title": "ضیائی تالیف (photosynthesis)",
            "english": EnglishVersion(title=english.title, chunks=english.chunks),
        }
    )

    repo.save(lesson)

    assert repo.get("l1") == lesson


def test_old_payload_without_english_still_loads(db_path: Path) -> None:
    lesson = make_lesson("l1", "Ali")
    LessonRepository(db_path).save(lesson)
    old_payload = lesson.model_dump_json(exclude={"english"})  # stored before F5
    with closing(connect(db_path)) as conn, conn:
        conn.execute("UPDATE lessons SET payload = ? WHERE id = 'l1'", (old_payload,))

    loaded = LessonRepository(db_path).get("l1")

    assert loaded is not None
    assert loaded.english is None


def test_lesson_columns_are_filled(db_path: Path) -> None:
    LessonRepository(db_path).save(make_lesson("l1", "Ali"))

    with closing(connect(db_path)) as conn:
        row = conn.execute("SELECT student, mode, title, created_at FROM lessons").fetchone()
    assert tuple(row) == ("Ali", "focus", "Lesson l1", "2026-11-11T09:30:00+00:00")


def test_get_unknown_lesson_returns_none(db_path: Path) -> None:
    assert LessonRepository(db_path).get("missing") is None


def test_init_db_is_idempotent(db_path: Path) -> None:
    LessonRepository(db_path).save(make_lesson("l1", "Ali"))

    init_db(db_path)

    assert LessonRepository(db_path).get("l1") is not None


def test_progress_requires_existing_lesson(db_path: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        ProgressRepository(db_path).record("missing", 0, 1)


def test_summary_uses_latest_score_per_chunk(db_path: Path) -> None:
    lessons = LessonRepository(db_path)
    progress = ProgressRepository(db_path)
    lessons.save(make_lesson("a1", "Ali"))
    lessons.save(make_lesson("a2", "Ali"))
    lessons.save(make_lesson("b1", "Bilal"))
    progress.record("a1", 0, 0)
    progress.record("a1", 0, 3)  # replaces the 0
    progress.record("a1", 1, 1)
    progress.record("a2", 1, 2)

    summary = progress.summary_by_student()

    assert summary == [
        StudentSummary(student="Ali", lessons=2, chunks_completed=3, average_score=2.0),
        StudentSummary(student="Bilal", lessons=1, chunks_completed=0, average_score=None),
    ]


def test_summary_is_empty_without_lessons(db_path: Path) -> None:
    assert ProgressRepository(db_path).summary_by_student() == []
