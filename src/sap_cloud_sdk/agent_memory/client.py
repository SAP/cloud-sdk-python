"""Client for the SAP Agent Memory service (v1 API).

Provides memory management (CRUD + semantic search) and message operations
over a synchronous HTTP interface. All endpoint paths are defined in
``_endpoints.py``, making it straightforward to migrate to a new API version.

Do not instantiate this class directly — use :func:`sap_cloud_sdk.agent_memory.create_client`.
"""

from __future__ import annotations

from typing import Any, Optional

from sap_cloud_sdk.agent_memory._endpoints import (
    MEMORIES,
    MEMORY_SEARCH,
    MESSAGES,
    RETENTION_CONFIG,
)
from sap_cloud_sdk.agent_memory._http_transport import HttpTransport
from sap_cloud_sdk.agent_memory._models import (
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)
from sap_cloud_sdk.agent_memory.utils._odata import (
    FilterDefinition,
    build_list_params,
    build_memory_filter,
    build_message_filter,
    extract_value_and_count,
)
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryValidationError
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


def _require_non_empty(**fields: str) -> None:
    """Raise AgentMemoryValidationError if any named field is an empty string."""
    empty = [name for name, value in fields.items() if not value]
    if empty:
        names = ", ".join(f"'{n}'" for n in empty)
        raise AgentMemoryValidationError(
            f"Required field(s) must be non-empty: {names}"
        )


def _validate_filter_clauses(
    clauses: list[FilterDefinition], allowed_targets: set[str]
) -> None:
    """Raise AgentMemoryValidationError if any FilterDefinition is invalid."""
    allowed_str = ", ".join(f'"{t}"' for t in sorted(allowed_targets))
    for clause in clauses:
        if clause.target not in allowed_targets:
            raise AgentMemoryValidationError(
                f"FilterDefinition 'target' must be one of {{{allowed_str}}}, "
                f'got "{clause.target}"'
            )
        if not clause.contains:
            raise AgentMemoryValidationError(
                "FilterDefinition 'contains' must be a non-empty string"
            )


