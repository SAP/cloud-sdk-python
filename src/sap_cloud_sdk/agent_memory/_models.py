"""Data models for the Agent Memory service (v1 API).

Each model exposes a ``from_dict()`` class method that maps the API response
payload to a typed Python object.

When migrating to a new API version, only the ``from_dict()`` methods and field
definitions in this file need to be updated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class MessageRole(str, Enum):
    """Role of the message author."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"


def _parse_metadata(raw: Any) -> Optional[dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"raw": raw}
    return None


@dataclass
class Memory:
    """Represents a memory entry with automatic vector embeddings.

    Attributes:
        id: Unique memory identifier (UUID).
        agent_id: Identifier of the agent that owns this memory.
        invoker_id: Identifier of the user or invoker.
        content: The memory text content.
        metadata: Optional metadata dict (Map type in OData).
        create_timestamp: ISO-8601 creation timestamp (read-only, set by server).
        update_timestamp: ISO-8601 last-update timestamp (read-only, set by server).
    """

    id: str
    agent_id: str
    invoker_id: str
    content: str
    metadata: Optional[dict[str, Any]] = None
    create_timestamp: Optional[str] = None
    update_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        """Create a ``Memory`` from an API response dictionary."""
        return cls(
            id=data.get("id", ""),
            agent_id=data.get("agentID", ""),
            invoker_id=data.get("invokerID", ""),
            content=data.get("content", ""),
            metadata=_parse_metadata(data.get("metadata")),
            create_timestamp=data.get("createTimestamp"),
            update_timestamp=data.get("updateTimestamp"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d: dict[str, Any] = {
            "id": self.id,
            "agentID": self.agent_id,
            "invokerID": self.invoker_id,
            "content": self.content,
            "createTimestamp": self.create_timestamp,
            "updateTimestamp": self.update_timestamp,
        }
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


@dataclass
class SearchResult:
    """Represents a memory search result with similarity scores.

    Returned by the ``search_memories`` operation.

    Attributes:
        id: Unique memory identifier (UUID).
        agent_id: Identifier of the agent that owns this memory.
        invoker_id: Identifier of the user or invoker.
        content: The memory text content.
        similarity: Cosine similarity score (0.0–1.0).
        metadata: Optional metadata dict.
        create_timestamp: ISO-8601 creation timestamp.
        update_timestamp: ISO-8601 last-update timestamp.
    """

    id: str
    agent_id: str
    invoker_id: str
    content: str
    similarity: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None
    create_timestamp: Optional[str] = None
    update_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchResult:
        """Create a ``SearchResult`` from an API response dictionary."""
        return cls(
            id=data.get("id", ""),
            agent_id=data.get("agentID", ""),
            invoker_id=data.get("invokerID", ""),
            content=data.get("content", ""),
            similarity=data.get("similarity"),
            metadata=_parse_metadata(data.get("metadata")),
            create_timestamp=data.get("createTimestamp"),
            update_timestamp=data.get("updateTimestamp"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d: dict[str, Any] = {
            "id": self.id,
            "agentID": self.agent_id,
            "invokerID": self.invoker_id,
            "content": self.content,
            "similarity": self.similarity,
            "createTimestamp": self.create_timestamp,
            "updateTimestamp": self.update_timestamp,
        }
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


@dataclass
class Message:
    """Represents a chat message in the Agent Memory system.

    Messages belonging to the same logical conversation are grouped
    via the ``message_group`` field.

    Attributes:
        id: Unique message identifier (UUID, read-only).
        agent_id: Identifier of the agent.
        invoker_id: Identifier of the user or invoker.
        message_group: Group identifier for conversation threading.
        role: Author role (USER, ASSISTANT, SYSTEM, TOOL). Nullable per API spec.
        content: The message text content.
        metadata: Optional metadata dict.
        create_timestamp: ISO-8601 creation timestamp (read-only, set by server).
    """

    id: str
    agent_id: str
    invoker_id: str
    message_group: str
    content: str
    role: Optional[MessageRole] = None
    metadata: Optional[dict[str, Any]] = None
    create_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create a ``Message`` from an API response dictionary."""
        raw_role = data.get("role")
        return cls(
            id=data.get("id", ""),
            agent_id=data.get("agentID", ""),
            invoker_id=data.get("invokerID", ""),
            message_group=data.get("messageGroup", ""),
            content=data.get("content", ""),
            role=MessageRole(raw_role) if raw_role else None,
            metadata=_parse_metadata(data.get("metadata")),
            create_timestamp=data.get("createTimestamp"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d: dict[str, Any] = {
            "id": self.id,
            "agentID": self.agent_id,
            "invokerID": self.invoker_id,
            "messageGroup": self.message_group,
            "content": self.content,
            "createTimestamp": self.create_timestamp,
        }
        if self.role is not None:
            d["role"] = self.role
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


# ── Admin models ──────────────────────────────────────────────────────────────


@dataclass
class RetentionConfig:
    """Represents the data retention configuration (singleton).

    Manages data retention policies across different data categories.
    Set a field to ``None`` to disable automatic cleanup for that category.

    Attributes:
        id: Config identifier (integer, read-only, set by server).
        message_days: How long to keep messages (days). ``None`` disables cleanup.
        memory_days: How long to keep memories without access (days). ``None`` disables cleanup.
        usage_log_days: How long to keep access and search logs (days). ``None`` disables cleanup.
        create_timestamp: ISO-8601 creation timestamp (read-only).
        update_timestamp: ISO-8601 last-update timestamp (read-only).
    """

    id: Optional[int]
    message_days: Optional[int] = None
    memory_days: Optional[int] = None
    usage_log_days: Optional[int] = None
    create_timestamp: Optional[str] = None
    update_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetentionConfig:
        """Create a ``RetentionConfig`` from an API response dictionary."""
        return cls(
            id=data.get("id"),
            message_days=data.get("messageDays"),
            memory_days=data.get("memoryDays"),
            usage_log_days=data.get("usageLogDays"),
            create_timestamp=data.get("createTimestamp"),
            update_timestamp=data.get("updateTimestamp"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "messageDays": self.message_days,
            "memoryDays": self.memory_days,
            "usageLogDays": self.usage_log_days,
            "createTimestamp": self.create_timestamp,
            "updateTimestamp": self.update_timestamp,
        }
