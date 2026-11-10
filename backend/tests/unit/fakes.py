"""A fake chat model for unit tests: no network, fixed structured responses."""

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

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
