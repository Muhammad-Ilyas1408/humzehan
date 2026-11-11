"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from humzehan import __version__
from humzehan.api.v1.router import api_router
from humzehan.core.config import Settings, get_settings
from humzehan.core.exceptions import (
    DomainError,
    InvalidInputError,
    LLMFailureError,
    NotFoundError,
)
from humzehan.core.logging import configure_logging
from humzehan.db.session import init_db

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    InvalidInputError: 400,
    NotFoundError: 404,
    LLMFailureError: 502,
}


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = next(
        (code for error, code in STATUS_BY_ERROR.items() if isinstance(exc, error)), 500
    )
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_db(settings.database_path)
        yield

    app = FastAPI(title="HumZehan API", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.include_router(api_router)
    return app


app = create_app()
