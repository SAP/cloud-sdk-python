"""Client for the SAP Agent Memory service (v1 API).

Provides memory management (CRUD + semantic search) and message operations
over a synchronous HTTP interface. All endpoint paths are defined in
``_endpoints.py``, making it straightforward to migrate to a new API version.

Do not instantiate this class directly — use :func:`sap_cloud_sdk.agent_memory.create_client`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig

from sap_cloud_sdk.agent_memory._endpoints import (
    MEMORIES,
    MEMORY_SEARCH,
    MESSAGES,
    RETENTION_CONFIG,
)
from sap_cloud_sdk.agent_memory._http_transport import HttpTransport
from sap_cloud_sdk.agent_memory._models import (
    AccessStrategy,
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
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryConfigError,
    AgentMemoryValidationError,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


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
        transport: HTTP transport loaded from the provider (``default``) binding,
            or from the subscriber binding when ``tenant`` is provided at init time.
        access_strategy: Default tenant access strategy for all operations.
            Defaults to ``SUBSCRIBER``. Can be overridden per method call.
        tenant: Default subscriber tenant subdomain. Required when
            ``access_strategy=SUBSCRIBER``. Can be overridden per method call.
        config_loader: Callable that loads an ``AgentMemoryConfig`` for a named
            binding instance (e.g. ``_load_config_for_instance``). Required to
            support per-call tenant overrides that differ from the client default.
    """

    def __init__(
        self,
        transport: HttpTransport,
        *,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER,
        tenant: Optional[str] = None,
        config_loader: Optional[Callable[[str], "AgentMemoryConfig"]] = None,
    ) -> None:
        self._default_access_strategy = access_strategy
        self._default_tenant = tenant
        self._config_loader = config_loader
        self._subscriber_transport_cache: dict[str, HttpTransport] = {}
        if access_strategy is AccessStrategy.SUBSCRIBER and tenant:
            # Pre-warm cache with the already-loaded subscriber transport
            self._subscriber_transport_cache[tenant] = transport
            self._provider_transport: Optional[HttpTransport] = None
        else:
            self._provider_transport = transport

    def close(self) -> None:
        """Close all underlying HTTP sessions and release resources."""
        if self._provider_transport is not None:
            self._provider_transport.close()
        for t in self._subscriber_transport_cache.values():
            t.close()
        self._subscriber_transport_cache.clear()

    def __enter__(self) -> AgentMemoryClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _get_transport(
        self,
        access_strategy: Optional[AccessStrategy],
        tenant: Optional[str],
    ) -> HttpTransport:
        """Return the transport for the effective access strategy and tenant.

        Per-call parameters take precedence over instance defaults. Each
        subscriber tenant gets its own transport loaded from its binding
        (lazily, with caching). The provider always uses a single transport.

        Raises:
            AgentMemoryValidationError: If the effective strategy is
                ``SUBSCRIBER`` but no tenant is available.
            AgentMemoryConfigError: If a per-call subscriber tenant requires a
                new binding load but no ``config_loader`` is configured.
        """
        effective_strategy = (
            access_strategy
            if access_strategy is not None
            else self._default_access_strategy
        )
        effective_tenant = tenant if tenant is not None else self._default_tenant

        if effective_strategy is AccessStrategy.SUBSCRIBER:
            if not effective_tenant:
                raise AgentMemoryValidationError(
                    "tenant is required when access_strategy=SUBSCRIBER"
                )
            if effective_tenant not in self._subscriber_transport_cache:
                if self._config_loader is None:
                    raise AgentMemoryConfigError(
                        f"No config_loader available to load binding for tenant "
                        f"'{effective_tenant}'. Pass config_loader to create_client()."
                    )
                config = self._config_loader(effective_tenant)
                self._subscriber_transport_cache[effective_tenant] = HttpTransport(
                    config
                )
            return self._subscriber_transport_cache[effective_tenant]

        # PROVIDER
        logger.warning(
            "AccessStrategy.PROVIDER is active: no tenant isolation will be applied. "
            "Only use this strategy for provider-owned operations."
        )
        if self._provider_transport is None:
            if self._config_loader is None:
                raise AgentMemoryConfigError(
                    "No provider transport available. "
                    "This client was created with a subscriber binding only."
                )
            from sap_cloud_sdk.agent_memory.config import _load_config_from_env

            self._provider_transport = HttpTransport(_load_config_from_env())
        return self._provider_transport

    # ── Memory operations ──────────────────────────────────────────────────────

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_ADD_MEMORY)
    def add_memory(
        self,
        agent_id: str,
        invoker_id: str,
        content: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> Memory:
        """Create a new memory entry.

        Args:
            agent_id: Identifier of the agent.
            invoker_id: Identifier of the user or invoker.
            content: The memory text content.
            metadata: Optional metadata dict (Map type in OData).
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            The created :class:`Memory`.

        Raises:
            AgentMemoryValidationError: If any required field is empty or tenant is missing
                for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(agent_id=agent_id, invoker_id=invoker_id, content=content)
        transport = self._get_transport(access_strategy, tenant)
        payload: dict[str, Any] = {
            "agentID": agent_id,
            "invokerID": invoker_id,
            "content": content,
        }
        if metadata is not None:
            payload["metadata"] = metadata
        data = transport.post(MEMORIES, json=payload)
        return Memory.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_MEMORY)
    def get_memory(
        self,
        memory_id: str,
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> Memory:
        """Retrieve a memory by ID.

        Args:
            memory_id: The memory identifier (UUID).
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            The :class:`Memory`.

        Raises:
            AgentMemoryNotFoundError: If no memory with the given ID exists.
            AgentMemoryValidationError: If ``memory_id`` is empty or tenant is missing
                for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(memory_id=memory_id)
        transport = self._get_transport(access_strategy, tenant)
        data = transport.get(f"{MEMORIES}({memory_id})")
        return Memory.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_UPDATE_MEMORY)
    def update_memory(
        self,
        memory_id: str,
        *,
        content: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """Update a memory's content and/or metadata.

        Args:
            memory_id: The memory identifier (UUID).
            content: New content to set.
            metadata: New metadata dict to set.
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Raises:
            AgentMemoryNotFoundError: If no memory with the given ID exists.
            AgentMemoryValidationError: If ``memory_id`` is empty, no fields are provided,
                or tenant is missing for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(memory_id=memory_id)
        if content is None and metadata is None:
            raise AgentMemoryValidationError(
                "At least one of 'content' or 'metadata' must be provided"
            )
        transport = self._get_transport(access_strategy, tenant)
        payload: dict[str, Any] = {}
        if content is not None:
            payload["content"] = content
        if metadata is not None:
            payload["metadata"] = metadata
        transport.patch(f"{MEMORIES}({memory_id})", json=payload)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_DELETE_MEMORY)
    def delete_memory(
        self,
        memory_id: str,
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """Delete a memory permanently.

        Args:
            memory_id: The memory identifier (UUID).
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Raises:
            AgentMemoryNotFoundError: If no memory with the given ID exists.
            AgentMemoryValidationError: If ``memory_id`` is empty or tenant is missing
                for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(memory_id=memory_id)
        transport = self._get_transport(access_strategy, tenant)
        transport.delete(f"{MEMORIES}({memory_id})")

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_LIST_MEMORIES)
    def list_memories(
        self,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        *,
        filters: Optional[list[FilterDefinition]] = None,
        limit: int = 50,
        offset: int = 0,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
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
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            List of :class:`Memory` objects.

        Raises:
            AgentMemoryValidationError: If ``limit`` < 1, ``offset`` < 0, a filter
                clause is invalid, or tenant is missing for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        if limit < 1:
            raise AgentMemoryValidationError("'limit' must be >= 1")
        if offset < 0:
            raise AgentMemoryValidationError("'offset' must be >= 0")
        if filters is not None:
            _validate_filter_clauses(filters, {"metadata", "content"})
        transport = self._get_transport(access_strategy, tenant)
        params = build_list_params(
            filter_expr=build_memory_filter(
                agent_id=agent_id,
                invoker_id=invoker_id,
                filter_clauses=filters,
            ),
            top=limit,
            skip=offset if offset else None,
        )
        response = transport.get(MEMORIES, params=params)
        items, _ = extract_value_and_count(response)
        return [Memory.from_dict(item) for item in items]

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_COUNT_MEMORIES)
    def count_memories(
        self,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> int:
        """Count memories matching the given filters.

        Args:
            agent_id: Filter by agent identifier.
            invoker_id: Filter by invoker/user identifier.
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            Total number of matching memories.

        Raises:
            AgentMemoryValidationError: If tenant is missing for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        transport = self._get_transport(access_strategy, tenant)
        params = build_list_params(
            filter_expr=build_memory_filter(agent_id=agent_id, invoker_id=invoker_id),
            top=0,
            count=True,
        )
        response = transport.get(MEMORIES, params=params)
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
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> list[SearchResult]:
        """Perform a semantic (vector) search over stored memories.

        Args:
            agent_id: Agent identifier to scope the search.
            invoker_id: Invoker/user identifier to scope the search.
            query: Natural-language search query (5–5000 characters).
            threshold: Minimum cosine similarity score (0.0–1.0). Default ``0.6``.
            limit: Maximum number of results (1–50). Default is ``10``.
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            List of :class:`SearchResult` objects.

        Raises:
            AgentMemoryValidationError: If required fields are empty, parameters are
                out of range (``query`` must be 5–5000 chars, ``threshold`` 0.0–1.0,
                ``limit`` 1–50), or tenant is missing for ``SUBSCRIBER``.
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
        transport = self._get_transport(access_strategy, tenant)
        payload: dict[str, Any] = {
            "agentID": agent_id,
            "invokerID": invoker_id,
            "query": query,
            "threshold": threshold,
            "top": limit,
        }
        response = transport.post(MEMORY_SEARCH, json=payload)
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
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
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
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            The created :class:`Message`.

        Raises:
            AgentMemoryValidationError: If any required field is empty or tenant is missing
                for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(
            agent_id=agent_id,
            invoker_id=invoker_id,
            message_group=message_group,
            content=content,
        )
        transport = self._get_transport(access_strategy, tenant)
        payload: dict[str, Any] = {
            "agentID": agent_id,
            "invokerID": invoker_id,
            "messageGroup": message_group,
            "role": role,
            "content": content,
        }
        if metadata is not None:
            payload["metadata"] = metadata
        data = transport.post(MESSAGES, json=payload)
        return Message.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_MESSAGE)
    def get_message(
        self,
        message_id: str,
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> Message:
        """Retrieve a message by ID.

        Args:
            message_id: The message identifier (UUID).
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            The :class:`Message`.

        Raises:
            AgentMemoryNotFoundError: If no message with the given ID exists.
            AgentMemoryValidationError: If ``message_id`` is empty or tenant is missing
                for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(message_id=message_id)
        transport = self._get_transport(access_strategy, tenant)
        data = transport.get(f"{MESSAGES}({message_id})")
        return Message.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_DELETE_MESSAGE)
    def delete_message(
        self,
        message_id: str,
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """Delete a message permanently.

        Args:
            message_id: The message identifier (UUID).
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Raises:
            AgentMemoryNotFoundError: If no message with the given ID exists.
            AgentMemoryValidationError: If ``message_id`` is empty or tenant is missing
                for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        _require_non_empty(message_id=message_id)
        transport = self._get_transport(access_strategy, tenant)
        transport.delete(f"{MESSAGES}({message_id})")

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
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
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
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            List of :class:`Message` objects.

        Raises:
            AgentMemoryValidationError: If ``limit`` < 1, ``offset`` < 0, a filter
                clause is invalid, or tenant is missing for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        if limit < 1:
            raise AgentMemoryValidationError("'limit' must be >= 1")
        if offset < 0:
            raise AgentMemoryValidationError("'offset' must be >= 0")
        if filters is not None:
            _validate_filter_clauses(filters, {"metadata", "content"})
        transport = self._get_transport(access_strategy, tenant)
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
        response = transport.get(MESSAGES, params=params)
        items, _ = extract_value_and_count(response)
        return [Message.from_dict(item) for item in items]

    # ── Admin operations ───────────────────────────────────────────────────────

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_RETENTION_CONFIG)
    def get_retention_config(
        self,
        *,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> RetentionConfig:
        """Retrieve the data retention configuration (singleton).

        Args:
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Returns:
            The current :class:`RetentionConfig`.

        Raises:
            AgentMemoryValidationError: If tenant is missing for ``SUBSCRIBER``.
            AgentMemoryHttpError: If the request fails.
        """
        transport = self._get_transport(access_strategy, tenant)
        data = transport.get(RETENTION_CONFIG)
        return RetentionConfig.from_dict(data)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_UPDATE_RETENTION_CONFIG)
    def update_retention_config(
        self,
        *,
        message_days: Optional[int] = None,
        memory_days: Optional[int] = None,
        usage_log_days: Optional[int] = None,
        access_strategy: Optional[AccessStrategy] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """Update the data retention configuration.

        Only the provided fields are updated. Set a field to ``0`` to
        explicitly pass zero, or omit it to leave unchanged.
        The server accepts ``null`` to disable cleanup for a category.

        Args:
            message_days: How long to keep messages (days).
            memory_days: How long to keep memories without access (days).
            usage_log_days: How long to keep access and search logs (days).
            access_strategy: Tenant access strategy. Overrides the client default when
                provided. Falls back to the default set on :func:`create_client`.
            tenant: Subscriber tenant subdomain. Overrides the client default when
                provided. Required (at call or client level) when strategy is ``SUBSCRIBER``.

        Raises:
            AgentMemoryValidationError: If no fields are provided, any provided value is
                negative, or tenant is missing for ``SUBSCRIBER``.
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
        transport = self._get_transport(access_strategy, tenant)
        payload: dict[str, Any] = {}
        if message_days is not None:
            payload["messageDays"] = message_days
        if memory_days is not None:
            payload["memoryDays"] = memory_days
        if usage_log_days is not None:
            payload["usageLogDays"] = usage_log_days
        transport.patch(RETENTION_CONFIG, json=payload)
