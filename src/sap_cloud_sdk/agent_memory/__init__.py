"""SAP Cloud SDK for Python — Agent Memory module.

The ``create_client()`` function auto-detects credentials from a mounted volume
or ``CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_*`` environment variables.

Usage::

    from sap_cloud_sdk.agent_memory import create_client, AccessStrategy

    # Subscriber tenant — strategy and tenant set once, inherited by all calls
    client = create_client(
        access_strategy=AccessStrategy.SUBSCRIBER,
        tenant="my-tenant-subdomain",
    )
    memories = client.list_memories(agent_id="my-agent", invoker_id="user-123")
"""

from typing import Optional

from sap_cloud_sdk.agent_memory._http_transport import HttpTransport
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory.config import (
    AgentMemoryConfig,
    _load_config_for_instance,
    _load_config_from_env,
)
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryConfigError,
    AgentMemoryError,
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
    AgentMemoryValidationError,
)
from sap_cloud_sdk.agent_memory._models import (
    AccessStrategy,
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)
from sap_cloud_sdk.agent_memory.utils._odata import FilterDefinition


def create_client(
    *,
    config: Optional[AgentMemoryConfig] = None,
    access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER,
    tenant: Optional[str] = None,
) -> AgentMemoryClient:
    """Create an :class:`AgentMemoryClient` with automatic credential detection.

    The binding loaded depends on ``access_strategy`` and ``tenant``:

    - ``SUBSCRIBER`` with ``tenant="acme-corp"`` — loads the subscriber
      binding from ``/etc/secrets/appfnd/hana-agent-memory/acme-corp/`` (or
      ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_*`` env vars).
    - ``PROVIDER`` — loads the provider binding from
      ``/etc/secrets/appfnd/hana-agent-memory/default/`` (or
      ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_*`` env vars).
    - Explicit ``config`` — uses the provided configuration directly.

    Args:
        config: Optional explicit configuration. When provided, binding
                discovery is skipped.
        access_strategy: Tenant access strategy for all operations.
                Defaults to ``SUBSCRIBER``.
        tenant: Subscriber tenant subdomain. Required when
                ``access_strategy=SUBSCRIBER``.

    Returns:
        A ready-to-use :class:`AgentMemoryClient`.

    Raises:
        AgentMemoryConfigError: If configuration is missing or invalid.
        AgentMemoryValidationError: If ``access_strategy=SUBSCRIBER`` and
                ``tenant`` is not provided.
    """
    try:
        if config is not None:
            resolved_config = config
        elif access_strategy is AccessStrategy.SUBSCRIBER and tenant:
            resolved_config = _load_config_for_instance(tenant)
        else:
            resolved_config = _load_config_from_env()

        transport = HttpTransport(resolved_config)
        return AgentMemoryClient(
            transport,
            access_strategy=access_strategy,
            tenant=tenant,
        )
    except AgentMemoryConfigError:
        raise
    except Exception as exc:
        raise AgentMemoryConfigError(
            f"Failed to create Agent Memory client: {exc}"
        ) from exc


__all__ = [
    "AccessStrategy",
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
