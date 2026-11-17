"""Extensibility module for SAP Cloud SDK for Python.

Enables agent developers to:

1. **Retrieve extension capability implementations at runtime** -- the active
   extension's tools (delivered via MCP servers) and custom instruction.
2. **Declare extension capabilities for A2A discovery** -- define what parts
   of the agent are extensible, for serialization into the agent's A2A card.

Basic usage::

    from sap_cloud_sdk.extensibility import create_client

    client = create_client("sap.ai:agent:myAgent:v1")
    ext_cap_impl = client.get_extension_capability_implementation(tenant=tenant_id)

    for server in ext_cap_impl.mcp_servers:
        print(server.ord_id, server.tool_names)

    if ext_cap_impl.instruction:
        print(ext_cap_impl.instruction)

A2A card serialization::

    from sap_cloud_sdk.extensibility import (
        ExtensionCapability,
        build_extension_capabilities,
    )

    capabilities = [
        ExtensionCapability(
            display_name="Onboarding Workflow",
            description="Add tools to the onboarding workflow.",
        ),
    ]
    extensions = build_extension_capabilities(capabilities)
"""

import logging
import os
from typing import Optional

from sap_cloud_sdk.core.telemetry import Module

_logger = logging.getLogger(__name__)


def _mock_file(name: str) -> str:
    """Return the absolute path to a mocks/<name> file relative to the working directory."""
    return os.path.join(os.getcwd(), "mocks", name)


# ---------------------------------------------------------------------------
# Dependency check — a2a-sdk is an optional extra
# ---------------------------------------------------------------------------

try:
    import a2a as _a2a  # noqa: F401
except ImportError as _exc:
    raise ImportError(
        "The 'a2a-sdk' package is required to use the extensibility module. "
        "Install it with: pip install sap-cloud-sdk[extensibility]"
    ) from _exc

from sap_cloud_sdk.extensibility._a2a import (
    EXTENSION_CAPABILITY_SCHEMA_VERSION,
    build_extension_capabilities,
)
from sap_cloud_sdk.extensibility._local_transport import (
    CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV,
    EXTENSIBILITY_MOCK_FILE,
    LocalTransport,
)
from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    DeploymentType,
    ExecutionMode,
    ExtensionCapability,
    ExtensionCapabilityImplementation,
    ExtensionSourceInfo,
    ExtensionSourceMapping,
    Hook,
    HookCapability,
    HookType,
    McpServer,
    N8nWorkflowConfig,
    OnFailure,
    ToolAdditions,
    Tools,
)
from sap_cloud_sdk.extensibility._noop_transport import NoOpTransport
from sap_cloud_sdk.extensibility._ums_transport import UmsTransport
from sap_cloud_sdk.extensibility.client import ExtensibilityClient
from sap_cloud_sdk.extensibility.config import ExtensibilityConfig, HookConfig
from sap_cloud_sdk.extensibility.exceptions import (
    ClientCreationError,
    ExtensibilityError,
    HookShortCircuit,
    TransportError,
)
from sap_cloud_sdk.extensibility._logging import configure_extension_logging
from sap_cloud_sdk.extensibility._mcp_patches import unwrap_buggy_mcp_otel_patches
from sap_cloud_sdk.extensibility._mcp_servers import resolve_mcp_servers


