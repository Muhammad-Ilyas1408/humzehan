"""Dashboard route: per-student totals."""

from typing import Annotated

from fastapi import APIRouter, Depends

from humzehan.api.deps import get_dashboard_service
from humzehan.schemas.dashboard import DashboardSummary
from humzehan.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardSummary:
    return service.summary()
