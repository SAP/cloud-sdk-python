"""UMS GraphQL transport for the extensibility service.

Queries UMS directly (per destination) instead of going through the legacy HTTP
backend.  Each destination is resolved via the Destination SDK, then a
GraphQL query is sent to the UMS ``/graphql`` endpoint.

Authentication uses **client certificates (mTLS)**.  The certificate is
obtained from the resolved destination and written to a temporary file
for the duration of the HTTP request.
"""

from __future__ import annotations

import base64
import collections
import logging
import os
import tempfile
import threading
import time
from http import HTTPMethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

from sap_cloud_sdk.destination import Level
from sap_cloud_sdk.destination import create_client as create_destination_client
from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    DEFAULT_HOOK_TIMEOUT,
    DeploymentType,
    ExecutionMode,
    ExtensionCapabilityImplementation,
    ExtensionSourceInfo,
    ExtensionSourceMapping,
    Hook,
    HookType,
    McpServer,
    N8nWorkflowConfig,
    OnFailure,
)
from sap_cloud_sdk.extensibility.exceptions import TransportError

if TYPE_CHECKING:
    from sap_cloud_sdk.extensibility.config import ExtensibilityConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variable for UMS destination name construction
# ---------------------------------------------------------------------------

ENV_CONHOS_LANDSCAPE = "APPFND_CONHOS_LANDSCAPE"
ENV_UMS_DESTINATION_NAME = "APPFND_UMS_DESTINATION_NAME"
_UMS_DESTINATION_PREFIX = "sap-managed-runtime-ums-"

# ---------------------------------------------------------------------------
# GraphQL query
# ---------------------------------------------------------------------------

_GRAPHQL_QUERY_FRAGMENT = """\
    edges {
      node {
        id
        title
        extensionVersion
        solutionId
        capabilityImplementations {
          capabilityId
          instruction { text }
          tools {
            additions { type mcpConfig { globalTenantId ordId toolNames } }
          }
          hooks { id hookId type name onFailure timeout deploymentType canShortCircuit
            n8nWorkflowConfig { workflowId method }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      cursor
    }"""

_GRAPHQL_QUERY = (
    """\
query GetExtCapImplementations($filters: EXTHUB__ExtCapImplementationFilterInput) {
  EXTHUB__ExtCapImplementationInstances(
    filters: $filters
    first: 50
  ) {
%s
  }
}"""
    % _GRAPHQL_QUERY_FRAGMENT
)

_GRAPHQL_QUERY_WITH_CURSOR = (
    """\
query GetExtCapImplementations($filters: EXTHUB__ExtCapImplementationFilterInput, $after: String) {
  EXTHUB__ExtCapImplementationInstances(
    filters: $filters
    first: 50
    after: $after
  ) {
%s
  }
}"""
    % _GRAPHQL_QUERY_FRAGMENT
)

_GRAPHQL_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

_UMS_GRAPHQL_PATH = "/graphql"

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------

#: Time-to-live for cached UMS responses, in seconds (10 minutes).
_CACHE_TTL_SECONDS: int = 600

#: Maximum number of entries in the in-memory UMS response cache.
#: When the cache exceeds this size, expired entries are swept first,
#: then the least-recently-used entries are evicted.
_CACHE_MAX_SIZE: int = 256

#: Maximum number of pages to fetch when paginating UMS results.
#: Acts as a safety limit to prevent infinite loops (50 * 100 = 5 000 extensions).
_MAX_PAGES: int = 100

# ---------------------------------------------------------------------------
# Enum parsing helpers
# ---------------------------------------------------------------------------

_HOOK_TYPE_MAP: dict[str, HookType] = {member.value: member for member in HookType}
_ON_FAILURE_MAP: dict[str, OnFailure] = {member.value: member for member in OnFailure}
_DEPLOYMENT_TYPE_MAP: dict[str, DeploymentType] = {
    member.value: member for member in DeploymentType
}
_HTTP_METHOD_MAP: dict[str, HTTPMethod] = {
    member.value: member for member in HTTPMethod
}


def _parse_hook_type_safe(value: str) -> Optional[HookType]:
    """Return a ``HookType`` for *value*, or ``None`` if unknown."""
    return _HOOK_TYPE_MAP.get(value)


def _parse_on_failure_safe(value: str) -> OnFailure:
    """Return an ``OnFailure`` for *value*, defaulting to ``CONTINUE``."""
    result = _ON_FAILURE_MAP.get(value)
    if result is None and value:
        logger.warning("Unknown onFailure value %r; defaulting to CONTINUE", value)
    return result or OnFailure.CONTINUE


