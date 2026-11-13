"""Application settings, loaded from environment variables and backend/.env."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for HumZehan."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    openai_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o-mini"
    # Model that reads text from photos; empty means "same as llm_model".
    vision_model: str = ""
    agent_max_loops: int = 2
    database_path: Path = Path("humzehan.db")
    max_source_chars: int = Field(default=8000, gt=0)
    max_image_bytes: int = Field(default=10 * 1024 * 1024, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string as well as a list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _default_vision_model(self) -> Self:
        if not self.vision_model.strip():
            self.vision_model = self.llm_model
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings instance (cached)."""
    return Settings()
