from typing import Any

import pytest
from fastapi.testclient import TestClient

SOURCE = "Plants make food from sunlight. Leaves hold chlorophyll."


@pytest.fixture
def lesson_id(client: TestClient) -> str:
    response = client.post(
        "/api/v1/lessons", data={"student": "Ali", "mode": "easyread", "text": SOURCE}
    )
    assert response.status_code == 201
    return str(response.json()["lesson_id"])


def post_progress(client: TestClient, **body: Any) -> Any:
    return client.post("/api/v1/progress", json=body)


def test_record_progress_returns_204(client: TestClient, lesson_id: str) -> None:
    response = post_progress(client, lesson_id=lesson_id, chunk_index=1, score=2)

    assert response.status_code == 204
    assert response.content == b""
    student = client.get("/api/v1/dashboard").json()["students"][0]
    assert student["chunks_completed"] == 1
    assert student["average_score"] == 2


def test_unknown_lesson_returns_404(client: TestClient) -> None:
    response = post_progress(client, lesson_id="missing", chunk_index=0, score=1)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_chunk_index_out_of_range_returns_400(client: TestClient, lesson_id: str) -> None:
    response = post_progress(client, lesson_id=lesson_id, chunk_index=2, score=1)  # 2 chunks

    assert response.status_code == 400
    assert "out of range" in response.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [
        {"chunk_index": -1, "score": 1},
        {"chunk_index": 0, "score": 4},
        {"chunk_index": 0, "score": -1},
        {"chunk_index": 0},
    ],
)
def test_invalid_body_returns_422(client: TestClient, lesson_id: str, body: dict[str, int]) -> None:
    response = post_progress(client, lesson_id=lesson_id, **body)

    assert response.status_code == 422
    assert "detail" in response.json()
