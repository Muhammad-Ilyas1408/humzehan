"""Extract route: read the printed text from a photo (before transforming it)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from humzehan.api.deps import get_extract_service
from humzehan.schemas.extract import ExtractResponse
from humzehan.services.extract_service import ExtractService

router = APIRouter(prefix="/extract", tags=["extract"])

ExtractServiceDep = Annotated[ExtractService, Depends(get_extract_service)]


@router.post("", response_model=ExtractResponse)
async def extract_text(
    service: ExtractServiceDep,
    # Optional so a missing file reaches the service (400) instead of FastAPI's 422.
    image: Annotated[UploadFile | None, File()] = None,
) -> ExtractResponse:
    """Return the text printed in the photo. The vision call runs in a worker thread."""
    # Read at most one byte over the limit: enough for the service to reject a large file.
    data = await image.read(service.max_image_bytes + 1) if image is not None else b""
    text = await run_in_threadpool(service.extract, data)
    return ExtractResponse(text=text)
