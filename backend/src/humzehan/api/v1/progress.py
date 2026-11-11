"""Progress route: save a quiz score for a chunk."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from humzehan.api.deps import get_progress_service
from humzehan.schemas.progress import ProgressCreate
from humzehan.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def record_progress(
    progress: ProgressCreate,
    service: Annotated[ProgressService, Depends(get_progress_service)],
) -> None:
    service.record(progress)
