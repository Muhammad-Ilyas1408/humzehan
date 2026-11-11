"""Shared pytest fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fakes import FakeLLM, make_lesson_llm
from humzehan.agents.graph import build_graph
from humzehan.api.deps import get_agent_graph
from humzehan.core.config import Settings
from humzehan.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Test settings that ignore any local .env file and use a fresh SQLite file per test."""
    return Settings(_env_file=None, app_env="test", database_path=tmp_path / "test.db")


@pytest.fixture
def fake_llm() -> FakeLLM:
    """The fake LLM behind the API's agent graph (override this fixture to change behaviour)."""
    return make_lesson_llm()


@pytest.fixture
def client(settings: Settings, fake_llm: FakeLLM) -> Iterator[TestClient]:
    """A TestClient for a fresh app with test settings and an agent graph on the fake LLM."""
    app = create_app(settings)
    graph = build_graph(fake_llm, settings)
    app.dependency_overrides[get_agent_graph] = lambda: graph
    with TestClient(app) as test_client:
        yield test_client
