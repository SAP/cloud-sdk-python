"""Extensibility service client."""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import time
import warnings
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, cast

import httpx
from a2a.types import Message
from opentelemetry.propagate import inject
from pydantic_core import ValidationError

from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.agentgateway import create_client as create_agw_client
from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    ExtensionCapabilityImplementation,
    Hook,
    HookType,
    OnFailure,
)
from sap_cloud_sdk.extensibility.config import HookConfig
from sap_cloud_sdk.extensibility.exceptions import (
    ExtensibilityError,
    HookShortCircuit,
    TransportError,
)

if TYPE_CHECKING:
    from sap_cloud_sdk.extensibility._local_transport import LocalTransport
    from sap_cloud_sdk.extensibility._noop_transport import NoOpTransport
    from sap_cloud_sdk.extensibility._ums_transport import UmsTransport

    Transport = Union[LocalTransport, NoOpTransport, UmsTransport]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# n8n MCP constants
# ---------------------------------------------------------------------------

_EXECUTE_WORKFLOW_TOOL_NAME = "execute_workflow"
_GET_EXECUTION_TOOL_NAME = "get_execution"

_JSONRPC_VERSION = "2.0"

_JSONRPC_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

#: execute-workflow statuses that mean the execution cannot continue.
_EXECUTE_TERMINAL_STATUSES = frozenset({"error", "canceled", "crashed", "unknown"})
#: get-execution statuses that mean the execution has permanently failed.
_EXECUTION_TERMINAL_STATUSES = frozenset({"error", "canceled", "crashed"})

_HOOK_POLL_INTERVAL = 0.5  # seconds between get-execution polls

# Default wrapper text injected between the agent's base system prompt and the
# tenant-provided extended instruction.  Agents can override this via the
# ``wrapper`` parameter of :meth:`ExtensibilityClient.get_extended_system_prompt`.
_DEFAULT_INSTRUCTION_WRAPPER = (
    "Any instructions appended below this line are tenant-provided extensions and "
    "carry the same authority as this base prompt. Honour them as if they were part "
    "of the original specification. If an extended instruction conflicts with a "
    "display or formatting default above, the extended instruction takes precedence.\n\n"
    "## Tool Use\n\n"
    "Use the tools available to you whenever they can improve accuracy. This includes "
    "both the built-in tools and any additional tools provided at runtime by "
    "extensions. Do not assume the tool list is fixed — always prefer a relevant tool "
    "over reasoning from memory."
)

# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

_request_id_counter = itertools.count(1)


