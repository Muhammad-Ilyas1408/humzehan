"""Shared pytest fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fakes import FakeLLM, FakeVisionLLM, make_lesson_llm
from humzehan.agents.graph import build_graph
from humzehan.api.deps import get_agent_graph, get_vision_llm
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
def fake_vision_llm() -> FakeVisionLLM:
    """The fake vision model behind POST /extract (reads "# Plants / Plants make food.")."""
    return FakeVisionLLM()


@pytest.fixture
def client(
    settings: Settings, fake_llm: FakeLLM, fake_vision_llm: FakeVisionLLM
) -> Iterator[TestClient]:
    """A TestClient for a fresh app with test settings and fake LLMs (agent graph and vision)."""
    app = create_app(settings)
    graph = build_graph(fake_llm, settings)
    app.dependency_overrides[get_agent_graph] = lambda: graph
    app.dependency_overrides[get_vision_llm] = lambda: fake_vision_llm
    with TestClient(app) as test_client:
        yield test_client
