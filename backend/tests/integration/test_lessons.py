from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fakes import URDU, FakeLLM
from humzehan.agents.state import ChunkTranslation, TransformOutput
from humzehan.core.config import Settings

SOURCE = "Plants make food from sunlight. Leaves hold chlorophyll."


def create(client: TestClient, **form: str) -> Any:
    data = {"student": "Ali", "mode": "focus", "text": SOURCE, **form}
    return client.post("/api/v1/lessons", data=data)


def test_create_and_fetch_lesson(client: TestClient) -> None:
    response = create(client)

    assert response.status_code == 201
    lesson = response.json()
    assert lesson["student"] == "Ali"
    assert lesson["mode"] == "focus"
    assert lesson["urdu"] is False
    assert lesson["title"] == "Photosynthesis"
    assert len(lesson["chunks"]) == 2
    assert all(len(chunk["quiz"]) == 3 for chunk in lesson["chunks"])
    assert [step["node"] for step in lesson["trace"]][:2] == ["ingest", "router"]

    fetched = client.get(f"/api/v1/lessons/{lesson['lesson_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == lesson


def test_lesson_without_urdu_field_is_english(client: TestClient, fake_llm: FakeLLM) -> None:
    lesson = create(client).json()

    assert lesson["urdu"] is False
    assert lesson["english"] is None
    assert fake_llm.calls_for(ChunkTranslation) == []
    assert lesson["trace"][-1]["node"] == "checker"


def test_create_urdu_lesson_keeps_english(client: TestClient) -> None:
    response = create(client, urdu="true")

    assert response.status_code == 201
    lesson = response.json()
    assert lesson["urdu"] is True
    assert lesson["title"] == f"{URDU} Photosynthesis"
    assert all(chunk["heading"].startswith(URDU) for chunk in lesson["chunks"])
    assert lesson["english"]["title"] == "Photosynthesis"
    assert [c["heading"] for c in lesson["english"]["chunks"]] == ["Food from light", "Leaves"]
    assert lesson["trace"][-1]["node"] == "urdu"

    fetched = client.get(f"/api/v1/lessons/{lesson['lesson_id']}")
    assert fetched.json() == lesson  # stored JSON includes the English version


def test_invalid_urdu_value_returns_422(client: TestClient) -> None:
    assert create(client, urdu="maybe").status_code == 422


def test_unknown_lesson_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/lessons/does-not-exist")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.parametrize("text", ["", "   \n  "])
def test_empty_text_returns_400(client: TestClient, text: str) -> None:
    response = create(client, text=text)

    assert response.status_code == 400
    assert response.json() == {"detail": "Text must not be empty."}


def test_missing_text_field_returns_400(client: TestClient) -> None:
    response = client.post("/api/v1/lessons", data={"student": "Ali", "mode": "focus"})

    assert response.status_code == 400


def test_too_long_text_returns_400(client: TestClient, settings: Settings) -> None:
    response = create(client, text="a" * (settings.max_source_chars + 1))

    assert response.status_code == 400
    assert "too long" in response.json()["detail"]


def test_text_at_the_limit_is_accepted(client: TestClient, settings: Settings) -> None:
    response = create(client, text="a" * settings.max_source_chars)

    assert response.status_code == 201


def test_blank_student_returns_400(client: TestClient) -> None:
    response = create(client, student="  ")

    assert response.status_code == 400


def test_invalid_mode_returns_422(client: TestClient) -> None:
    response = create(client, mode="dyslexia")

    assert response.status_code == 422


def _fail(_: str) -> BaseModel:
    raise RuntimeError("provider down")


@pytest.mark.parametrize("fake_llm", [FakeLLM(handlers={TransformOutput: _fail})])
def test_llm_failure_returns_502(client: TestClient) -> None:
    response = create(client)

    assert response.status_code == 502
    assert response.json() == {"detail": "The AI service could not create the lesson."}
    assert client.get("/api/v1/dashboard").json() == {"students": []}  # nothing saved
