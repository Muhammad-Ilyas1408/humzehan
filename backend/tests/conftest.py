"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from humzehan.core.config import Settings
from humzehan.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Test settings that ignore any local .env file."""
    return Settings(_env_file=None, app_env="test")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """A TestClient for a fresh app built with test settings."""
    with TestClient(create_app(settings)) as test_client:
        yield test_client
