"""Fake chat models and test images: no network, fixed structured responses."""

import base64
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from humzehan.agents.state import (
    CheckerOutput,
    ChunkDraft,
    ChunkTranslation,
    QuizSet,
    TitleTranslation,
    TransformOutput,
)
from humzehan.schemas.lesson import Chunk, GlossaryItem, QuizItem
from humzehan.services.extract_service import PageText

Handler = Callable[[str], BaseModel]


@dataclass
class Call:
    schema: type[BaseModel]
    system: str
    user: str


def _text(messages: Any) -> tuple[str, str]:
    """Return (system, user) text from the message list the nodes send."""
    system = user = ""
    for role, content in messages:
        if role == "system":
            system = content
        else:
            user = content
    return system, user


class _StructuredRunnable(RunnableLambda[Any, BaseModel]):
    """RunnableLambda that reports the size of each batch() call (batch runs in a thread pool)."""

    def __init__(self, func: Callable[[Any], BaseModel], on_batch: Callable[[int], None]) -> None:
        super().__init__(func)
        self._on_batch = on_batch

    def batch(self, inputs: list[Any], *args: Any, **kwargs: Any) -> list[BaseModel]:  # type: ignore[override]
        self._on_batch(len(inputs))
        return super().batch(inputs, *args, **kwargs)


class FakeLLM(BaseChatModel):
    """Returns ``handlers[schema](user_prompt)`` for each structured-output call."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    handlers: dict[type[BaseModel], Handler]
    calls: list[Call] = Field(default_factory=list)
    batches: list[tuple[type[BaseModel], int]] = Field(default_factory=list)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("FakeLLM only supports with_structured_output")

    def with_structured_output(  # type: ignore[override]
        self, schema: type[BaseModel], **kwargs: Any
    ) -> Runnable[Any, BaseModel]:
        def respond(messages: Sequence[Any]) -> BaseModel:
            system, user = _text(messages)
            with self._lock:
                self.calls.append(Call(schema=schema, system=system, user=user))
            return self.handlers[schema](user)

        def record_batch(size: int) -> None:
            with self._lock:
                self.batches.append((schema, size))

        return _StructuredRunnable(respond, record_batch)

    def calls_for(self, schema: type[BaseModel]) -> list[Call]:
        return [c for c in self.calls if c.schema is schema]

    def batch_sizes(self, schema: type[BaseModel]) -> list[int]:
        return [size for s, size in self.batches if s is schema]


def _transform_output(_: str) -> TransformOutput:
    return TransformOutput(
        title="Photosynthesis",
        chunks=[
            ChunkDraft(heading="Food from light", body="Plants make food.", hook=None, glossary=[]),
            ChunkDraft(heading="Leaves", body="Leaves hold chlorophyll.", hook=None, glossary=[]),
        ],
    )


def _quiz_set(_: str) -> QuizSet:
    item = QuizItem(
        question="What do plants make?", options=["Food", "Rocks", "Air"], answer_index=0
    )
    return QuizSet(questions=[item, item, item])


def _approve_all(_: str) -> CheckerOutput:
    return CheckerOutput(reviews=[], suspect_judgments=[])  # missing reviews count as approve


URDU = "اردو"  # prefix the fake translator puts before every translated text


def english_chunk_in(user: str) -> Chunk:
    """The English chunk the urdu node put into a translation prompt (as JSON)."""
    payload = user.split("ENGLISH CHUNK (JSON):\n", 1)[1].rsplit("\n\nTranslate", 1)[0]
    return Chunk.model_validate_json(payload)


def translate_chunk(user: str) -> ChunkTranslation:
    """Fake translation: same structure, every text prefixed with URDU."""
    chunk = english_chunk_in(user)
    return ChunkTranslation(
        heading=f"{URDU} {chunk.heading}",
        body=f"{URDU} {chunk.body}",
        hook=None if chunk.hook is None else f"{URDU} {chunk.hook}",
        glossary=[
            GlossaryItem(term=f"{URDU} {g.term}", meaning=f"{URDU} {g.meaning}")
            for g in chunk.glossary
        ],
        quiz=[
            QuizItem(
                question=f"{URDU} {q.question}",
                options=[f"{URDU} {o}" for o in q.options],
                answer_index=q.answer_index,
            )
            for q in chunk.quiz
        ],
    )


def translate_title(user: str) -> TitleTranslation:
    title = user.split("ENGLISH LESSON TITLE:\n", 1)[1].split("\n", 1)[0]
    return TitleTranslation(title=f"{URDU} {title}")


def make_lesson_llm() -> FakeLLM:
    """A FakeLLM that produces a 2-chunk lesson ("Photosynthesis") approved on the first check,
    and translates it (structure kept, texts prefixed with URDU) when Urdu is requested."""
    return FakeLLM(
        handlers={
            TransformOutput: _transform_output,
            QuizSet: _quiz_set,
            CheckerOutput: _approve_all,
            ChunkTranslation: translate_chunk,
            TitleTranslation: translate_title,
        }
    )


class FakeVisionLLM(BaseChatModel):
    """Fake vision model: records the messages and returns ``page`` (or raises ``error``)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    page: PageText = Field(
        default_factory=lambda: PageText(text="# Plants\n\nPlants make food.", legible=True)
    )
    error: Exception | None = None
    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-vision"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("FakeVisionLLM only supports with_structured_output")

    def with_structured_output(  # type: ignore[override]
        self, schema: type[BaseModel], **kwargs: Any
    ) -> Runnable[Any, BaseModel]:
        def respond(messages: list[BaseMessage]) -> BaseModel:
            self.calls.append(list(messages))
            if self.error is not None:
                raise self.error
            return self.page

        return RunnableLambda(respond)

    def sent_image(self, call: int = -1) -> Image.Image:
        """Decode the image that was sent to the model in call number ``call``."""
        human = self.calls[call][-1]
        assert isinstance(human.content, list)
        block = next(b for b in human.content if isinstance(b, dict) and b["type"] == "image_url")
        url: str = block["image_url"]["url"]
        prefix = "data:image/jpeg;base64,"
        assert url.startswith(prefix)
        image = Image.open(BytesIO(base64.b64decode(url.removeprefix(prefix))))
        image.load()
        return image


def make_image(fmt: str = "PNG", size: tuple[int, int] = (200, 100), **save: Any) -> bytes:
    """Bytes of a small generated image (white, with a black bar on the left half)."""
    image = Image.new("RGB", size, (255, 255, 255))
    image.paste((0, 0, 0), (0, 0, size[0] // 2, size[1]))
    if fmt == "GIF":
        image = image.convert("P")
    out = BytesIO()
    image.save(out, format=fmt, **save)
    return out.getvalue()


def make_rotated_jpeg(size: tuple[int, int] = (200, 100)) -> bytes:
    """A JPEG stored as ``size`` whose EXIF orientation (6) says "rotate 90° clockwise to view"."""
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation
    return make_image("JPEG", size, exif=exif)
