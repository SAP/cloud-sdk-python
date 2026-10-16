"""In-memory thread registry for local development and unit testing."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryThreadConflictError,
    AgentMemoryThreadExpiredError,
    AgentMemoryThreadNotFoundError,
)
from sap_cloud_sdk.agent_memory.thread_registry._base import (
    BaseThreadRegistry,
    ThreadPage,
    ThreadRegistryEntry,
    _validate_ttl,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


@dataclass
class _StoredEntry:
    thread_id: str
    agent_id: str
    invoker_id: str
    description: Optional[str]
    metadata: Optional[dict[str, Any]]
    created_at: str
    thread_ttl: Optional[int] = None
    last_active: float = field(default_factory=time.monotonic)
    last_active_wall: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def is_expired(self, registry_ttl: Optional[int]) -> bool:
        effective = self.thread_ttl if self.thread_ttl is not None else registry_ttl
        if effective is None:
            return False
        return time.monotonic() - self.last_active > effective

    def touch(self) -> None:
        self.last_active = time.monotonic()
        self.last_active_wall = datetime.now(timezone.utc)

    def to_entry(self, registry_ttl: Optional[int] = None) -> ThreadRegistryEntry:
        effective_ttl = self.thread_ttl if self.thread_ttl is not None else registry_ttl
        if effective_ttl is not None:
            expires_iso: Optional[str] = (
                self.last_active_wall + timedelta(seconds=effective_ttl)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            expires_iso = None
        return ThreadRegistryEntry(
            threadId=self.thread_id,
            agentId=self.agent_id,
            invokerId=self.invoker_id,
            description=self.description,
            createdAt=self.created_at,
            updatedAt=self.last_active_wall.strftime("%Y-%m-%dT%H:%M:%SZ"),
            expiresAt=expires_iso,
            threadTtl=self.thread_ttl,
            metadata=self.metadata,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class InMemoryThreadRegistry(BaseThreadRegistry):
    """Dict-backed thread registry for local development and unit testing.

    State is in-process only and will not survive restarts.

    Implements a sliding idle TTL: expiry is computed as ``ttl_seconds``
    of inactivity. The window resets on every write. Expiry is checked lazily
    at read time — no background thread is needed.

    ``expiresAt`` in returned entries is computed from the wall-clock time of
    the last write plus the effective TTL, approximating the ``expiresAt`` field
    returned by the Agent Memory Service.

    Irreducible differences from the service-backed registry:

    - **Best-effort timing**: expiry time advances on every register/update
      (sliding); the service records server-side expiry at creation.
    - **Lazy eviction**: threads are evicted at the next read, not on a sweep
      schedule. A thread may appear live briefly after its true TTL.
    - **No restart survival**: all state is lost on process exit.

    Args:
        default_ttl_seconds: Registry-level default inactivity threshold.
            Applied when a per-call ``ttl_seconds`` is not supplied.
            ``None`` means threads never expire.
    """

    def __init__(
        self,
        *,
        default_ttl_seconds: Optional[int] = None,
    ) -> None:
        _validate_ttl(default_ttl_seconds)
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, _StoredEntry] = {}

    def _effective_ttl(self, ttl_seconds: Optional[int]) -> Optional[int]:
        return ttl_seconds if ttl_seconds is not None else self._default_ttl

    def _get_live(self, thread_id: str) -> _StoredEntry:
        entry = self._store.get(thread_id)
        if entry is None or entry.is_expired(self._default_ttl):
            raise AgentMemoryThreadNotFoundError(f"Thread '{thread_id}' not found")
        return entry

    @record_metrics(
        Module.AGENT_MEMORY, Operation.AGENT_MEMORY_CREATE_OR_REGISTER_THREAD
    )
    def create_or_register_thread(
        self,
        agent_id: str,
        invoker_id: str,
        *,
        thread_id: Optional[str] = None,
        description: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        _validate_ttl(ttl_seconds)
        ttl = self._effective_ttl(ttl_seconds)

        if thread_id is None:
            thread_id = str(uuid.uuid4())
            entry = _StoredEntry(
                thread_id=thread_id,
                agent_id=agent_id,
                invoker_id=invoker_id,
                description=description,
                metadata=metadata,
                created_at=_now_iso(),
                thread_ttl=ttl,
            )
            self._store[thread_id] = entry
            return entry.to_entry(self._default_ttl)

        existing = self._store.get(thread_id)
        if existing is not None:
            if existing.is_expired(self._default_ttl):
                raise AgentMemoryThreadExpiredError(
                    f"Thread '{thread_id}' has expired and cannot be re-created with the same ID"
                )
            if existing.agent_id != agent_id or existing.invoker_id != invoker_id:
                raise AgentMemoryThreadConflictError(
                    f"Thread '{thread_id}' is already registered by a different owner"
                )
            existing.touch()
            return existing.to_entry(self._default_ttl)

        entry = _StoredEntry(
            thread_id=thread_id,
            agent_id=agent_id,
            invoker_id=invoker_id,
            description=description,
            metadata=metadata,
            created_at=_now_iso(),
            thread_ttl=ttl,
        )
        self._store[thread_id] = entry
        return entry.to_entry(self._default_ttl)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_THREAD)
    def get_thread(
        self,
        thread_id: str,
        *,
        tenant_id: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        return self._get_live(thread_id).to_entry(self._default_ttl)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_LIST_THREADS)
    def list_threads(
        self,
        *,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> ThreadPage:
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError(f"limit must be a non-negative integer, got {limit!r}")
        resolved_offset = 0 if offset is None else offset
        if (
            not isinstance(resolved_offset, int)
            or isinstance(resolved_offset, bool)
            or resolved_offset < 0
        ):
            raise ValueError(f"offset must be a non-negative integer, got {offset!r}")
        all_matching = [
            entry.to_entry(self._default_ttl)
            for entry in self._store.values()
            if not entry.is_expired(self._default_ttl)
            and (agent_id is None or entry.agent_id == agent_id)
            and (invoker_id is None or entry.invoker_id == invoker_id)
        ]
        total = len(all_matching)
        if limit is not None and limit == 0:
            return ThreadPage(entries=[], total=total, limit=0, offset=resolved_offset)
        page = (
            all_matching[resolved_offset:]
            if limit is None
            else all_matching[resolved_offset : resolved_offset + limit]
        )
        return ThreadPage(
            entries=page,
            total=total,
            limit=len(page) if limit is None else limit,
            offset=resolved_offset,
        )

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_UPDATE_THREAD)
    def update_thread(
        self,
        thread_id: str,
        *,
        description: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        # PATCH-style merge: only fields the caller passed are modified. An
        # omitted ttl_seconds leaves the thread's existing TTL untouched.
        entry = self._get_live(thread_id)
        if description is not None:
            entry.description = description
        if metadata is not None:
            entry.metadata = metadata
        if ttl_seconds is not None:
            _validate_ttl(ttl_seconds)
            entry.thread_ttl = ttl_seconds
        entry.touch()
        return entry.to_entry(self._default_ttl)

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_DELETE_THREAD)
    def delete_thread(
        self,
        thread_id: str,
        *,
        tenant_id: Optional[str] = None,
    ) -> None:
        self._store.pop(thread_id, None)
