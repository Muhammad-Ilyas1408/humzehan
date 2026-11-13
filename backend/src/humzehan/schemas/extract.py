"""API schema for reading text from a photo."""

from pydantic import BaseModel


class ExtractResponse(BaseModel):
    """The text read from the photo, for the student to check before transforming."""

    text: str
