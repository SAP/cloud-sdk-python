"""Extensibility service client."""

from __future__ import annotations

import itertools
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Optional, Union, cast

import httpx
from a2a.types import Message
from opentelemetry.propagate import inject
from pydantic_core import ValidationError

from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    ExtensionCapabilityImplementation,
    Hook,
)
from sap_cloud_sdk.extensibility.config import HookConfig
from sap_cloud_sdk.extensibility.exceptions import TransportError

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
        raise TransportError(f"n8n returned an error: {msg}")

    result = jsonrpc.get("result", {})
    if result.get("isError"):
        content = result.get("content", [])
        error_text = next(
            (c.get("text", "") for c in content if c.get("type") == "text"), ""
        )
        raise TransportError(f"n8n tool call failed: {error_text}")

    for item in result.get("content", []):
        if item.get("type") == "text":
            try:
                return json.loads(item["text"])
            except (json.JSONDecodeError, KeyError):
                continue

    structured = result.get("structuredContent")
    if structured is not None:
        return structured

    raise TransportError("Hook response contains no parseable content.")


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

    @record_metrics(
        Module.EXTENSIBILITY,
        Operation.EXTENSIBILITY_CALL_HOOK,
    )
    def call_hook(
        self,
        hook: Hook,
        hook_config: HookConfig,
    ) -> Optional[Message]:
        """Call a hook's MCP endpoint and poll until completion.

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
            raise TransportError(
                f"Workflow execution failed with status {status!r}"
                + (f": {error_msg}" if error_msg else "")
            )

        # 3. Return immediately if execution completed synchronously
        if status == "success":
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
                raise TransportError(
                    f"Failed to extract response from last executed node: {exc}"
                ) from exc

        # 4. Poll get-execution for running/new/waiting/started
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
                    raise TransportError(
                        f"Failed to extract response from last executed node: {exc}"
                    ) from exc

            if last_status in _EXECUTION_TERMINAL_STATUSES:
                error_msg = data.get("error", "")
                raise TransportError(
                    f"Workflow execution failed with status {last_status!r}"
                    + (f": {error_msg}" if error_msg else "")
                )

            # Continue polling for: running, waiting, new, unknown

        raise TransportError(
            f"Workflow execution timed out after {hook.timeout}s. "
            f"Last status: {last_status!r}"
        )
