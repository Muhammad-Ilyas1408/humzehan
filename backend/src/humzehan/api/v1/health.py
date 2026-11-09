"""Health check route."""

from fastapi import APIRouter

from humzehan import __version__
from humzehan.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API is up, plus the running version."""
    return HealthResponse(status="ok", version=__version__)
