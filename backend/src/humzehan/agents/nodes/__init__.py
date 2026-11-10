"""Agent nodes. Each node is a function ``(state) -> partial state`` that appends a TraceStep."""

from humzehan.agents.nodes.checker import make_checker_node
from humzehan.agents.nodes.ingest import ingest
from humzehan.agents.nodes.quiz import make_quiz_node
from humzehan.agents.nodes.router import route_by_mode, router
from humzehan.agents.nodes.transform import make_transform_node

__all__ = [
    "ingest",
    "make_checker_node",
    "make_quiz_node",
    "make_transform_node",
    "route_by_mode",
    "router",
]
