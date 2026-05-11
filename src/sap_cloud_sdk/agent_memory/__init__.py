"""SAP Cloud SDK for Python — Agent Memory module.

The ``create_client()`` function auto-detects credentials from a mounted volume
or ``CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_*`` environment variables.

Usage::

    from sap_cloud_sdk.agent_memory import create_client

    client = create_client()
    memories = client.list_memories(agent_id="my-agent", invoker_id="user-123")
"""

from typing import Optional

from sap_cloud_sdk.agent_memory._http_transport import HttpTransport
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig, _load_config_from_env
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryConfigError,
    AgentMemoryError,
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
    AgentMemoryValidationError,
)
from sap_cloud_sdk.agent_memory._models import (
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)
from sap_cloud_sdk.agent_memory.utils._odata import FilterDefinition


def create_client(*, config: Optional[AgentMemoryConfig] = None) -> AgentMemoryClient:
    """Create an :class:`AgentMemoryClient` with automatic credential detection.

    Args:
        config: Optional explicit configuration. If ``None``, credentials are
                loaded from the mounted volume at
                ``/etc/secrets/appfnd/hana-agent-memory/default/`` or from
                ``CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_*`` environment variables.

    Returns:
        A ready-to-use :class:`AgentMemoryClient`.

    Raises:
        AgentMemoryConfigError: If configuration is missing or invalid.
    """
    try:
        resolved_config = config if config is not None else _load_config_from_env()
        transport = HttpTransport(resolved_config)
        return AgentMemoryClient(transport)
    except AgentMemoryConfigError:
        raise
    except Exception as exc:
        raise AgentMemoryConfigError(
            f"Failed to create Agent Memory client: {exc}"
        ) from exc


__all__ = [
    "AgentMemoryClient",
    "AgentMemoryConfig",
    "AgentMemoryError",
    "AgentMemoryConfigError",
    "AgentMemoryHttpError",
    "AgentMemoryNotFoundError",
    "AgentMemoryValidationError",
    "FilterDefinition",
    "Memory",
    "Message",
    "MessageRole",
    "RetentionConfig",
    "SearchResult",
    "create_client",
]