def _parse_deployment_type_safe(value: str) -> DeploymentType:
    """Return a ``DeploymentType`` for *value*, defaulting to ``UNKNOWN``."""
    result = _DEPLOYMENT_TYPE_MAP.get(value)
    if result is None and value:
        logger.warning("Unknown deploymentType value %r; defaulting to UNKNOWN", value)
    return result or DeploymentType.UNKNOWN


def _parse_method_safe(value: str) -> HTTPMethod:
    """Return an ``HTTPMethod`` for *value*, defaulting to ``POST``."""
    result = _HTTP_METHOD_MAP.get(value)
    if result is None and value:
        logger.warning("Unknown HTTP method %r; defaulting to POST", value)
    return result or HTTPMethod.POST


# ---------------------------------------------------------------------------
# Destination name resolution
# ---------------------------------------------------------------------------


def _ums_destination_name(config_override: Optional[str] = None) -> Optional[str]:
    """Construct the UMS destination name from configuration or environment.

    Resolution order:

    1. **Config override** -- if ``config.destination_name`` is set, use
       it directly.
    2. **Explicit env var override** -- if ``APPFND_UMS_DESTINATION_NAME``
       is set, use its value directly.  This is useful in subaccounts
       where the UMS destination follows a non-standard naming convention.
    3. **Landscape-based construction** -- the destination name is built as
       ``sap-managed-runtime-ums-{APPFND_CONHOS_LANDSCAPE}``.

    Args:
        config_override: Optional destination name from
            :class:`ExtensibilityConfig`.  Takes highest priority when set.

    Returns:
        The resolved UMS destination name, or ``None`` if no configuration
        or environment variables are available to determine it.
    """
    # 0. Config-level override takes highest priority
    if config_override:
        logger.debug(
            "Using UMS destination name from config override: %s",
            config_override,
        )
        return config_override

    # 1. Explicit env var override takes precedence
    override = os.environ.get(ENV_UMS_DESTINATION_NAME)
    if override:
        logger.debug(
            "Using UMS destination name from %s: %s",
            ENV_UMS_DESTINATION_NAME,
            override,
        )
        return override

    # 2. Construct from landscape (existing logic)
    landscape = os.environ.get(ENV_CONHOS_LANDSCAPE)
    if not landscape:
        logger.warning(
            "%s is not set; cannot construct UMS destination name. "
            "Set %s or %s to configure the UMS destination name.",
            ENV_CONHOS_LANDSCAPE,
            ENV_UMS_DESTINATION_NAME,
            ENV_CONHOS_LANDSCAPE,
        )
        return None

    destination_name = f"{_UMS_DESTINATION_PREFIX}{landscape}"
    logger.debug(
        "Resolved UMS destination name from %s: %s",
        ENV_CONHOS_LANDSCAPE,
        destination_name,
    )
    return destination_name


# ---------------------------------------------------------------------------
# Response transformation helpers
# ---------------------------------------------------------------------------


def _build_mcp_server(addition: Dict[str, Any]) -> McpServer:
    """Convert a UMS ``tools.additions[]`` entry into an :class:`McpServer`.

    The UMS schema nests ``ordId`` and ``toolNames`` under the
    ``mcpConfig`` object inside each addition.
    """
    mcp_config = addition.get("mcpConfig") or {}
    return McpServer(
        ord_id=mcp_config.get("ordId", ""),
        global_tenant_id=mcp_config.get("globalTenantId", ""),
        tool_names=mcp_config.get("toolNames"),
    )


