"""FastAPI dependencies: settings, the agent graph and the services.

Tests override ``get_agent_graph`` with a graph built on a fake LLM.
"""

import threading
from typing import Annotated, cast

from fastapi import Depends, Request

from humzehan.agents.graph import AgentGraph, build_graph
from humzehan.core.config import Settings
from humzehan.db.repositories import LessonRepository, ProgressRepository
from humzehan.llm.client import get_chat_model
from humzehan.services.dashboard_service import DashboardService
from humzehan.services.lesson_service import LessonService
from humzehan.services.progress_service import ProgressService

_graph_lock = threading.Lock()


def get_app_settings(request: Request) -> Settings:
    """The Settings the app was created with (see ``create_app``)."""
    return cast(Settings, request.app.state.settings)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_agent_graph(request: Request, settings: SettingsDep) -> AgentGraph:
    """Build the agent graph once (on first use) and reuse it for every request."""
    state = request.app.state
    with _graph_lock:
        if getattr(state, "agent_graph", None) is None:
            state.agent_graph = build_graph(get_chat_model(settings), settings)
        return cast(AgentGraph, state.agent_graph)


def get_lesson_service(
    settings: SettingsDep, graph: Annotated[AgentGraph, Depends(get_agent_graph)]
) -> LessonService:
    return LessonService(LessonRepository(settings.database_path), graph, settings.max_source_chars)


def get_progress_service(settings: SettingsDep) -> ProgressService:
    return ProgressService(
        LessonRepository(settings.database_path), ProgressRepository(settings.database_path)
    )


def get_dashboard_service(settings: SettingsDep) -> DashboardService:
    return DashboardService(ProgressRepository(settings.database_path))
