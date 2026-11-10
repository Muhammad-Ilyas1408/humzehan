import pytest

from humzehan.agents.nodes import route_by_mode, router
from humzehan.agents.state import AgentState
from humzehan.schemas.lesson import LearningMode


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (LearningMode.FOCUS, "focus_transform"),
        (LearningMode.EASYREAD, "easyread_transform"),
        (LearningMode.LITERAL, "literal_transform"),
        ("easyread", "easyread_transform"),
    ],
)
def test_route_by_mode(mode: LearningMode, expected: str) -> None:
    assert route_by_mode({"mode": mode}) == expected


def test_router_node_appends_trace_step() -> None:
    state: AgentState = {"mode": LearningMode.LITERAL, "trace": []}
    result = router(state)
    assert [step.node for step in result["trace"]] == ["router"]
    assert "literal_transform" in result["trace"][0].note