def _build_tool_call(arguments: dict[str, Any], tool_name: str) -> dict[str, Any]:
    return {
        "jsonrpc": _JSONRPC_VERSION,
        "id": next(_request_id_counter),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _parse_sse_response(text: str) -> dict[str, Any]:
    """Extract the last JSON-RPC message from an SSE ``data:`` stream."""
    result: dict[str, Any] | None = None
    for line in text.splitlines():
        if line.startswith("data:"):
            payload = line[len("data:") :].strip()
            if payload:
                result = json.loads(payload)
    if result is None:
        raise TransportError("No JSON-RPC message found in SSE response.")
    return result


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    if "text/event-stream" in response.headers.get("content-type", ""):
        return _parse_sse_response(response.text)
    return response.json()


def _extract_tool_result(jsonrpc: dict[str, Any]) -> dict[str, Any]:
    if "error" in jsonrpc:
        msg = jsonrpc["error"].get("message", "Unknown error")
        raise ExtensibilityError(f"n8n returned an error: {msg}")

    result = jsonrpc.get("result", {})
    if result.get("isError"):
        content = result.get("content", [])
        error_text = next(
            (c.get("text", "") for c in content if c.get("type") == "text"), ""
        )
        raise ExtensibilityError(f"n8n tool call failed: {error_text}")

    for item in result.get("content", []):
        if item.get("type") == "text":
            try:
                return json.loads(item["text"])
            except (json.JSONDecodeError, KeyError):
                continue

    structured = result.get("structuredContent")
    if structured is not None:
        return structured

    raise ExtensibilityError("Hook response contains no parseable content.")


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
        self,
        transport: Transport,
        _telemetry_source: Optional[Module] = None,
        *,
        _audit_channel_id: str = "",
        _audit_service_name: str = "",
    ) -> None:
        """Initialize the client with a transport.

        Warning:
            For internal and testing use. Use :func:`create_client` in application code.

        Args:
            transport: Configured transport for extensibility requests.
                Either :class:`UmsTransport` (cloud), :class:`LocalTransport`
                (local dev), or :class:`NoOpTransport` (graceful degradation).
            _telemetry_source: Internal telemetry source identifier. Not intended for external use.
            _audit_channel_id: ALS channel ID for audit events. Internal use only.
            _audit_service_name: ALS service name for audit events. Internal use only.
        """
        self._transport = transport
        self._telemetry_source = _telemetry_source
        self._audit_channel_id = _audit_channel_id
        self._audit_service_name = _audit_service_name or _audit_channel_id

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

    def get_extended_instruction(
        self,
        *,
        tenant: str,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
    ) -> str:
        """Return the raw extended instruction for a tenant, or an empty string.

        Fetches the extension capability implementation for ``tenant`` and
        returns the merged instruction text.  Returns ``""`` when no extension
        is active or the extension carries no instruction.

        The tenant is passed explicitly so this method is safe under concurrent
        requests from different tenants — no per-tenant state is stored on the
        client instance.

        Args:
            tenant: Tenant ID extracted from the incoming request's JWT.
            capability_id: Extension capability ID. Defaults to ``"default"``.

        Returns:
            Instruction text, or ``""`` if none is configured.

        Example::

            from sap_cloud_sdk.extensibility import create_client

            client = create_client("sap.ai:agent:myAgent:v1")
            instruction = client.get_extended_instruction(tenant=tenant_id)
        """
        ext_impl = self.get_extension_capability_implementation(
            tenant=tenant, capability_id=capability_id
        )
        return ext_impl.instruction or ""

    def get_extended_system_prompt(
        self,
        system_prompt: str,
        *,
        tenant: str,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
        wrapper: Optional[str] = None,
    ) -> str:
        """Combine the agent's base system prompt with the tenant's extended instruction.

        Fetches the extension capability implementation for ``tenant`` and,
        when an instruction is present, appends it to ``system_prompt`` with a
        default wrapper preamble in between.  Returns ``system_prompt`` unchanged
        when no extension instruction is active.

        The wrapper text explains to the LLM that the appended content comes from
        a tenant-provided extension and should be honoured with the same authority
        as the base prompt.  Pass ``wrapper=""`` to suppress it, or supply a
        custom string to replace it.

        The tenant is passed explicitly so this method is safe under concurrent
        requests from different tenants — no per-tenant state is stored on the
        client instance.

        Args:
            system_prompt: The agent's base system prompt.
            tenant: Tenant ID extracted from the incoming request's JWT.
            capability_id: Extension capability ID. Defaults to ``"default"``.
            wrapper: Text inserted between ``system_prompt`` and the extended
                instruction.  Defaults to :data:`_DEFAULT_INSTRUCTION_WRAPPER`.
                Pass ``""`` to append the instruction with no preamble.

        Returns:
            Combined prompt string, or ``system_prompt`` unchanged when no
            extended instruction is configured for the tenant.

        Example::

            from sap_cloud_sdk.extensibility import create_client

            client = create_client("sap.ai:agent:myAgent:v1")
            effective_prompt = client.get_extended_system_prompt(
                SYSTEM_PROMPT,
                tenant=tenant_id,
            )
        """
        instruction = self.get_extended_instruction(
            tenant=tenant, capability_id=capability_id
        )
        if not instruction:
            return system_prompt

        preamble = _DEFAULT_INSTRUCTION_WRAPPER if wrapper is None else wrapper
        if preamble:
            return (
                system_prompt
                + "\n\n"
                + preamble
                + "\n\n## Extended Instructions\n"
                + instruction
            )
        return system_prompt + "\n\n## Extended Instructions\n" + instruction

    @record_metrics(
        Module.EXTENSIBILITY,
        Operation.EXTENSIBILITY_CALL_HOOK,
        deprecated=True,
    )
    def call_hook(
        self,
        hook: Hook,
        hook_config: HookConfig,
    ) -> Optional[Message]:
        """Call a hook's MCP endpoint and poll until completion.

        .. deprecated::
            Use :meth:`call_hook_agw` instead, which invokes the hook through
            Agent Gateway (handles tenant resolution, user-token exchange, and
            the per-hook MCP translation-card contract).

        Executes the workflow via ``execute-workflow``, then polls
        ``get-execution`` every 500 ms until the execution succeeds, fails,
        or ``hook.timeout`` seconds elapse.

        This method is transport-agnostic: regardless of how extension
        metadata was fetched (backend, local file, or no-op),
        the actual hook invocation is always a direct HTTP call to the
        URL embedded in the :class:`Hook` object.

        Args:
            hook: Hook configuration (workflow ID, method, timeout).
            hook_config: Hook invocation configuration (endpoint URL, auth token, optional payload).

        Returns:
            Parsed ``Message`` from the last executed workflow node, or ``None``
            if the hook completed successfully but produced no message.

        Raises:
            TransportError: On HTTP errors, terminal execution failures, or timeout.

        Example:
            ```python
            from sap_cloud_sdk.extensibility import create_client

            client = create_client("sap.ai:agent:myAgent:v1")
            impl = client.get_extension_capability_implementation(tenant="tenant-abc")

            if impl.hooks:
                hook = impl.hooks[0]
                result = client.call_hook(
                    hook,
                    HookConfig(
                        endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
                        auth_token="my-secret-token",
                        payload={"foo": "bar"},
                    ),
                )
            ```
        """
        warnings.warn(
            "call_hook() is deprecated. Use call_hook_agw() instead, which "
            "invokes the hook through Agent Gateway.",
            DeprecationWarning,
            stacklevel=2,
        )
        headers = {**_JSONRPC_HEADERS}
        inject(headers)

        message_payload: dict[str, Any] = {}
        if hook_config.payload is not None:
            model_dump = getattr(hook_config.payload, "model_dump", None)
            if callable(model_dump):
                message_payload = cast(dict[str, Any], model_dump(exclude_none=True))

        # 1. Execute workflow
        execute_workflow_arguments = {
            "workflowId": hook.n8n_workflow_config.workflow_id,
            "inputs": {
                "type": "webhook",
                "webhookData": {
                    "method": hook.n8n_workflow_config.method,
                    "query": {},
                    "body": message_payload,
                    "headers": headers,
                },
            },
        }

        try:
            with httpx.Client(
                headers={"Authorization": f"Bearer {hook_config.auth_token}"},
                timeout=hook.timeout,
            ) as client:
                tool_resp = client.post(
                    hook_config.endpoint,
                    json=_build_tool_call(
                        execute_workflow_arguments, _EXECUTE_WORKFLOW_TOOL_NAME
                    ),
                    headers=headers,
                )
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(
                f"HTTP request to hook MCP endpoint failed: {exc}"
            ) from exc

        try:
            data = _extract_tool_result(_parse_response(tool_resp))
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"Could not parse hook response: {exc}") from exc

        status = data.get("status", "")

        # 2. Fail fast on terminal statuses from execute-workflow
        if status in _EXECUTE_TERMINAL_STATUSES:
            error_msg = data.get("error", "")
            raise ExtensibilityError(
                f"Workflow execution failed with status {status!r}"
                + (f": {error_msg}" if error_msg else "")
            )

        # 3. Poll get-execution for running/new/waiting/started
        execution_id = data.get("executionId")
        get_execution_arguments = {
            "workflowId": hook.n8n_workflow_config.workflow_id,
            "executionId": str(execution_id),
            "includeData": True,
        }

        deadline = time.monotonic() + hook.timeout
        last_status = status
        while time.monotonic() < deadline:
            time.sleep(_HOOK_POLL_INTERVAL)

            try:
                with httpx.Client(
                    headers={"Authorization": f"Bearer {hook_config.auth_token}"},
                    timeout=hook.timeout,
                ) as client:
                    tool_resp = client.post(
                        hook_config.endpoint,
                        json=_build_tool_call(
                            get_execution_arguments, _GET_EXECUTION_TOOL_NAME
                        ),
                        headers=headers,
                    )
            except TransportError:
                raise
            except Exception as exc:
                raise TransportError(
                    f"HTTP request to hook MCP endpoint failed: {exc}"
                ) from exc

            try:
                data = _extract_tool_result(_parse_response(tool_resp))
            except TransportError:
                raise
            except Exception as exc:
                raise TransportError(f"Could not parse hook response: {exc}") from exc

            last_status = data.get("execution", {}).get("status", "") or data.get(
                "status", ""
            )

            if last_status == "success":
                try:
                    result_data = data.get("data", {}).get("resultData", {})
                    last_node = result_data.get("lastNodeExecuted", "")
                    response_json = (
                        result_data.get("runData", {})
                        .get(last_node, [{}])[0]
                        .get("data", {})
                        .get("main", [[{}]])[0][0]
                        .get("json", {})
                    )
                    return Message(**response_json)
                except (KeyError, IndexError, TypeError, ValidationError) as exc:
                    raise ExtensibilityError(
                        f"Failed to extract response from last executed node: {exc}"
                    ) from exc

            if last_status in _EXECUTION_TERMINAL_STATUSES:
                error_msg = data.get("error", "")
                raise ExtensibilityError(
                    f"Workflow execution failed with status {last_status!r}"
                    + (f": {error_msg}" if error_msg else "")
                )

            # Continue polling for: running, waiting, new, unknown

        raise ExtensibilityError(
            f"Workflow execution timed out after {hook.timeout}s. "
            f"Last status: {last_status!r}"
        )

    async def _discover_n8n_tools(
        self, agw_client: Any, hook: Hook, user_token: Optional[str]
    ) -> Any:
        tools = await agw_client.list_mcp_tools(user_token=user_token or None)

        tool_name = hook.n8n_workflow_config.tool_name
        card_ord_id = hook.n8n_workflow_config.card_ord_id

        hook_tool = next(
            (t for t in tools if t.name == tool_name and t.server_name == card_ord_id),
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
        message_body = (
            message.model_dump(mode="json", exclude_none=True)
            if message is not None
            else {}
        )
        tool_arguments = {"body": message_body}
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
            structured = (
                data.get("structuredContent") or data.get("value") if data else None
            )
            return Message(**structured) if structured else None
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
            ExtensibilityError: When the hook tool is not found via Agent Gateway.

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

    def emit_instruction_spans(
        self,
        ext_impl: Optional[ExtensionCapabilityImplementation],
    ) -> None:
        """Emit one OTel span per instruction source in the extension implementation.

        Each span is named ``extension_instruction`` and carries the full set of
        ``sap.extension.*`` attributes.  No-ops when ``ext_impl`` has no
        instruction source information.

        Args:
            ext_impl: Extension capability implementation returned by
                :meth:`get_extension_capability_implementation`.

        Example::

            client = create_client("sap.ai:agent:myAgent:v1")
            ext = client.get_extension_capability_implementation(tenant=tenant_id)
            client.emit_instruction_spans(ext)
        """
        if not ext_impl or not ext_impl.source or not ext_impl.source.instructions:
            return

        from opentelemetry import trace as _otel_trace

        from sap_cloud_sdk.core.telemetry import (
            ATTR_CAPABILITY_ID,
            ATTR_EXTENSION_ID,
            ATTR_EXTENSION_ITEM_NAME,
            ATTR_EXTENSION_NAME,
            ATTR_EXTENSION_TYPE,
            ATTR_EXTENSION_VERSION,
            ATTR_IS_EXTENSION,
            ATTR_JOULE_STUDIO_GSID,
            ATTR_SOLUTION_ID,
            ExtensionType,
        )

        tracer = _otel_trace.get_tracer("sap.cloud_sdk.extension")
        for source_info in ext_impl.source.instructions.values():
            attrs: dict[str, Any] = {
                ATTR_IS_EXTENSION: True,
                ATTR_EXTENSION_TYPE: ExtensionType.INSTRUCTION.value,
                ATTR_CAPABILITY_ID: ext_impl.capability_id,
                ATTR_EXTENSION_ID: source_info.extension_id,
                ATTR_EXTENSION_NAME: source_info.extension_name,
                ATTR_EXTENSION_VERSION: source_info.extension_version,
                ATTR_EXTENSION_ITEM_NAME: source_info.extension_name,
                ATTR_SOLUTION_ID: source_info.solution_id or "",
                ATTR_JOULE_STUDIO_GSID: source_info.joule_studio_gsid or "",
            }
            with tracer.start_as_current_span(
                "extension_instruction", attributes=attrs
            ):
                pass

    async def run_hooks(
        self,
        hooks: list[Hook],
        hook_type: HookType,
        message: Message,
        *,
        tenant_subdomain: Optional[str] = None,
        tenant_id: str = "",
        user_id: str = "",
        user_token: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
        ext_impl: Optional[ExtensionCapabilityImplementation] = None,
        status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> float:
        """Run all hooks of the given type against *message*.

        Filters ``hooks`` to those matching ``hook_type``, executes them in
        order, appends any hook-contributed parts to ``message`` in place, and
        returns the total wall-clock duration (in seconds) of all hook calls.

        Telemetry spans, metrics, and audit events are recorded for each hook.
        Audit events are only emitted when ``audit_channel_id`` was supplied to
        :func:`create_client` via :class:`~sap_cloud_sdk.extensibility.ExtensibilityConfig`.

        Args:
            hooks: All hooks from the extension capability implementation.
                Only those matching ``hook_type`` are executed.
            hook_type: :attr:`~sap_cloud_sdk.extensibility.HookType.BEFORE` or
                :attr:`~sap_cloud_sdk.extensibility.HookType.AFTER`.
            message: A2A ``Message`` to pass to each hook.  Hook responses are
                appended to ``message.parts`` in place.
            tenant_subdomain: Tenant subdomain forwarded to
                :meth:`call_hook_agw` for AGW client creation.
            tenant_id: Tenant ID stamped on audit events (from the IAS JWT
                ``app_tid`` claim).
            user_id: User identifier stamped on audit events (email or sub).
            user_token: Bearer token forwarded to :meth:`call_hook_agw`.
            headers: Additional HTTP headers forwarded to :meth:`call_hook_agw`.
            ext_impl: Extension capability implementation used for per-hook
                source info resolution (telemetry attribution).
            status_callback: Optional async callable called before each hook
                with a human-readable status text.  Use this to forward status
                updates to an A2A ``TaskUpdater`` without coupling the SDK to
                the A2A types.  Signature: ``async (text: str) -> None``.

        Returns:
            Total wall-clock time (seconds) spent executing hooks.

        Raises:
            HookShortCircuit: When a hook returns ``stop_execution=true`` and
                ``can_short_circuit=true``, or when a hook times out / fails and
                its ``on_failure`` policy is ``BLOCK``.

        Example::

            from sap_cloud_sdk.extensibility import create_client, HookType

            client = create_client("sap.ai:agent:myAgent:v1")
            ext = client.get_extension_capability_implementation(tenant=tenant_id)

            duration = await client.run_hooks(
                ext.hooks,
                HookType.BEFORE,
                message,
                tenant_subdomain=tenant_subdomain,
                tenant_id=tenant_id,
                user_id=user_id,
                user_token=inbound_token,
                ext_impl=ext,
            )
        """
        from opentelemetry import trace as _otel_trace

        from sap_cloud_sdk.core.telemetry import (
            ATTR_CAPABILITY_ID,
            ATTR_EXTENSION_ID,
            ATTR_EXTENSION_ITEM_NAME,
            ATTR_EXTENSION_NAME,
            ATTR_EXTENSION_TYPE,
            ATTR_EXTENSION_VERSION,
            ATTR_IS_EXTENSION,
            ATTR_JOULE_STUDIO_GSID,
            ATTR_SOLUTION_ID,
            ExtensionType,
            extension_context,
            record_hook_call_duration,
        )

        def _get_tracer() -> Any:
            return _otel_trace.get_tracer("sap.cloud_sdk.extension")

        filtered = [h for h in hooks if h.type == hook_type]
        phase = "pre" if hook_type == HookType.BEFORE else "post"
        logger.info("Found %d %s-execution hook(s)", len(filtered), phase)

        total_duration = 0.0

        for hook in filtered:
            hook_name = hook.name or hook.id or "unknown"
            logger.debug(
                "Executing hook '%s' (id=%s, type=%s, can_short_circuit=%s)",
                hook_name,
                hook.id or "N/A",
                hook_type.name,
                hook.can_short_circuit,
            )

            if status_callback is not None:
                await status_callback(f"Executing {phase}-execution hook: {hook_name}")

            source_info = (
                ext_impl.get_source_info_for_hook(hook.id) if ext_impl else None
            )
            resolved_name = source_info.extension_name if source_info else "unknown"
            resolved_id = source_info.extension_id if source_info else ""
            resolved_version = str(source_info.extension_version) if source_info else ""
            resolved_solution_id = (
                getattr(source_info, "solution_id", "") or "" if source_info else ""
            )
            resolved_joule_studio_gsid = (
                getattr(source_info, "joule_studio_gsid", "") or ""
                if source_info
                else ""
            )
            capability = (
                ext_impl.capability_id if ext_impl else DEFAULT_EXTENSION_CAPABILITY_ID
            )

            _attrs: dict[str, Any] = {
                ATTR_IS_EXTENSION: True,
                ATTR_EXTENSION_TYPE: ExtensionType.HOOK.value,
                ATTR_CAPABILITY_ID: capability,
                ATTR_EXTENSION_ID: resolved_id,
                ATTR_EXTENSION_NAME: resolved_name,
                ATTR_EXTENSION_VERSION: resolved_version,
                ATTR_EXTENSION_ITEM_NAME: hook_name,
                ATTR_SOLUTION_ID: resolved_solution_id,
                ATTR_JOULE_STUDIO_GSID: resolved_joule_studio_gsid,
            }

            t0 = time.monotonic()
            try:
                with (
                    extension_context(
                        capability_id=capability,
                        extension_name=resolved_name,
                        extension_type=ExtensionType.HOOK,
                        extension_id=resolved_id,
                        extension_version=resolved_version,
                        item_name=hook_name,
                        solution_id=resolved_solution_id,
                        joule_studio_gsid=resolved_joule_studio_gsid,
                    ),
                    _get_tracer().start_as_current_span(
                        f"extension_hook {hook_name}",
                        attributes=_attrs,
                    ),
                ):
                    logger.debug(
                        "Calling hook '%s' via AGW (tenant_subdomain=%s)",
                        hook_name,
                        tenant_subdomain or "<none>",
                    )
                    response = await asyncio.wait_for(
                        self.call_hook_agw(
                            hook=hook,
                            user_token=user_token or None,
                            message=message,
                            headers=headers,
                            tenant_subdomain=tenant_subdomain,
                        ),
                        timeout=60,
                    )
                    logger.debug(
                        "Hook '%s' AGW call returned: response=%s",
                        hook_name,
                        "none"
                        if response is None
                        else f"parts={len(response.parts or [])}, metadata={response.metadata}",
                    )
                    if response is not None:
                        logger.info("Hook '%s' returned a response", hook_name)
                        if status_callback is not None:
                            await status_callback(f"Processing {hook_name} response…")
                        metadata = response.metadata or {}
                        if metadata.get("stop_execution"):
                            if hook.can_short_circuit:
                                stop_reason = metadata.get("stop_execution_reason") or (
                                    f"Hook '{hook_name}' blocked execution."
                                )
                                logger.warning(
                                    "Hook '%s' blocked execution: %s",
                                    hook_name,
                                    stop_reason,
                                )
                                if self._audit_channel_id:
                                    from sap_cloud_sdk.extensibility._audit import (
                                        _emit_hook_short_circuit,
                                    )

                                    await _emit_hook_short_circuit(
                                        tenant_subdomain=tenant_subdomain or "",
                                        tenant_id=tenant_id,
                                        user_id=user_id,
                                        hook_name=hook_name,
                                        capability_id=capability,
                                        reason=stop_reason,
                                        channel_id=self._audit_channel_id,
                                        service_name=self._audit_service_name,
                                    )
                                raise HookShortCircuit(
                                    stop_reason,
                                    hook_name=hook_name,
                                    capability_id=capability,
                                )
                            else:
                                logger.info(
                                    "Hook '%s' signalled stop_execution but canShortCircuit=false"
                                    " — ignoring",
                                    hook_name,
                                )

                        if response.parts:
                            message.parts.extend(response.parts)
                            logger.info(
                                "Hook '%s' appended %d part(s)",
                                hook_name,
                                len(response.parts),
                            )

                    if self._audit_channel_id:
                        from sap_cloud_sdk.extensibility._audit import (
                            _emit_hook_executed,
                        )

                        await _emit_hook_executed(
                            phase=phase,
                            tenant_subdomain=tenant_subdomain or "",
                            tenant_id=tenant_id,
                            user_id=user_id,
                            hook_name=hook_name,
                            capability_id=capability,
                            channel_id=self._audit_channel_id,
                            service_name=self._audit_service_name,
                        )

            except HookShortCircuit:
                raise
            except asyncio.TimeoutError:
                logger.error("Hook '%s' timed out after 60s", hook_name)
                if hook.on_failure == OnFailure.BLOCK:
                    raise HookShortCircuit(
                        f"Hook '{hook_name}' timed out after 60s",
                        hook_name=hook_name,
                        capability_id=capability,
                    )
                logger.warning("Hook '%s' timed out — continuing execution", hook_name)
            except Exception as exc:
                logger.error("Hook '%s' failed: %s", hook_name, exc, exc_info=True)
                if hook.on_failure == OnFailure.BLOCK:
                    raise HookShortCircuit(
                        f"Hook '{hook_name}' failed: {exc}",
                        hook_name=hook_name,
                        capability_id=capability,
                    )
                logger.warning("Hook '%s' failed — continuing execution", hook_name)
            finally:
                duration = time.monotonic() - t0
                total_duration += duration
                record_hook_call_duration(duration)
                logger.debug(
                    "Hook '%s' wall-clock duration: %.3fs", hook_name, duration
                )

        return total_duration

    async def audit_instruction_applied(
        self,
        *,
        tenant_subdomain: str,
        tenant_id: str,
        context_id: str,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
        user_id: str = "",
    ) -> None:
        """Emit an ALS audit event recording that a tenant instruction was applied.

        No-ops when ``audit_channel_id`` was not set on the client via
        :class:`~sap_cloud_sdk.extensibility.ExtensibilityConfig`.

        Args:
            tenant_subdomain: DWC subdomain used to resolve the ALS destination.
            tenant_id: Tenant ID from the IAS JWT ``app_tid`` claim.
            context_id: A2A conversation context ID for the current request.
            capability_id: Extension capability ID. Defaults to ``"default"``.
            user_id: User email or sub claim for the ALS initiator field.
        """
        if not self._audit_channel_id:
            return
        from sap_cloud_sdk.extensibility._audit import _emit_instruction_applied

        await _emit_instruction_applied(
            tenant_subdomain=tenant_subdomain,
            tenant_id=tenant_id,
            user_id=user_id,
            context_id=context_id,
            capability_id=capability_id,
            channel_id=self._audit_channel_id,
            service_name=self._audit_service_name,
        )
