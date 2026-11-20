from __future__ import annotations

from typing import Optional


class AgentMemoryError(Exception):
    """Base exception for all Agent Memory service errors."""


class AgentMemoryConfigError(AgentMemoryError):
    """Raised for configuration errors (missing env vars, bad VCAP_SERVICES, empty base_url)."""


class AgentMemoryHttpError(AgentMemoryError):
    """Raised for HTTP and network failures.

    Attributes:
        status_code: HTTP status code, or None for network-level failures.
        response_text: Raw response body text, or None if unavailable.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class AgentMemoryNotFoundError(AgentMemoryHttpError):
    """Raised when the Agent Memory service returns 404 Not Found."""


class AgentMemoryValidationError(AgentMemoryError):
    """Raised when client-side input validation fails before a request is sent."""


class AgentMemoryThreadNotFoundError(AgentMemoryError):
    """Raised when a thread_id does not exist in the thread registry.

    Both the in-memory and service-backed registries raise this type so callers
    catch a single exception regardless of backend.
    """


class AgentMemoryThreadConflictError(AgentMemoryError):
    """Raised when a thread_id is already registered by a different owner.

    "Owner" is the ``(agent_id, invoker_id)`` pair. The service-backed registry
    maps the HTTP 409 ownership conflict onto this type.
    """


class AgentMemoryThreadExpiredError(AgentMemoryError):
    """Raised when a thread_id belongs to an expired thread that has not yet been cleaned up.

    Raised on 409 responses whose body contains "expired", meaning the thread
    row still exists in the DB but its TTL has passed. Re-registering with the
    same ID is not allowed until the cleanup job removes the row.
    """
