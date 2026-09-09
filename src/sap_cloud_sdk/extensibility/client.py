"""Extensibility service client."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional, Union

from a2a.types import Message
from pydantic_core import ValidationError

from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.agentgateway import create_client as create_agw_client
from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    ExtensionCapabilityImplementation,
    Hook,
)
from sap_cloud_sdk.extensibility.exceptions import ExtensibilityError, TransportError

if TYPE_CHECKING:
    from sap_cloud_sdk.extensibility._local_transport import LocalTransport
    from sap_cloud_sdk.extensibility._noop_transport import NoOpTransport
    from sap_cloud_sdk.extensibility._ums_transport import UmsTransport

    Transport = Union[LocalTransport, NoOpTransport, UmsTransport]

logger = logging.getLogger(__name__)


class ExtensibilityClient:
    """Client for SAP Extensibility operations.

    Retrieves extension capability implementations (MCP servers and instructions)
    from the extensibility service backend.

    Note:
        Do not instantiate this class directly. Use :func:`create_client` instead,
        which wires the transport and configuration.

    Example:
        ```python
        from sap_cloud_sdk.extensibility import create_client

        client = create_client("sap.ai:agent:myAgent:v1")
        ext = client.get_extension_capability_implementation(tenant=tenant_id)
        ```
    """

    def __init__(
        self, transport: Transport, _telemetry_source: Optional[Module] = None
    ) -> None:
        """Initialize the client with a transport.

        Warning:
            For internal and testing use. Use :func:`create_client` in application code.

        Args:
            transport: Configured transport for extensibility requests.
                Either :class:`UmsTransport` (cloud), :class:`LocalTransport`
                (local dev), or :class:`NoOpTransport` (graceful degradation).
            _telemetry_source: Internal telemetry source identifier. Not intended for external use.
        """
        self._transport = transport
        self._telemetry_source = _telemetry_source

    @record_metrics(
        Module.EXTENSIBILITY,
        Operation.EXTENSIBILITY_GET_EXTENSION_CAPABILITY_IMPLEMENTATION,
    )
    def get_extension_capability_implementation(
        self,
        *,
        tenant: str,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
        skip_cache: bool = False,
    ) -> ExtensionCapabilityImplementation:
        """Retrieve the active extension's contribution for a capability.

        On failure (service unavailable, destination errors, etc.), logs the error
        and returns an empty ``ExtensionCapabilityImplementation`` so the agent can
        continue with built-in tools only.

        Args:
            tenant: Tenant ID for the request.  Used to filter extensions
                in the GraphQL query (via
                ``agent.uclSystemInstance.localTenantIdIn``) and sent as
                the ``X-Tenant`` HTTP header.  Also used as a cache
                isolation key so that different tenants receive their own
                cached results.  Typically extracted from the incoming
                request's JWT.
            capability_id: Extension capability ID to look up. Defaults to ``"default"``.
            skip_cache: When ``True``, bypass any transport-level cache and
                fetch a fresh result.  Useful for ORD document creation or
                other scenarios that require up-to-date data.  The fresh
                result is still written back into the cache so that
                subsequent normal reads benefit.  Defaults to ``False``.

        Returns:
            Parsed implementation from the extensibility backend, or an empty result on any error.

        Example::

            from sap_cloud_sdk.extensibility import create_client

            client = create_client("sap.ai:agent:myAgent:v1")
            ext = client.get_extension_capability_implementation(
                tenant="1d2e1a41-a28b-431f-9e3f-42e9704bfa75",
            )
        """
        logger.info("Fetching extension capabilities for tenant=%s", tenant)
        try:
            return self._transport.get_extension_capability_implementation(
                capability_id=capability_id,
                skip_cache=skip_cache,
                tenant=tenant,
            )
        except Exception:
            logger.error(
                "Failed to retrieve extension capability implementation. "
                "Returning empty result. The agent will continue with built-in tools only.",
                exc_info=True,
            )
            return ExtensionCapabilityImplementation(capability_id=capability_id)

    async def _discover_n8n_tools(
        self, agw_client: Any, hook: Hook, user_token: Optional[str]
    ) -> Any:
        tools = await agw_client.list_mcp_tools(user_token=user_token or None)

        tool_name = hook.n8n_workflow_config.tool_name
        card_ord_id = hook.n8n_workflow_config.card_ord_id

        hook_tool = next(
            (
                t
                for t in tools
                if t.name == tool_name and t.server_name == card_ord_id
            ),
            None,
        )
        if hook_tool is None:
            raise ExtensibilityError(
                f"MCP tool '{tool_name}' on server '{card_ord_id}' "
                "not found via Agent Gateway."
            )
        logger.info("Discovered hook tool: name=%s server=%s", tool_name, card_ord_id)
        return hook_tool

    async def _execute_workflow_via_agw(
        self,
        agw_client: Any,
        hook_tool: Any,
        hook: Hook,
        user_token: Optional[str],
        message: Optional[Any],
        headers: Optional[dict],
    ) -> Optional[Message]:
        message_body = message.model_dump(mode="json") if message is not None else {}
        tool_arguments = {
            "inputs": {
                "type": "webhook",
                "webhookData": {
                    "method": hook.n8n_workflow_config.method,
                    "query": {},
                    "body": message_body,
                    "headers": headers or {},
                },
            },
        }
        logger.info(
            "Calling hook tool=%s server=%s",
            hook.n8n_workflow_config.tool_name,
            hook.n8n_workflow_config.card_ord_id,
        )
        try:
            result_str = await agw_client.call_mcp_tool(
                hook_tool,
                user_token=user_token or None,
                **tool_arguments,  # type: ignore[arg-type]
            )
        except Exception as exc:
            raise TransportError(
                f"AGW tool call for '{hook.n8n_workflow_config.tool_name}' failed: {exc}"
            ) from exc

        try:
            data = json.loads(result_str)
        except Exception as exc:
            raise TransportError(f"Could not parse hook response: {exc}") from exc

        try:
            return Message(**data) if data else None
        except (TypeError, ValidationError) as exc:
            raise ExtensibilityError(
                f"Hook response did not conform to the A2A Message protocol: {exc}"
            ) from exc

    @record_metrics(
        Module.EXTENSIBILITY,
        Operation.EXTENSIBILITY_CALL_HOOK,
    )
    async def call_hook_agw(
        self,
        hook: Hook,
        user_token: Optional[str] = None,
        message: Optional[Any] = None,
        headers: Optional[dict] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> Optional[Message]:
        """Call a hook via Agent Gateway MCP tool invocation.

        Discovers the hook's MCP tool via Agent Gateway by matching ``tool_name``
        and ``card_ord_id`` from the hook config, then calls it and returns
        the result.

        Auth and endpoint resolution are handled internally by an AGW client
        created from ``tenant_subdomain`` — no manual token or URL configuration
        is required.

        Args:
            hook: Hook configuration (tool name, card ORD ID, method, timeout).
            user_token: Optional user token forwarded to the Agent Gateway client
                for MCP tool discovery and invocation.
            message: Optional A2A ``Message`` payload serialised into the webhook
                body sent to the n8n workflow.
            headers: Optional HTTP headers included in the webhook data passed to
                the n8n workflow.
            tenant_subdomain: Tenant subdomain used to instantiate the Agent
                Gateway client. Pass ``None`` to use the default subdomain.

        Returns:
            Parsed ``Message`` from the hook tool response, or ``None``
            if the hook completed successfully but produced no message.

        Raises:
            TransportError: On AGW tool call errors or unparseable responses.
            ExtensibilityError: When the hook tool is not found via Agent Gateway,
                or the hook response does not conform to the A2A Message protocol.

        Example:
            ```python
            from sap_cloud_sdk.extensibility import create_client

            client = create_client("sap.ai:agent:myAgent:v1")
            impl = client.get_extension_capability_implementation(tenant="tenant-abc")

            if impl.hooks:
                result = await client.call_hook_agw(
                    hook=impl.hooks[0],
                    user_token="my-user-token",
                    message=my_message,
                    tenant_subdomain="my-tenant",
                )
            ```
        """
        agw_client = create_agw_client(
            tenant_subdomain, _telemetry_source=Module.EXTENSIBILITY
        )
        logger.info(
            "AGW client created successfully for tenant_subdomain=%s", tenant_subdomain
        )
        hook_tool = await self._discover_n8n_tools(agw_client, hook, user_token)
        logger.info("Discovered n8n workflow tool")
        return await self._execute_workflow_via_agw(
            agw_client, hook_tool, hook, user_token, message, headers
        )
