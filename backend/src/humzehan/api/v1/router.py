"""Aggregate router for API version 1."""

from fastapi import APIRouter

from humzehan.api.v1 import dashboard, extract, health, lessons, progress

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(lessons.router)
api_router.include_router(extract.router)
api_router.include_router(progress.router)
api_router.include_router(dashboard.router)
