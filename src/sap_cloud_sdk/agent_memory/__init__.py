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
      ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_*`` env vars). Per-call
      tenant overrides load additional bindings lazily and cache them.
    - ``PROVIDER`` — loads the provider binding from
      ``/etc/secrets/appfnd/hana-agent-memory/default/`` (or
      ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_*`` env vars).
    - Explicit ``config`` — uses the provided configuration for all calls.
      Per-call tenant overrides are not supported when ``config`` is provided.

    Args:
        config: Optional explicit configuration. When provided, no binding
                discovery is performed and per-call tenant overrides are disabled.
        access_strategy: Default tenant access strategy for all client operations.
                Defaults to ``SUBSCRIBER``. Individual method calls may override
                this value.
        tenant: Default subscriber tenant subdomain. Required when
                ``access_strategy=SUBSCRIBER``. Individual method calls may
                override this value.

    Returns:
        A ready-to-use :class:`AgentMemoryClient`.

    Raises:
        AgentMemoryConfigError: If configuration is missing or invalid.
    """
    try:
        if config is not None:
            initial_config = config
            loader = None
        elif access_strategy is AccessStrategy.SUBSCRIBER and tenant:
            initial_config = _load_config_for_instance(tenant)
            loader = _load_config_for_instance
        else:
            initial_config = _load_config_from_env()
            loader = _load_config_for_instance

        transport = HttpTransport(initial_config)
        return AgentMemoryClient(
            transport,
            access_strategy=access_strategy,
            tenant=tenant,
            config_loader=loader,
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
