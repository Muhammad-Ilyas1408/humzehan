from typing import Any

import pytest
from fastapi.testclient import TestClient

from fakes import FakeVisionLLM, make_image, make_rotated_jpeg
from humzehan.api.deps import get_vision_llm
from humzehan.core.config import Settings
from humzehan.main import create_app
from humzehan.services.extract_service import UNREADABLE_MESSAGE, PageText

URL = "/api/v1/extract"


def upload(
    client: TestClient, data: bytes, name: str = "page.png", content_type: str = "image/png"
) -> Any:
    return client.post(URL, files={"image": (name, data, content_type)})


@pytest.mark.parametrize(
    ("fmt", "name", "content_type"),
    [("PNG", "page.png", "image/png"), ("JPEG", "page.jpg", "image/jpeg")],
)
def test_valid_photo_returns_text(
    client: TestClient, fake_vision_llm: FakeVisionLLM, fmt: str, name: str, content_type: str
) -> None:
    response = upload(client, make_image(fmt), name, content_type)

    assert response.status_code == 200
    assert response.json() == {"text": "# Plants\n\nPlants make food."}
    assert len(fake_vision_llm.calls) == 1
    assert fake_vision_llm.sent_image().format == "JPEG"


def test_webp_photo_returns_text(client: TestClient) -> None:
    response = upload(client, make_image("WEBP"), "page.webp", "image/webp")

    assert response.status_code == 200


def test_text_is_stripped(client: TestClient, fake_vision_llm: FakeVisionLLM) -> None:
    fake_vision_llm.page = PageText(text="\n  Leaves are green.  \n", legible=True)

    assert upload(client, make_image()).json() == {"text": "Leaves are green."}


def test_exif_rotated_photo_reaches_the_model_upright(
    client: TestClient, fake_vision_llm: FakeVisionLLM
) -> None:
    response = upload(client, make_rotated_jpeg((200, 100)), "page.jpg", "image/jpeg")

    assert response.status_code == 200
    assert fake_vision_llm.sent_image().size == (100, 200)


def test_large_photo_reaches_the_model_downscaled(
    client: TestClient, fake_vision_llm: FakeVisionLLM
) -> None:
    response = upload(client, make_image("PNG", (3000, 4000)))

    assert response.status_code == 200
    sent = fake_vision_llm.sent_image()
    assert sent.format == "JPEG"
    assert sent.size == (1536, 2048)


@pytest.mark.parametrize(
    ("data", "name", "content_type"),
    [
        (make_image("GIF"), "page.gif", "image/gif"),
        (b"this is not an image", "page.png", "image/png"),  # name and type lie
        (make_image("GIF"), "page.jpg", "image/jpeg"),
    ],
    ids=["gif", "text-named-png", "gif-named-jpg"],
)
def test_wrong_file_type_is_rejected(
    client: TestClient,
    fake_vision_llm: FakeVisionLLM,
    data: bytes,
    name: str,
    content_type: str,
) -> None:
    response = upload(client, data, name, content_type)

    assert response.status_code == 400
    assert response.json() == {"detail": "Please upload a JPG, PNG or WEBP photo."}
    assert fake_vision_llm.calls == []


def test_empty_file_is_rejected(client: TestClient) -> None:
    response = upload(client, b"")

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_missing_file_is_rejected(client: TestClient) -> None:
    response = client.post(URL, data={"other": "x"})

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_too_large_file_is_rejected(settings: Settings, fake_vision_llm: FakeVisionLLM) -> None:
    small_limit = settings.model_copy(update={"max_image_bytes": 2000})
    app = create_app(small_limit)
    app.dependency_overrides[get_vision_llm] = lambda: fake_vision_llm
    data = make_image("PNG", (600, 600), compress_level=0)
    assert len(data) > 2000

    with TestClient(app) as client:
        response = upload(client, data)

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
    assert fake_vision_llm.calls == []


@pytest.mark.parametrize(
    "page",
    [
        PageText(text="", legible=False),
        PageText(text="Blurry words", legible=False),
        PageText(text="   ", legible=True),
    ],
    ids=["illegible-empty", "illegible-with-text", "legible-but-blank"],
)
def test_unreadable_photo_is_rejected(
    client: TestClient, fake_vision_llm: FakeVisionLLM, page: PageText
) -> None:
    fake_vision_llm.page = page

    response = upload(client, make_image())

    assert response.status_code == 400
    assert response.json() == {"detail": UNREADABLE_MESSAGE}


def test_llm_failure_returns_502(client: TestClient, fake_vision_llm: FakeVisionLLM) -> None:
    fake_vision_llm.error = RuntimeError("provider down")

    response = upload(client, make_image())

    assert response.status_code == 502
    assert response.json() == {"detail": "The AI service could not read the photo."}
