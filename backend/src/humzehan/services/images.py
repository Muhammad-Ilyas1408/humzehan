"""Prepare an uploaded photo for the vision model. Pure functions: nothing is stored or logged."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from humzehan.core.exceptions import InvalidInputError

ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
MAX_SIDE_PX = 2048
JPEG_QUALITY = 85
WRONG_TYPE_MESSAGE = "Please upload a JPG, PNG or WEBP photo."


def _to_rgb(image: Image.Image) -> Image.Image:
    """Return an RGB copy; transparent areas become white (JPEG has no transparency)."""
    if image.mode == "RGB":
        return image
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def prepare_image(data: bytes) -> bytes:
    """Check the real file type, fix the EXIF rotation, shrink to MAX_SIDE_PX and return a JPEG.

    The type is detected from the file's bytes, not its name or content type.
    Raises ``InvalidInputError`` if the bytes are not a readable JPEG, PNG or WEBP image.
    """
    try:
        with Image.open(BytesIO(data)) as opened:
            if opened.format not in ALLOWED_FORMATS:
                raise InvalidInputError(WRONG_TYPE_MESSAGE)
            opened.load()
            image = ImageOps.exif_transpose(opened)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise InvalidInputError(WRONG_TYPE_MESSAGE) from exc

    image = _to_rgb(image)
    image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.Resampling.LANCZOS)  # only ever shrinks
    out = BytesIO()
    image.save(out, format="JPEG", quality=JPEG_QUALITY)
    return out.getvalue()
