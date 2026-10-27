"""Base interface and shared types for thread registries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NoReturn, Optional

from typing_extensions import TypedDict

from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryThreadConflictError,
    AgentMemoryThreadExpiredError,
)


def _validate_ttl(ttl_seconds: Optional[int]) -> None:
    """Raise ValueError for any TTL that cannot represent a positive duration."""
    if ttl_seconds is not None and (
        not isinstance(ttl_seconds, int)
        or isinstance(ttl_seconds, bool)
        or ttl_seconds <= 0
    ):
        raise ValueError(f"ttl_seconds must be a positive integer, got {ttl_seconds!r}")


def _raise_thread_expired(
    thread_id: str, *, from_exc: Optional[BaseException] = None
) -> NoReturn:
    """Raise the canonical "re-create an expired thread" error.

    Both registries reject re-creating a thread whose ID has expired; this
    keeps the message identical whether the check is local (in-memory) or
    derived from a service 409 response.
    """
    raise AgentMemoryThreadExpiredError(
        f"Thread '{thread_id}' has expired and cannot be re-created with the same ID"
    ) from from_exc


def _raise_thread_conflict(
    thread_id: str, *, from_exc: Optional[BaseException] = None
) -> NoReturn:
    """Raise the canonical "thread owned by someone else" error."""
    raise AgentMemoryThreadConflictError(
        f"Thread '{thread_id}' is already registered by a different owner"
    ) from from_exc


class ThreadRegistryEntry(TypedDict):
    """A single thread registry record returned by all registry operations."""

    threadId: str
    agentId: str
    invokerId: str
    description: Optional[str]
    createdAt: Optional[str]
    updatedAt: Optional[str]
    expiresAt: Optional[str]
    threadTtl: Optional[int]
    metadata: Optional[dict[str, Any]]


class ThreadPage(TypedDict):
    """Paginated result from :meth:`~BaseThreadRegistry.list_threads`.

    ``total`` reflects the full server-side count for the given filters
    regardless of the page size::

        page = registry.list_threads(agent_id="sales-agent")
        if page["offset"] + len(page["entries"]) < page["total"]:
            next_page = registry.list_threads(
                agent_id="sales-agent",
                limit=page["limit"],
                offset=page["offset"] + page["limit"],
            )
    """

    entries: list[ThreadRegistryEntry]
    total: int
    limit: int
    offset: int


class BaseThreadRegistry(ABC):
    """Abstract base class for thread registry implementations.

    Analogous to ``BaseCheckpointSaver`` in the LangGraph ecosystem.
    Both ``InMemoryThreadRegistry`` (local dev) and
    ``SAPAgentMemoryThreadRegistry`` (service-backed) implement this interface.

    Subclasses must implement all five abstract methods. Missing implementations
    raise ``TypeError`` at instantiation time.

    .. note:: Async interface

        If async support is introduced in a future version, async methods will
        always arrive as **non-abstract concrete defaults** (never as
        ``@abstractmethod``). Existing subclasses are therefore never required
        to implement them, and will automatically benefit from a default
        threadpool-backed implementation via ``asyncio.to_thread``.
    """

    @abstractmethod
    def create_or_register_thread(
        self,
        agent_id: str,
        invoker_id: str,
        *,
        thread_id: Optional[str] = None,
        description: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        """Create a thread (server-assigned ID) or register an existing one.

        When ``thread_id`` is omitted the server assigns a UUID and a new
        thread is always created.

        When ``thread_id`` is supplied the call is idempotent for the same
        ``(agent_id, invoker_id)`` owner.

        Raises:
            AgentMemoryThreadConflictError: If the thread exists under a different owner.
            AgentMemoryThreadExpiredError: If the thread exists but has expired.
        """
        ...

    @abstractmethod
    def get_thread(
        self,
        thread_id: str,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        """Fetch a single thread by ID.

        Raises:
            AgentMemoryThreadNotFoundError: If the thread does not exist.
        """
        ...

    @abstractmethod
    def list_threads(
        self,
        *,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadPage:
        """List threads with optional filters and pagination.

        When ``limit`` is ``None`` all matching threads are returned.
        """
        ...

    @abstractmethod
    def update_thread(
        self,
        thread_id: str,
        *,
        description: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        """Update mutable fields of a thread.

        Only the fields you pass are modified; omitted fields are left
        unchanged (PATCH-style merge, mirroring LangGraph's ``threads.update``).

        Pass ``ttl_seconds`` (a positive integer) to set the sliding TTL. Omit
        it to leave the current TTL unchanged.

        Raises:
            AgentMemoryThreadNotFoundError: If the thread does not exist.
        """
        ...

    @abstractmethod
    def delete_thread(
        self,
        thread_id: str,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> None:
        """Delete a thread. Idempotent — a missing thread is a no-op."""
        ...
