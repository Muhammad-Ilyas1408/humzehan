from fastapi.testclient import TestClient

SOURCE = "Plants make food from sunlight. Leaves hold chlorophyll."


def create_lesson(client: TestClient, student: str) -> str:
    response = client.post(
        "/api/v1/lessons", data={"student": student, "mode": "literal", "text": SOURCE}
    )
    assert response.status_code == 201
    return str(response.json()["lesson_id"])


def score(client: TestClient, lesson_id: str, chunk_index: int, value: int) -> None:
    response = client.post(
        "/api/v1/progress",
        json={"lesson_id": lesson_id, "chunk_index": chunk_index, "score": value},
    )
    assert response.status_code == 204


def test_empty_dashboard(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert response.json() == {"students": []}


def test_dashboard_totals_for_two_students(client: TestClient) -> None:
    ali_1 = create_lesson(client, "Ali")
    ali_2 = create_lesson(client, "Ali")
    sara = create_lesson(client, "Sara")
    create_lesson(client, "Sara")  # no progress yet

    score(client, ali_1, 0, 1)
    score(client, ali_1, 0, 3)  # retake: latest score counts
    score(client, ali_1, 1, 2)
    score(client, ali_2, 0, 1)
    score(client, sara, 1, 0)

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert response.json() == {
        "students": [
            {"student": "Ali", "lessons": 2, "chunks_completed": 3, "average_score": 2.0},
            {"student": "Sara", "lessons": 2, "chunks_completed": 1, "average_score": 0.0},
        ]
    }


def test_student_without_scores_has_no_average(client: TestClient) -> None:
    create_lesson(client, "Zara")

    assert client.get("/api/v1/dashboard").json() == {
        "students": [
            {"student": "Zara", "lessons": 1, "chunks_completed": 0, "average_score": None}
        ]
    }
