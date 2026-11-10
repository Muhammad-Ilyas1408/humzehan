"""Router: choose the transform node for the student's learning style (no LLM)."""

from typing import Literal

from humzehan.agents.nodes._common import add_step, start_timer
from humzehan.agents.state import AgentState
from humzehan.schemas.lesson import LearningMode

TransformNodeName = Literal["focus_transform", "easyread_transform", "literal_transform"]

TRANSFORM_NODES: dict[LearningMode, TransformNodeName] = {
    LearningMode.FOCUS: "focus_transform",
    LearningMode.EASYREAD: "easyread_transform",
    LearningMode.LITERAL: "literal_transform",
}


def route_by_mode(state: AgentState) -> TransformNodeName:
    """Pure function: the name of the transform node for ``state["mode"]``."""
    return TRANSFORM_NODES[LearningMode(state["mode"])]


def router(state: AgentState) -> AgentState:
    """Graph node that records the routing decision in the trace."""
    started = start_timer()
    mode = LearningMode(state["mode"])
    note = f"mode={mode.value} -> {route_by_mode(state)}"
    return {"mode": mode, "trace": add_step(state, "router", note, started)}