def _build_hook(raw: Dict[str, Any]) -> Optional[Hook]:
    """Convert a UMS ``hooks[]`` entry into a :class:`Hook`.

    Maps fields from the UMS GraphQL schema:

    * ``id`` → ``id`` (DB UUID)
    * ``hookId`` → ``hook_id`` (developer-defined identifier)
    * ``type`` → ``type`` (parsed to :class:`HookType`)
    * ``name`` → ``name``
    * ``onFailure`` → ``on_failure`` (parsed to :class:`OnFailure`, default ``CONTINUE``)
    * ``timeout`` → ``timeout`` (default :data:`DEFAULT_HOOK_TIMEOUT`)
    * ``deploymentType`` → ``deployment_type`` (parsed to :class:`DeploymentType`, default ``N8N``)
    * ``canShortCircuit`` → ``can_short_circuit`` (default ``False``)
    * ``n8nWorkflowConfig`` → ``n8n_workflow_config`` (:class:`N8nWorkflowConfig`)

    Returns ``None`` when the hook type is unknown/missing.
    """
    hook_type = _parse_hook_type_safe(raw.get("type", ""))
    if hook_type is None:
        logger.warning(
            "Skipping hook with unknown type %r (hookId=%s)",
            raw.get("type"),
            raw.get("hookId"),
        )
        return None

    n8n_config = raw.get("n8nWorkflowConfig") or {}
    workflow_id = n8n_config.get("workflowId", "")
    if not workflow_id:
        logger.warning(
            "Skipping hook with missing workflowId (hookId=%s)",
            raw.get("hookId"),
        )
        return None

    deployment_type = _parse_deployment_type_safe(raw.get("deploymentType", ""))
    method = _parse_method_safe(n8n_config.get("method", "POST"))
    on_failure = _parse_on_failure_safe(raw.get("onFailure", ""))

    return Hook(
        id=raw.get("id", ""),
        hook_id=raw.get("hookId", ""),
        n8n_workflow_config=N8nWorkflowConfig(workflow_id=workflow_id, method=method),
        name=raw.get("name", ""),
        type=hook_type,
        deployment_type=deployment_type,
        timeout=raw.get("timeout", DEFAULT_HOOK_TIMEOUT),
        execution_mode=ExecutionMode.SYNC,
        on_failure=on_failure,
        order=0,
        can_short_circuit=raw.get("canShortCircuit", False),
    )


def _build_source_mapping(
    nodes: List[Dict[str, Any]],
    mcp_servers: List[McpServer],
    hooks: List[Hook],
) -> ExtensionSourceMapping:
    """Build a source mapping from per-node title to contributed tools/hooks.

    Each node has a ``title`` (the extension name) and a list of
    ``capabilityImplementations`` whose tools and hooks were contributed
    by that extension.
    """
    tool_map: Dict[str, ExtensionSourceInfo] = {}
    hook_map: Dict[str, ExtensionSourceInfo] = {}

    for node in nodes:
        title = node.get("title", "")
        source_info = ExtensionSourceInfo(
            extension_name=title,
            extension_version=node.get("extensionVersion", ""),
            extension_id=node.get("id", ""),
            solution_id=node.get("solutionId") or "",
        )

        for cap_impl in node.get("capabilityImplementations", []):
            # Map tools (toolNames are nested under mcpConfig)
            additions = (cap_impl.get("tools") or {}).get("additions", [])
            for addition in additions:
                mcp_config = addition.get("mcpConfig") or {}
                tool_names = mcp_config.get("toolNames") or []
                for tool_name in tool_names:
                    tool_map[tool_name] = source_info

            # Map hooks (use id as the mapping key)
            for raw_hook in cap_impl.get("hooks") or []:
                hook_id = raw_hook.get("id", "")
                if hook_id:
                    hook_map[hook_id] = source_info

    return ExtensionSourceMapping(tools=tool_map, hooks=hook_map)


