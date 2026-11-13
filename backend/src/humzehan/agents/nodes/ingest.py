"""Ingest node: prepare the source text (text only; photos are read earlier by POST /extract)."""

from humzehan.agents.nodes._common import add_step, start_timer
from humzehan.agents.state import AgentState


def ingest(state: AgentState) -> AgentState:
    started = start_timer()
    source_text = state.get("source_text", "").strip()
    if not source_text:
        raise ValueError("source_text is empty")
    words = len(source_text.split())
    return {
        "source_text": source_text,
        "loops": 0,
        "reviews": [],
        "chunks": [],
        "trace": add_step(state, "ingest", f"Received text ({words} words)", started),
    }
