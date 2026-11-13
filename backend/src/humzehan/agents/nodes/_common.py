"""Helpers shared by the agent nodes: tracing and structured LLM calls."""

import time
from typing import Protocol

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from pydantic import BaseModel

from humzehan.agents.state import AgentState
from humzehan.schemas.lesson import TraceStep


class Node(Protocol):
    """A graph node: ``(state) -> partial state``."""

    def __call__(self, state: AgentState) -> AgentState: ...


def start_timer() -> float:
    return time.perf_counter()


def add_step(state: AgentState, node: str, note: str, started: float) -> list[TraceStep]:
    """Return the trace with one new step appended (does not mutate the state)."""
    ms = max(0, round((time.perf_counter() - started) * 1000))
    return [*state.get("trace", []), TraceStep(node=node, note=note, ms=ms)]


def _validated[M: BaseModel](schema: type[M], result: object) -> M:
    return result if isinstance(result, schema) else schema.model_validate(result)


def ask[M: BaseModel](llm: BaseChatModel, schema: type[M], system: str, user: str) -> M:
    """Call the LLM with structured output and return a validated ``schema`` instance."""
    result = llm.with_structured_output(schema).invoke([("system", system), ("human", user)])
    return _validated(schema, result)


def ask_many[M: BaseModel](
    llm: BaseChatModel, schema: type[M], system: str, users: list[str]
) -> list[M]:
    """Run one structured call per user prompt in parallel; results keep the input order."""
    if not users:
        return []
    inputs: list[LanguageModelInput] = [[("system", system), ("human", user)] for user in users]
    results = llm.with_structured_output(schema).batch(inputs)
    return [_validated(schema, result) for result in results]


def ask_many_or_errors[M: BaseModel](
    llm: BaseChatModel, schema: type[M], system: str, users: list[str]
) -> list[M | Exception]:
    """Like ``ask_many``, but a failed call (provider error or invalid output) is returned as
    its exception in that position instead of failing the whole batch."""
    if not users:
        return []
    inputs: list[LanguageModelInput] = [[("system", system), ("human", user)] for user in users]
    results = llm.with_structured_output(schema).batch(inputs, return_exceptions=True)
    out: list[M | Exception] = []
    for result in results:
        if isinstance(result, Exception):
            out.append(result)
            continue
        try:
            out.append(_validated(schema, result))
        except ValueError as exc:  # pydantic.ValidationError is a ValueError
            out.append(exc)
    return out
