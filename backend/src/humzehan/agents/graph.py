"""Wire the agent nodes into a LangGraph graph.

ingest -> router -> {focus|easyread|literal}_transform -> quiz -> checker
checker -> back to the mode's transform node (which rewrites only non-approved chunks) while
chunks are not approved and fewer than ``agent_max_loops`` rewrite rounds were done; otherwise
-> urdu (only when ``urdu`` is set) -> END. The whole pipeline is checked in English; the
translation runs last because the checker cannot verify Urdu against the English SOURCE.
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
    make_urdu_node,
    route_by_mode,
    router,
)
from humzehan.agents.nodes.router import TRANSFORM_NODES
from humzehan.agents.state import AgentState
from humzehan.core.config import Settings, get_settings
from humzehan.schemas.lesson import LearningMode, Lesson

AgentGraph = CompiledStateGraph[AgentState, None, AgentState, AgentState]

URDU_NODE = "urdu"


def after_checker(state: AgentState, max_loops: int) -> str:
    """Decide where to go after the checker."""
    finished = all(review.action == "approve" for review in state.get("reviews", []))
    if not finished and state.get("loops", 0) < max_loops:
        return route_by_mode(state)
    # Approved, or out of rewrite rounds (keep the latest version).
    return URDU_NODE if state.get("urdu", False) else END


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
    graph.add_node(URDU_NODE, make_urdu_node(llm))

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "router")
    graph.add_conditional_edges("router", route_by_mode, transform_names)
    for name in transform_names:
        graph.add_edge(name, "quiz")
    graph.add_edge("quiz", "checker")
    graph.add_conditional_edges(
        "checker",
        lambda state: after_checker(state, max_loops),
        [*transform_names, URDU_NODE, END],
    )
    graph.add_edge(URDU_NODE, END)
    return graph.compile()


def build_lesson(state: AgentState, student: str) -> Lesson:
    """Turn a finished agent state into a Lesson.

    The lesson is Urdu only when the urdu node translated it (``english`` is set); a requested
    translation that failed validation leaves an English lesson.
    """
    english = state.get("english")
    return Lesson(
        lesson_id=str(uuid.uuid4()),
        student=student,
        mode=LearningMode(state["mode"]),
        urdu=english is not None,
        title=state["title"],
        chunks=state["chunks"],
        english=english,
        trace=state["trace"],
        created_at=datetime.now(UTC),
    )
