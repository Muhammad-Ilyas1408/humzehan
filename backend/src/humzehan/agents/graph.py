"""Wire the agent nodes into a LangGraph graph.

ingest -> router -> {focus|easyread|literal}_transform -> quiz -> checker
checker -> END when all chunks are approved or after ``agent_max_loops`` rewrite rounds,
otherwise back to the mode's transform node (which rewrites only non-approved chunks).
"""

import uuid
from datetime import UTC, datetime

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from humzehan.agents.nodes import (
    ingest,
    make_checker_node,
    make_quiz_node,
    make_transform_node,
    route_by_mode,
    router,
)
from humzehan.agents.nodes.router import TRANSFORM_NODES
from humzehan.agents.state import AgentState
from humzehan.core.config import Settings, get_settings
from humzehan.schemas.lesson import LearningMode, Lesson

AgentGraph = CompiledStateGraph[AgentState, None, AgentState, AgentState]


def after_checker(state: AgentState, max_loops: int) -> str:
    """Decide where to go after the checker."""
    if all(review.action == "approve" for review in state.get("reviews", [])):
        return END
    if state.get("loops", 0) >= max_loops:
        return END  # keep the latest version
    return route_by_mode(state)


def build_graph(llm: BaseChatModel, settings: Settings | None = None) -> AgentGraph:
    """Build and compile the agent graph. The LLM is injected so tests can pass a fake one."""
    max_loops = (settings or get_settings()).agent_max_loops
    transform_names: list[str] = list(TRANSFORM_NODES.values())

    graph: StateGraph[AgentState, None, AgentState, AgentState] = StateGraph(AgentState)
    graph.add_node("ingest", ingest)
    graph.add_node("router", router)
    for mode, node_name in TRANSFORM_NODES.items():
        graph.add_node(node_name, make_transform_node(llm, mode))
    graph.add_node("quiz", make_quiz_node(llm))
    graph.add_node("checker", make_checker_node(llm))

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "router")
    graph.add_conditional_edges("router", route_by_mode, transform_names)
    for name in transform_names:
        graph.add_edge(name, "quiz")
    graph.add_edge("quiz", "checker")
    graph.add_conditional_edges(
        "checker",
        lambda state: after_checker(state, max_loops),
        [*transform_names, END],
    )
    return graph.compile()


def build_lesson(state: AgentState, student: str, urdu: bool = False) -> Lesson:
    """Turn a finished agent state into a Lesson."""
    return Lesson(
        lesson_id=str(uuid.uuid4()),
        student=student,
        mode=LearningMode(state["mode"]),
        urdu=urdu,
        title=state["title"],
        chunks=state["chunks"],
        trace=state["trace"],
        created_at=datetime.now(UTC),
    )
