"""Create the chat model used by all agent nodes."""

from langchain_openai import ChatOpenAI

from humzehan.core.config import Settings

TEMPERATURE = 0.2


def get_chat_model(settings: Settings) -> ChatOpenAI:
    """Return a ChatOpenAI client configured from settings (low temperature)."""
    return ChatOpenAI(
        model_name=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=TEMPERATURE,
    )