def _transform_ums_response(
    data: Dict[str, Any],
    capability_id: str,
) -> ExtensionCapabilityImplementation:
    """Transform a UMS GraphQL response into an :class:`ExtensionCapabilityImplementation`.

    Args:
        data: The ``data`` portion of the GraphQL JSON response.
        capability_id: The requested capability ID to filter by.

    Returns:
        A populated ``ExtensionCapabilityImplementation``.
    """
    edges = data.get("EXTHUB__ExtCapImplementationInstances", {}).get("edges", [])

    extension_names: List[str] = []
    mcp_servers: List[McpServer] = []
    hooks: List[Hook] = []
    instructions: List[str] = []
    nodes: List[Dict[str, Any]] = []

    for edge in edges:
        node = edge.get("node", {})
        nodes.append(node)
        title = node.get("title", "")
        if title:
            extension_names.append(title)

        for cap_impl in node.get("capabilityImplementations", []):
            # Filter by capability_id
            if cap_impl.get("capabilityId") != capability_id:
                continue

            # Instruction
            raw_instruction = cap_impl.get("instruction")
            if raw_instruction and isinstance(raw_instruction, dict):
                text = raw_instruction.get("text")
                if text:
                    instructions.append(text)

            # MCP servers from tools.additions
            additions = (cap_impl.get("tools") or {}).get("additions", [])
            for addition in additions:
                mcp_servers.append(_build_mcp_server(addition))

            # Hooks
            for raw_hook in cap_impl.get("hooks") or []:
                hook = _build_hook(raw_hook)
                if hook is not None:
                    hooks.append(hook)

    source = _build_source_mapping(nodes, mcp_servers, hooks)

    instruction = "\n\n".join(instructions) if instructions else None

    return ExtensionCapabilityImplementation(
        capability_id=capability_id,
        extension_names=extension_names,
        mcp_servers=mcp_servers,
        instruction=instruction,
        hooks=hooks,
        source=source,
    )


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class UmsTransport:
    """UMS GraphQL transport for the extensibility service.

    Resolves the UMS destination via the Destination SDK, then sends
    a GraphQL query to the UMS ``/graphql`` endpoint and transforms
    the response into an :class:`ExtensionCapabilityImplementation`.

    The destination name is resolved in order:

    1. ``config.destination_name`` (explicit config override).
    2. ``APPFND_UMS_DESTINATION_NAME`` environment variable.
    3. ``sap-managed-runtime-ums-{APPFND_CONHOS_LANDSCAPE}`` (constructed).
    4. ``EXTENSIBILITY_SERVICE`` (fallback with warning).

    Args:
        agent_ord_id: ORD ID of the agent.
        config: Extensibility configuration with optional
            ``destination_name`` override and ``destination_instance``.
    """

    def __init__(self, agent_ord_id: str, config: ExtensibilityConfig) -> None:
        self._agent_ord_id = agent_ord_id
        self._config = config
        self._destination_name = _ums_destination_name(config.destination_name)
        self._dest_client = create_destination_client(
            instance=config.destination_instance
        )
        self._cache: collections.OrderedDict[
            tuple[str, str],
            tuple[float, List[Dict[str, Any]]],
        ] = collections.OrderedDict()
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # get_extension_capability_implementation
    # ------------------------------------------------------------------

    def get_extension_capability_implementation(
        self,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
        skip_cache: bool = False,
        tenant: str = "",
    ) -> ExtensionCapabilityImplementation:
        """Fetch extension capability implementation from UMS via GraphQL.

        Resolves the UMS destination, sends the
        ``EXTHUB__ExtCapImplementationInstances`` GraphQL query, and
        transforms the response into an
        :class:`ExtensionCapabilityImplementation`.

        Results are cached in-memory for 10 minutes (see
        :data:`_CACHE_TTL_SECONDS`), keyed by
        ``(tenant, capability_id)``.
        Set *skip_cache* to ``True`` to bypass the cache and fetch a fresh
        result -- the fresh result will still be written back into the
        cache so that subsequent normal reads benefit from the update.

        Args:
            capability_id: Extension capability ID to filter by.
                Defaults to ``"default"``.
            skip_cache: When ``True``, bypass the in-memory cache and
                fetch a fresh result from UMS.  The fresh result is
                written back into the cache.  Defaults to ``False``.
            tenant: Tenant ID for the request.  Included in the GraphQL
                query as ``agent.uclSystemInstance.localTenantIdIn``
                and sent as the ``X-Tenant`` HTTP header.  Also used
                as a cache isolation key.

        Returns:
            Parsed ``ExtensionCapabilityImplementation`` from UMS.

        Raises:
            TransportError: If destination resolution, HTTP communication,
                or response parsing fails.
        """
        # Guard: destination name must be resolved
        if self._destination_name is None:
            raise TransportError(
                "UMS destination name could not be resolved. "
                "Set the APPFND_UMS_DESTINATION_NAME or "
                "APPFND_CONHOS_LANDSCAPE environment variable, or provide "
                "a destination_name in ExtensibilityConfig."
            )

        # 0. Cache lookup ------------------------------------------------
        cache_key = (tenant, capability_id)
        all_edges: List[Dict[str, Any]] = []

        if not skip_cache:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    ts, cached_edges = cached
                    if (time.monotonic() - ts) < _CACHE_TTL_SECONDS:
                        logger.debug(
                            "UMS cache hit for tenant=%s capability_id=%s",
                            tenant,
                            capability_id,
                        )
                        self._cache.move_to_end(cache_key)
                        all_edges = cached_edges
                        combined_data: Dict[str, Any] = {
                            "EXTHUB__ExtCapImplementationInstances": {
                                "edges": all_edges
                            },
                        }
                        return _transform_ums_response(combined_data, capability_id)
                    logger.debug(
                        "UMS cache expired for tenant=%s capability_id=%s",
                        tenant,
                        capability_id,
                    )

        # 1. Resolve destination -----------------------------------------
        try:
            dest = self._dest_client.get_destination(
                self._destination_name, level=Level.SUB_ACCOUNT
            )
        except Exception as exc:
            raise TransportError(
                f"Failed to resolve destination '{self._destination_name}': {exc}"
            ) from exc

        if dest is None:
            raise TransportError(
                f"Destination '{self._destination_name}' not found in Destination Service."
            )

        base_url = dest.url
        if base_url is None:
            raise TransportError(
                f"Destination '{self._destination_name}' has no URL configured."
            )

        # 2. Extract client certificate ----------------------------------
        if not dest.certificates:
            raise TransportError(
                f"Destination '{self._destination_name}' has no "
                f"client certificates. UmsTransport requires mTLS via "
                f"ClientCertificateAuthentication."
            )

        cert = dest.certificates[0]
        try:
            cert_bytes = base64.b64decode(cert.content)
        except Exception as exc:
            raise TransportError(
                f"Failed to decode client certificate '{cert.name}': {exc}"
            ) from exc

        # 3. Build GraphQL request --------------------------------------
        url = f"{base_url.rstrip('/')}{_UMS_GRAPHQL_PATH}"

        agent_filter: dict[str, Any] = {
            "ordIdEquals": self._agent_ord_id,
            "uclSystemInstance": {
                "localTenantIdIn": tenant,
            },
        }

        filters: dict[str, Any] = {"agent": agent_filter}

        variables: dict[str, Any] = {
            "filters": filters,
        }

        request_headers = {
            **_GRAPHQL_HEADERS,
            "X-Tenant": tenant,
        }

        # 4. Send paginated requests with mTLS --------------------------
        all_edges = []
        cursor: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pem") as cert_file:
                cert_file.write(cert_bytes)
                cert_file.flush()

                with httpx.Client(cert=cert_file.name) as client:
                    for _ in range(_MAX_PAGES):
                        if cursor is not None:
                            query = _GRAPHQL_QUERY_WITH_CURSOR
                            variables["after"] = cursor
                        else:
                            query = _GRAPHQL_QUERY
                            variables.pop("after", None)

                        gql_body = {
                            "query": query,
                            "variables": variables,
                        }
                        response = client.post(
                            url,
                            json=gql_body,
                            headers=request_headers,
                        )

                        # 5. Parse response ---------------------------------
                        try:
                            response.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            raise TransportError(
                                f"UMS returned HTTP {response.status_code}: "
                                f"{response.text}"
                            ) from exc

                        try:
                            body = response.json()
                        except Exception as exc:
                            raise TransportError(
                                f"Failed to parse UMS response as JSON: {exc}"
                            ) from exc

                        # Check for GraphQL-level errors
                        if "errors" in body:
                            error_messages = [
                                e.get("message", "Unknown error")
                                for e in body["errors"]
                            ]
                            raise TransportError(
                                f"UMS GraphQL errors: {'; '.join(error_messages)}"
                            )

                        data = body.get("data")
                        if data is None:
                            raise TransportError(
                                "UMS response is missing the 'data' field."
                            )

                        connection = data.get(
                            "EXTHUB__ExtCapImplementationInstances", {}
                        )
                        all_edges.extend(connection.get("edges", []))

                        # Check for next page
                        page_info = connection.get("pageInfo") or {}
                        if not page_info.get("hasNextPage", False):
                            break
                        cursor = page_info.get("cursor")

        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"HTTP request to UMS endpoint failed: {exc}") from exc

        # 6. Populate cache ----------------------------------------------
        now = time.monotonic()

        with self._cache_lock:
            # Evict expired entries first.
            expired_keys = [
                k
                for k, (ts, _) in self._cache.items()
                if (now - ts) >= _CACHE_TTL_SECONDS
            ]
            for k in expired_keys:
                del self._cache[k]

            # If still at capacity, evict the least-recently-used entry.
            while len(self._cache) >= _CACHE_MAX_SIZE:
                self._cache.popitem(last=False)

            self._cache[cache_key] = (now, all_edges)

        # 7. Transform -----------------------------------------------------------
        combined_data: Dict[str, Any] = {
            "EXTHUB__ExtCapImplementationInstances": {"edges": all_edges},
        }
        result = _transform_ums_response(combined_data, capability_id)

        return result
