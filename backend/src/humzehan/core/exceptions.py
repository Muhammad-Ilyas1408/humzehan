"""Domain exceptions raised by services. ``main.py`` maps them to HTTP status codes."""


class DomainError(Exception):
    """Base class for errors that the API reports to the client as ``{"detail": ...}``."""


class InvalidInputError(DomainError):
    """The request is well-formed but its content is not acceptable (HTTP 400)."""


class NotFoundError(DomainError):
    """A requested resource does not exist (HTTP 404)."""


class LLMFailureError(DomainError):
    """The agent / LLM provider failed to produce a lesson (HTTP 502)."""
