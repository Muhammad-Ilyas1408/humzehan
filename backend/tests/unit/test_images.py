from io import BytesIO

import pytest
from PIL import Image

from fakes import make_image, make_rotated_jpeg
from humzehan.core.exceptions import InvalidInputError
from humzehan.services.images import MAX_SIDE_PX, prepare_image


def open_result(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    image.load()
    return image


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_accepted_formats_are_returned_as_jpeg(fmt: str) -> None:
    result = open_result(prepare_image(make_image(fmt)))

    assert result.format == "JPEG"
    assert result.mode == "RGB"
    assert result.size == (200, 100)


def test_exif_orientation_is_applied() -> None:
    result = open_result(prepare_image(make_rotated_jpeg((200, 100))))

    # Orientation 6 = rotate 90° clockwise: the left black half ends up on top.
    assert result.size == (100, 200)
    assert result.convert("L").getpixel((50, 10)) < 60
    assert result.convert("L").getpixel((50, 190)) > 200


def test_large_image_is_downscaled_to_max_side() -> None:
    result = open_result(prepare_image(make_image("PNG", (4000, 1000))))

    assert result.size == (MAX_SIDE_PX, 512)


def test_small_image_is_not_upscaled() -> None:
    assert open_result(prepare_image(make_image("PNG", (300, 400)))).size == (300, 400)


def test_transparent_png_is_flattened_onto_white() -> None:
    out = BytesIO()
    Image.new("RGBA", (40, 40), (0, 0, 0, 0)).save(out, format="PNG")

    result = open_result(prepare_image(out.getvalue()))

    assert result.mode == "RGB"
    assert result.convert("L").getpixel((20, 20)) > 240


@pytest.mark.parametrize(
    "data",
    [
        make_image("GIF"),
        make_image("BMP"),
        b"%PDF-1.7 not an image",
        b"just some text",
        make_image("PNG")[:40],  # truncated PNG
    ],
    ids=["gif", "bmp", "pdf", "text", "truncated-png"],
)
def test_other_files_are_rejected(data: bytes) -> None:
    with pytest.raises(InvalidInputError, match="JPG, PNG or WEBP"):
        prepare_image(data)