def create_client(
    agent_ord_id: str,
    *,
    config: Optional[ExtensibilityConfig] = None,
    _telemetry_source: Optional[Module] = None,
) -> ExtensibilityClient:
    """Create an :class:`ExtensibilityClient` for runtime extension lookups.

    Local mode is activated in two ways (checked in order):

    1. **Environment variable** ``CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE`` set to a
       file path -- the client reads extension data from that file.
    2. **File-presence detection** -- if ``mocks/extensibility.json`` exists at
       the repository root, it is used automatically.

    The environment variable takes precedence when both are present.  In either
    case the JSON file must use the same schema as the backend response
    (see :mod:`_local_transport`).

    This function never raises.  If the client cannot be constructed
    (e.g. missing destination credentials in local development), it logs
    the error and returns a client backed by a no-op transport that
    always returns empty results.  This ensures the agent can always
    start and operate with its built-in tools.

    Args:
        agent_ord_id: ORD ID of the agent (e.g.,
            ``"sap.ai:agent:myAgent:v1"``). Required for the backend transport
            to identify the agent when querying extensibility data.
        config: Optional configuration overrides for destination name,
            instance, and audit settings. If omitted, uses default
            :class:`ExtensibilityConfig`.
        _telemetry_source: Internal telemetry source identifier. Not intended for external use.

    Returns:
        A client ready for :meth:`ExtensibilityClient.get_extension_capability_implementation`.
    """
    effective = config or ExtensibilityConfig()
    _audit_kw = dict(
        _audit_channel_id=effective.audit_channel_id,
        _audit_service_name=effective.audit_service_name,
    )
    try:
        # 1. Env var takes precedence (explicit always wins)
        local_file = os.environ.get(CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV)
        if local_file:
            _logger.warning(
                "Local mock mode active: using LocalTransport backed by %s. "
                "This is intended for local development only and must not be "
                "used in production.",
                local_file,
            )
            transport = LocalTransport(local_file)
            return ExtensibilityClient(
                transport, _telemetry_source=_telemetry_source, **_audit_kw
            )

        # 2. File-presence detection at mocks/extensibility.json
        mock_path = _mock_file(EXTENSIBILITY_MOCK_FILE)
        if os.path.isfile(mock_path):
            _logger.warning(
                "Local mock mode active: using LocalTransport backed by %s. "
                "This is intended for local development only and must not be "
                "used in production.",
                mock_path,
            )
            transport = LocalTransport(mock_path)
            return ExtensibilityClient(
                transport, _telemetry_source=_telemetry_source, **_audit_kw
            )

        # 3. Cloud mode via extensibility service transport
        transport = UmsTransport(agent_ord_id, effective)
        return ExtensibilityClient(
            transport, _telemetry_source=_telemetry_source, **_audit_kw
        )
    except Exception:
        _logger.error(
            "Failed to create extensibility client. "
            "Returning no-op client. The agent will operate without extensions.",
            exc_info=True,
        )
        return ExtensibilityClient(NoOpTransport())


__all__ = [
    # Client
    "create_client",
    "ExtensibilityClient",
    # Local mode
    "LocalTransport",
    "CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV",
    "EXTENSIBILITY_MOCK_FILE",
    # A2A card helpers
    "build_extension_capabilities",
    "EXTENSION_CAPABILITY_SCHEMA_VERSION",
    # Models -- A2A card
    "ExtensionCapability",
    "ToolAdditions",
    "Tools",
    "HookCapability",
    # Models -- runtime
    "ExtensionCapabilityImplementation",
    "ExtensionSourceInfo",
    "ExtensionSourceMapping",
    "McpServer",
    "Hook",
    "N8nWorkflowConfig",
    # Constants
    "DEFAULT_EXTENSION_CAPABILITY_ID",
    # Enums
    "HookType",
    "DeploymentType",
    "ExecutionMode",
    "OnFailure",
    # Config
    "ExtensibilityConfig",
    "HookConfig",
    # Transports
    "UmsTransport",
    # Exceptions
    "ClientCreationError",
    "ExtensibilityError",
    "HookShortCircuit",
    "TransportError",
    # Utilities (always available — no optional deps)
    "configure_extension_logging",
    "unwrap_buggy_mcp_otel_patches",
    "resolve_mcp_servers",
    # LangChain adapters (lazy — require extensibility-langchain extra)
    "ExtensionTelemetryInterceptor",
    "load_extension_tools_langchain",
]

# ---------------------------------------------------------------------------
# Lazy loading for optional framework adapters
# ---------------------------------------------------------------------------

_LAZY: dict[str, tuple[str, str]] = {
    "ExtensionTelemetryInterceptor": (
        "sap_cloud_sdk.extensibility._langchain",
        "ExtensionTelemetryInterceptor",
    ),
    "load_extension_tools_langchain": (
        "sap_cloud_sdk.extensibility._tools_langchain",
        "load_extension_tools_langchain",
    ),
}

_LAZY_HINTS: dict[str, str] = {
    "ExtensionTelemetryInterceptor": "langchain-mcp-adapters",
    "load_extension_tools_langchain": "langchain-mcp-adapters",
}


def __getattr__(name: str) -> object:
    if name in _LAZY:
        module_path, attr = _LAZY[name]
        import importlib

        try:
            mod = importlib.import_module(module_path)
            value = getattr(mod, attr)
            globals()[name] = value
            return value
        except ImportError as exc:
            hint = _LAZY_HINTS.get(name, "")
            raise ImportError(
                f"'{name}' requires '{hint}' to be installed. "
                f"Install it with: pip install 'sap-cloud-sdk[extensibility-langchain]'"
            ) from exc
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