class AgentMemoryClient:
    """Client for the SAP Agent Memory service (v1 API).

    Provides memory CRUD, semantic search, and message management.

    Do not instantiate directly — use :func:`sap_cloud_sdk.agent_memory.create_client`.

    Args:
        transport: HTTP transport layer (injected by ``create_client``).
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def close(self) -> None:
        """Close the underlying HTTP session and release resources."""
        self._transport.close()

    def __enter__(self) -> AgentMemoryClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # ── Memory operations ──────────────────────────────────────────────────────

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_ADD_MEMORY)
    def add_memory(
        self,
        agent_id: str,
        invoker_id: str,
        content: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Memory:
        """Create a new memory entry.

        Args:
            agent_id: Identifier of the agent.
            invoker_id: Identifier of the user or invoker.
            content: The memory text content.
            metadata: Optional metadata dict (Map type in OData).

        Returns:
            The created :class:`Memory`.

        Raises:
            AgentMemoryValidationError: If any required field is empty.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(agent_id=agent_id, invoker_id=invoker_id, content=content)
        payload: dict[str, Any] = {
            "agentID": agent_id,
            "invokerID": invoker_id,
            "content": content,
        }
        if metadata is not None:
            payload["metadata"] = metadata
        data = self._transport.post(MEMORIES, json=payload)
        return Memory.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_MEMORY)
    def get_memory(self, memory_id: str) -> Memory:
        """Retrieve a memory by ID.

        Args:
            memory_id: The memory identifier (UUID).

        Returns:
            The :class:`Memory`.

        Raises:
            AgentMemoryNotFoundError: If no memory with the given ID exists.
            AgentMemoryValidationError: If ``memory_id`` is empty.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(memory_id=memory_id)
        data = self._transport.get(f"{MEMORIES}({memory_id})")
        return Memory.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_UPDATE_MEMORY)
    def update_memory(
        self,
        memory_id: str,
        *,
        content: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update a memory's content and/or metadata.

        Args:
            memory_id: The memory identifier (UUID).
            content: New content to set.
            metadata: New metadata dict to set.

        Raises:
            AgentMemoryNotFoundError: If no memory with the given ID exists.
            AgentMemoryValidationError: If ``memory_id`` is empty or no fields are provided.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(memory_id=memory_id)
        if content is None and metadata is None:
            raise AgentMemoryValidationError(
                "At least one of 'content' or 'metadata' must be provided"
            )
        payload: dict[str, Any] = {}
        if content is not None:
            payload["content"] = content
        if metadata is not None:
            payload["metadata"] = metadata
        self._transport.patch(f"{MEMORIES}({memory_id})", json=payload)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_DELETE_MEMORY)
    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory permanently.

        Args:
            memory_id: The memory identifier (UUID).

        Raises:
            AgentMemoryNotFoundError: If no memory with the given ID exists.
            AgentMemoryValidationError: If ``memory_id`` is empty.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(memory_id=memory_id)
        self._transport.delete(f"{MEMORIES}({memory_id})")

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_LIST_MEMORIES)
    def list_memories(
        self,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        *,
        filters: Optional[list[FilterDefinition]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Memory]:
        """List memories, optionally filtered by agent and/or invoker.

        Args:
            agent_id: Filter by agent identifier.
            invoker_id: Filter by invoker/user identifier.
            filters: Additional substring filters. Each :class:`FilterDefinition`
                specifies a ``target`` field (``"metadata"`` or ``"content"``)
                and a required ``contains`` substring. Multiple clauses are
                combined with AND. Metadata filtering is free-text only —
                key-value structured search is not supported.
            limit: Maximum number of memories to return. Default is ``50``.
            offset: Number of memories to skip (for pagination). Default is ``0``.

        Returns:
            List of :class:`Memory` objects.

        Raises:
            AgentMemoryValidationError: If ``limit`` < 1, ``offset`` < 0, or a
                filter clause is invalid.
            AgentMemoryHttpError: If the request fails.
        """
        if limit < 1:
            raise AgentMemoryValidationError("'limit' must be >= 1")
        if offset < 0:
            raise AgentMemoryValidationError("'offset' must be >= 0")
        if filters is not None:
            _validate_filter_clauses(filters, {"metadata", "content"})
        params = build_list_params(
            filter_expr=build_memory_filter(
                agent_id=agent_id,
                invoker_id=invoker_id,
                filter_clauses=filters,
            ),
            top=limit,
            skip=offset if offset else None,
        )
        response = self._transport.get(MEMORIES, params=params)
        items, _ = extract_value_and_count(response)
        return [Memory.from_dict(item) for item in items]

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_COUNT_MEMORIES)
    def count_memories(
        self,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
    ) -> int:
        """Count memories matching the given filters.

        Args:
            agent_id: Filter by agent identifier.
            invoker_id: Filter by invoker/user identifier.

        Returns:
            Total number of matching memories.

        Raises:
            AgentMemoryHttpError: If the request fails.
        """
        params = build_list_params(
            filter_expr=build_memory_filter(agent_id=agent_id, invoker_id=invoker_id),
            top=0,
            count=True,
        )
        response = self._transport.get(MEMORIES, params=params)
        _, total = extract_value_and_count(response)
        return total or 0

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_SEARCH_MEMORIES)
    def search_memories(
        self,
        agent_id: str,
        invoker_id: str,
        query: str,
        threshold: float = 0.6,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Perform a semantic (vector) search over stored memories.

        Args:
            agent_id: Agent identifier to scope the search.
            invoker_id: Invoker/user identifier to scope the search.
            query: Natural-language search query (5–5000 characters).
            threshold: Minimum cosine similarity score (0.0–1.0). Default ``0.6``.
            limit: Maximum number of results (1–50). Default is ``10``.

        Returns:
            List of :class:`SearchResult` objects.

        Raises:
            AgentMemoryValidationError: If required fields are empty or parameters are
                out of range (``query`` must be 5–5000 chars, ``threshold`` 0.0–1.0,
                ``limit`` 1–50).
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(agent_id=agent_id, invoker_id=invoker_id, query=query)
        if not (5 <= len(query) <= 5000):
            raise AgentMemoryValidationError(
                "'query' must be between 5 and 5000 characters"
            )
        if not (0.0 <= threshold <= 1.0):
            raise AgentMemoryValidationError("'threshold' must be between 0.0 and 1.0")
        if not (1 <= limit <= 50):
            raise AgentMemoryValidationError("'limit' must be between 1 and 50")
        payload: dict[str, Any] = {
            "agentID": agent_id,
            "invokerID": invoker_id,
            "query": query,
            "threshold": threshold,
            "top": limit,
        }
        response = self._transport.post(MEMORY_SEARCH, json=payload)
        items = response.get("value", [])
        return [SearchResult.from_dict(item) for item in items]

    # ── Message operations ─────────────────────────────────────────────────────

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_ADD_MESSAGE)
    def add_message(
        self,
        agent_id: str,
        invoker_id: str,
        message_group: str,
        role: MessageRole,
        content: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """Create a new message.

        One message is stored per call. Messages sharing the same
        ``message_group`` form a logical conversation.

        Args:
            agent_id: Identifier of the agent.
            invoker_id: Identifier of the user or invoker.
            message_group: Group identifier for conversation threading.
            role: Author role (USER, ASSISTANT, SYSTEM, TOOL).
            content: The message text content.
            metadata: Optional metadata dict.

        Returns:
            The created :class:`Message`.

        Raises:
            AgentMemoryValidationError: If any required field is empty.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(
            agent_id=agent_id,
            invoker_id=invoker_id,
            message_group=message_group,
            content=content,
        )
        payload: dict[str, Any] = {
            "agentID": agent_id,
            "invokerID": invoker_id,
            "messageGroup": message_group,
            "role": role,
            "content": content,
        }
        if metadata is not None:
            payload["metadata"] = metadata
        data = self._transport.post(MESSAGES, json=payload)
        return Message.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_MESSAGE)
    def get_message(self, message_id: str) -> Message:
        """Retrieve a message by ID.

        Args:
            message_id: The message identifier (UUID).

        Returns:
            The :class:`Message`.

        Raises:
            AgentMemoryNotFoundError: If no message with the given ID exists.
            AgentMemoryValidationError: If ``message_id`` is empty.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(message_id=message_id)
        data = self._transport.get(f"{MESSAGES}({message_id})")
        return Message.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_DELETE_MESSAGE)
    def delete_message(self, message_id: str) -> None:
        """Delete a message permanently.

        Args:
            message_id: The message identifier (UUID).

        Raises:
            AgentMemoryNotFoundError: If no message with the given ID exists.
            AgentMemoryValidationError: If ``message_id`` is empty.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(message_id=message_id)
        self._transport.delete(f"{MESSAGES}({message_id})")

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_LIST_MESSAGES)
    def list_messages(
        self,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        message_group: Optional[str] = None,
        role: Optional[str] = None,
        *,
        filters: Optional[list[FilterDefinition]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """List messages, optionally filtered by agent, invoker, group, and role.

        Args:
            agent_id: Filter by agent identifier.
            invoker_id: Filter by invoker/user identifier.
            message_group: Filter by conversation group identifier.
            role: Filter by author role (USER, ASSISTANT, SYSTEM, TOOL).
            filters: Additional substring filters. Each :class:`FilterDefinition`
                specifies a ``target`` field (``"metadata"`` or ``"content"``)
                and a required ``contains`` substring. Multiple clauses are
                combined with AND. Metadata filtering is free-text only —
                key-value structured search is not supported.
            limit: Maximum number of messages to return. Default is ``50``.
            offset: Number of messages to skip (for pagination). Default is ``0``.

        Returns:
            List of :class:`Message` objects.

        Raises:
            AgentMemoryValidationError: If ``limit`` < 1, ``offset`` < 0, or a
                filter clause is invalid.
            AgentMemoryHttpError: If the request fails.
        """
        if limit < 1:
            raise AgentMemoryValidationError("'limit' must be >= 1")
        if offset < 0:
            raise AgentMemoryValidationError("'offset' must be >= 0")
        if filters is not None:
            _validate_filter_clauses(filters, {"metadata", "content"})
        params = build_list_params(
            filter_expr=build_message_filter(
                agent_id=agent_id,
                invoker_id=invoker_id,
                message_group=message_group,
                role=role,
                filter_clauses=filters,
            ),
            top=limit,
            skip=offset if offset else None,
        )
        response = self._transport.get(MESSAGES, params=params)
        items, _ = extract_value_and_count(response)
        return [Message.from_dict(item) for item in items]

    # ── Admin operations ───────────────────────────────────────────────────────

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_RETENTION_CONFIG)
    def get_retention_config(self) -> RetentionConfig:
        """Retrieve the data retention configuration (singleton).

        Returns:
            The current :class:`RetentionConfig`.

        Raises:
            AgentMemoryHttpError: If the request fails.
        """
        data = self._transport.get(RETENTION_CONFIG)
        return RetentionConfig.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_UPDATE_RETENTION_CONFIG)
    def update_retention_config(
        self,
        *,
        message_days: Optional[int] = None,
        memory_days: Optional[int] = None,
        usage_log_days: Optional[int] = None,
    ) -> None:
        """Update the data retention configuration.

        Only the provided fields are updated. Set a field to ``0`` to
        explicitly pass zero, or omit it to leave unchanged.
        The server accepts ``null`` to disable cleanup for a category.

        Args:
            message_days: How long to keep messages (days).
            memory_days: How long to keep memories without access (days).
            usage_log_days: How long to keep access and search logs (days).

        Raises:
            AgentMemoryValidationError: If no fields are provided, or any provided
                value is negative.
            AgentMemoryHttpError: If the request fails.
        """
        if message_days is None and memory_days is None and usage_log_days is None:
            raise AgentMemoryValidationError(
                "At least one of 'message_days', 'memory_days', or "
                "'usage_log_days' must be provided"
            )
        for name, value in (
            ("message_days", message_days),
            ("memory_days", memory_days),
            ("usage_log_days", usage_log_days),
        ):
            if value is not None and value < 0:
                raise AgentMemoryValidationError(f"'{name}' must be >= 0")
        payload: dict[str, Any] = {}
        if message_days is not None:
            payload["messageDays"] = message_days
        if memory_days is not None:
            payload["memoryDays"] = memory_days
        if usage_log_days is not None:
            payload["usageLogDays"] = usage_log_days
        self._transport.patch(RETENTION_CONFIG, json=payload)
