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

from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory.config import (
    AgentMemoryConfig,
    _make_config_factory,
)
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryConfigError,
    AgentMemoryError,
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
    AgentMemoryThreadConflictError,
    AgentMemoryThreadExpiredError,
    AgentMemoryThreadNotFoundError,
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
from sap_cloud_sdk.agent_memory.thread_registry import (
    BaseThreadRegistry,
    InMemoryThreadRegistry,
    SAPAgentMemoryThreadRegistry,
    ThreadPage,
    ThreadRegistryEntry,
    create_thread_registry,
)
from sap_cloud_sdk.core.protocol.http import (
    HttpClient,
    IasAuthProvider,
    XsuaaAuthProvider,
)
from sap_cloud_sdk.core.telemetry import Module


def _build_agent_memory_http(
    instance: str, config: Optional[AgentMemoryConfig]
) -> tuple[HttpClient, bool]:
    """Build an :class:`HttpClient` for the given config, returning (client, is_ias)."""
    # Explicit config is wrapped as a static factory; otherwise the binding is read
    # via a ConfigFactory that re-reads on each call to pick up secret rotation.
    config_factory = (
        (lambda: config) if config is not None else _make_config_factory(instance)
    )
    cfg = config_factory()
    is_ias = cfg.auth_mode == "ias"
    auth = (
        IasAuthProvider()
        if is_ias
        else XsuaaAuthProvider(config_factory, module=Module.AGENT_MEMORY)
    )
    return HttpClient(cfg.base_url, auth, timeout=cfg.timeout), is_ias


def create_client(
    *,
    instance: str = "default",
    config: Optional[AgentMemoryConfig] = None,
    access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER,
    tenant: Optional[str] = None,
) -> AgentMemoryClient:
    """Create an :class:`AgentMemoryClient` with automatic credential detection.

    The binding loaded depends on ``instance``, ``access_strategy``, and ``tenant``:

    - ``instance="default"`` (the default) — discovers the XSUAA-backed HANA Agent
      Memory binding at ``$SERVICE_BINDING_ROOT/hana-agent-memory/default/``
      (or ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_*`` env vars).
    - ``instance="my-agent-memory"`` — discovers the IAS-based Serverless Agent
      Memory binding at ``$SERVICE_BINDING_ROOT/hana-agent-memory/my-agent-memory/``.
      The SDK detects auth mode from the binding contents: ``uaa`` present → XSUAA,
      absent → IAS.
    - Explicit ``config`` — uses the provided configuration directly, ``instance``
      is ignored.

    Args:
        instance: Binding instance name declared in ``app.yaml``. Defaults to
            ``"default"``, which matches the XSUAA-backed HANA Agent Memory
            service. Serverless agents pass the name they declared in ``requires:``.
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
        http, is_ias = _build_agent_memory_http(instance, config)
        if is_ias:
            # IAS mode: calls are routed by the per-request token, not by an
            # XSUAA access strategy — tenant/access_strategy do not apply.
            return AgentMemoryClient(http, _ias_mode=True)
        return AgentMemoryClient(
            http,
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
    "AgentMemoryThreadConflictError",
    "AgentMemoryThreadExpiredError",
    "AgentMemoryThreadNotFoundError",
    "AgentMemoryValidationError",
    "FilterDefinition",
    "Memory",
    "Message",
    "MessageRole",
    "RetentionConfig",
    "SearchResult",
    "BaseThreadRegistry",
    "InMemoryThreadRegistry",
    "SAPAgentMemoryThreadRegistry",
    "ThreadPage",
    "ThreadRegistryEntry",
    "create_client",
    "create_thread_registry",
]
