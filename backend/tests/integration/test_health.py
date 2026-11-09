from fastapi.testclient import TestClient

from humzehan import __version__


def test_health_returns_ok_and_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
