"""Lesson routes: create a lesson from text, fetch a saved lesson."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, status
from starlette.concurrency import run_in_threadpool

from humzehan.api.deps import get_lesson_service
from humzehan.schemas.lesson import LearningMode, Lesson
from humzehan.services.lesson_service import LessonService

router = APIRouter(prefix="/lessons", tags=["lessons"])

LessonServiceDep = Annotated[LessonService, Depends(get_lesson_service)]


@router.post("", response_model=Lesson, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    service: LessonServiceDep,
    student: Annotated[str, Form()],
    mode: Annotated[LearningMode, Form()],
    # Default "" so empty text reaches the service (400) instead of FastAPI's 422.
    text: Annotated[str, Form()] = "",
    urdu: Annotated[bool, Form()] = False,
) -> Lesson:
    """Rewrite the text in the chosen learning style (optionally translated into simple Urdu).
    The agent runs in a worker thread."""
    return await run_in_threadpool(service.create, student, mode, text, urdu)


@router.get("/{lesson_id}", response_model=Lesson)
def get_lesson(lesson_id: str, service: LessonServiceDep) -> Lesson:
    return service.get(lesson_id)
