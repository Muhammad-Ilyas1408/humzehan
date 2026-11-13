"""Read the printed text from a photo of a textbook page with a vision model.

This runs before the agent: the student checks and fixes the text, then transforms it.
The image is never stored or logged.
"""

import base64
import logging
from functools import cache
from importlib.resources import files

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from humzehan.core.exceptions import InvalidInputError, LLMFailureError
from humzehan.services.images import prepare_image

logger = logging.getLogger(__name__)

UNREADABLE_MESSAGE = (
    "We couldn't read text in this photo. Try a clearer, well-lit photo of one page."
)
USER_INSTRUCTION = "Copy the printed text from this textbook page."


class PageText(BaseModel):
    """Structured output requested from the vision model."""

    text: str = Field(description="The printed text, copied exactly. Empty if not legible.")
    legible: bool = Field(description="False if the photo has no readable printed text.")


@cache
def extract_prompt() -> str:
    """The system prompt in ``services/prompts/extract.md``."""
    resource = files("humzehan.services").joinpath("prompts", "extract.md")
    return resource.read_text(encoding="utf-8")


def _megabytes(size: int) -> str:
    return f"{size / (1024 * 1024):.1f}".removesuffix(".0")


class ExtractService:
    def __init__(self, llm: BaseChatModel, max_image_bytes: int) -> None:
        self._llm = llm
        self._max_image_bytes = max_image_bytes

    @property
    def max_image_bytes(self) -> int:
        return self._max_image_bytes

    def extract(self, data: bytes) -> str:
        """Return the text printed in the photo ``data``. Blocking: call from a thread."""
        if not data:
            raise InvalidInputError("The photo is empty. Please choose another file.")
        if len(data) > self._max_image_bytes:
            raise InvalidInputError(
                f"The photo is too large (over {_megabytes(self._max_image_bytes)} MB). "
                "Please choose a smaller photo."
            )

        jpeg = prepare_image(data)
        page = self._read_page(jpeg)

        text = page.text.strip()
        if not page.legible or not text:
            raise InvalidInputError(UNREADABLE_MESSAGE)
        return text

    def _read_page(self, jpeg: bytes) -> PageText:
        data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        messages = [
            SystemMessage(content=extract_prompt()),
            HumanMessage(
                content=[
                    {"type": "text", "text": USER_INSTRUCTION},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                ]
            ),
        ]
        try:
            result = self._llm.with_structured_output(PageText).invoke(messages)
            return result if isinstance(result, PageText) else PageText.model_validate(result)
        except Exception as exc:
            # Log the error type only: never the image or any text read from it.
            logger.error("Vision model failed to read a photo: %s", type(exc).__name__)
            raise LLMFailureError("The AI service could not read the photo.") from exc
