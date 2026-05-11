"""Data models for the extensibility module.

Defines the dataclasses used to represent extension capabilities (for A2A card
serialization) and extension capability implementations (resolved at runtime).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from http import HTTPMethod
from typing import Any, Dict, List, Optional

#: Default extension capability ID used in v1 (single capability per agent).
DEFAULT_EXTENSION_CAPABILITY_ID = "default"

#: Default hook execution timeout in seconds, used when the backend omits the field.
DEFAULT_HOOK_TIMEOUT: int = 30


class HookType(StrEnum):
    """Hook type for extension hooks.

    Defines the possible types of hooks that can be registered.

    Attributes:
        BEFORE: Hook executed before an operation.
        AFTER: Hook executed after an operation.
    """

    BEFORE = "BEFORE"
    AFTER = "AFTER"


class DeploymentType(StrEnum):
    """Deployment type for extension hooks.

    Defines the possible deployment types for hooks.

    Attributes:
        N8N: Hook deployed on N8N platform.
        SERVERLESS: Hook deployed as Serverless function.
        UNKNOWN: Unrecognized deployment type returned by the backend.
    """

    N8N = "N8N"
    SERVERLESS = "SERVERLESS"
    UNKNOWN = "UNKNOWN"


class ExecutionMode(StrEnum):
    """Execution mode for extension hooks.

    Defines how hooks are executed.

    Attributes:
        SYNC: Synchronous execution - waits for hook to complete.
        ASYNC: Asynchronous execution - does not wait for hook to complete.
    """

    SYNC = "SYNC"
    ASYNC = "ASYNC"


class OnFailure(StrEnum):
    """Behavior when a hook execution fails.

    Defines the possible behaviors when a hook fails.

    Attributes:
        CONTINUE: Continue execution despite hook failure.
        BLOCK: Block execution when hook fails.
    """

    CONTINUE = "CONTINUE"
    BLOCK = "BLOCK"


def _parse_hook_type(value: Any) -> HookType | None:
    """Parse a hook type value into a HookType enum.

    Args:
        value: Hook type value (string, HookType, or None).

    Returns:
        HookType enum if value matches a known type, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, HookType):
        return value
    if isinstance(value, str):
        for m in HookType:
            if m.value == value:
                return m
    return None


def _parse_deployment_type(value: Any) -> DeploymentType | None:
    """Parse a deployment type value into a DeploymentType enum.

    Args:
        value: Deployment type value (string, DeploymentType, or None).

    Returns:
        DeploymentType enum if value matches a known type, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, DeploymentType):
        return value
    if isinstance(value, str):
        for m in DeploymentType:
            if m.value == value:
                return m
    return None


def _parse_execution_mode(value: Any) -> ExecutionMode | None:
    """Parse an execution mode value into an ExecutionMode enum.

    Args:
        value: Execution mode value (string, ExecutionMode, or None).

    Returns:
        ExecutionMode enum if value matches a known type, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, ExecutionMode):
        return value
    if isinstance(value, str):
        for m in ExecutionMode:
            if m.value == value:
                return m
    return None


def _parse_on_failure(value: Any) -> OnFailure | None:
    """Parse an on_failure value into an OnFailure enum.

    Args:
        value: On failure value (string, OnFailure, or None).

    Returns:
        OnFailure enum if value matches a known type, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, OnFailure):
        return value
    if isinstance(value, str):
        for m in OnFailure:
            if m.value == value:
                return m
    return None


def _parse_http_method(value: Any) -> HTTPMethod | None:
    """Parse an HTTP method value into an HTTPMethod enum.

    Args:
        value: HTTP method value (string, HTTPMethod, or None).

    Returns:
        HTTPMethod enum if value matches a known method, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, HTTPMethod):
        return value
    if isinstance(value, str):
        # Convert to uppercase for case-insensitive matching
        upper_value = value.upper()
        for m in HTTPMethod:
            if m.value == upper_value:
                return m
    return None


@dataclass
class ToolAdditions:
    """Configuration for tool additions at an extension capability.

    Controls whether an extension capability accepts additional tools.

    Attributes:
        enabled: Whether tool additions are enabled.
    """

    enabled: bool = True


@dataclass
class Tools:
    """Tool-related configuration for an extension capability.

    Groups all tool configuration options. The structure mirrors the
    wire format in the A2A card (``"tools": {"additions": {...}}``).

    Attributes:
        additions: Configuration for tool additions.
    """

    additions: ToolAdditions = field(default_factory=ToolAdditions)


@dataclass
class HookCapability:
    """Configuration for hooks at an extension capability.

    Controls whether hooks are supported and which hooks are supported.

    Attributes:
        id: Hook ID.
        type: Type of the hook (BEFORE, AFTER).
        display_name: Human-readable name of the hook.
        description: Description of the hook.
    """

    id: str
    type: HookType
    display_name: str
    description: str

    def __post_init__(self) -> None:
        """Validate that type is a valid HookType enum value."""
        if not isinstance(self.type, HookType):
            raise ValueError(
                f"type must be a HookType enum value, got: {type(self.type).__name__} = {self.type!r}"
            )


@dataclass
class N8nWorkflowConfig:
    """n8n workflow configuration embedded in a hook.

    Attributes:
        workflow_id: n8n workflow ID.
        method: HTTP method for the n8n webhook call.
    """

    workflow_id: str
    method: HTTPMethod

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> N8nWorkflowConfig:
        """Parse an N8nWorkflowConfig entry from the backend JSON response.

        Expected JSON shape::

            {
                "workflowId": "unique_n8n_workflow_id",
                "method": "POST"
            }

        Args:
            obj: Raw dict from the ``n8nWorkflowConfig`` field.

        Returns:
            Parsed ``N8nWorkflowConfig`` instance.
        """
        method = _parse_http_method(obj.get("method", "POST")) or HTTPMethod.POST
        return cls(
            workflow_id=obj.get("workflowId", ""),
            method=method,
        )


@dataclass
class Hook:
    """Hook-related implementation for an extension capability.

    Groups all hook configuration options.

    Attributes:
        id: Database-generated UUID for the hook (from cuid).
        hook_id: Developer-defined hook key (e.g., "before_tool_execution");
            not guaranteed to be unique.
        n8n_workflow_config: n8n workflow configuration (workflow ID and HTTP method).
        name: Human-readable name of the hook.
        type: Type of the hook (e.g., "BEFORE", "AFTER")
        deployment_type: Deployment type of the hook (e.g., "N8N", "SERVERLESS")
        timeout: Timeout in seconds for hook execution.
        execution_mode: Execution mode for the hook (e.g., "SYNC", "ASYNC").
        on_failure: Behavior if the hook execution fails (e.g., "CONTINUE", "BLOCK").
        order: Execution order of the hook relative to other hooks.
        can_short_circuit: Whether this hook can short-circuit the main execution flow.

    """

    id: str
    hook_id: str
    n8n_workflow_config: N8nWorkflowConfig
    name: str
    type: HookType
    deployment_type: DeploymentType
    timeout: int
    execution_mode: ExecutionMode
    on_failure: OnFailure
    order: int
    can_short_circuit: bool

    def __post_init__(self) -> None:
        """Validate that enum fields have valid values."""
        if not isinstance(self.type, HookType):
            raise ValueError(
                f"type must be a HookType enum value, got: {type(self.type).__name__} = {self.type!r}"
            )
        if not isinstance(self.deployment_type, DeploymentType):
            raise ValueError(
                f"deployment_type must be a DeploymentType enum value, got: {type(self.deployment_type).__name__} = {self.deployment_type!r}"
            )
        if not isinstance(self.execution_mode, ExecutionMode):
            raise ValueError(
                f"execution_mode must be an ExecutionMode enum value, got: {type(self.execution_mode).__name__} = {self.execution_mode!r}"
            )
        if not isinstance(self.on_failure, OnFailure):
            raise ValueError(
                f"on_failure must be an OnFailure enum value, got: {type(self.on_failure).__name__} = {self.on_failure!r}"
            )

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> Hook:
        """Parse an Hook entry from the extensibility service JSON response.

        Expected JSON shape::

            {
                "id": "UUID",
                "hookId": "before_tool_execution",
                "name": "Before Tool Execution Hook",
                "hookType": "BEFORE",
                "deploymentType": "N8N",
                "timeout": 30,
                "executionMode": "SYNC",
                "onFailure": "CONTINUE",
                "order": 1,
                "canShortCircuit": true,
                "n8nWorkflowConfig": {
                    "workflowId": "unique_n8n_workflow_id",
                    "method": "POST"
                }
            }

        Args:
            obj: Raw dict from the extensibility service ``hooks[]`` array.

        Returns:
            Parsed ``Hook`` instance.

        Raises:
            ValueError: If required enum fields have invalid values.
        """
        hook_type = _parse_hook_type(obj.get("hookType", ""))
        deployment_type = _parse_deployment_type(obj.get("deploymentType", ""))
        execution_mode = _parse_execution_mode(obj.get("executionMode", "SYNC"))
        on_failure = _parse_on_failure(obj.get("onFailure", "CONTINUE"))
        n8n_workflow_config = N8nWorkflowConfig.from_dict(
            obj.get("n8nWorkflowConfig") or {}
        )

        # Validate required enum fields
        if hook_type is None:
            hook_type_value = obj.get("hookType", "")
            raise ValueError(
                f"Invalid or missing hookType: {hook_type_value!r}. "
                f"Must be one of: {', '.join(m.value for m in HookType)}"
            )
        if deployment_type is None:
            deployment_type_value = obj.get("deploymentType", "")
            raise ValueError(
                f"Invalid or missing deploymentType: {deployment_type_value!r}. "
                f"Must be one of: {', '.join(m.value for m in DeploymentType)}"
            )

        # Use default enum values if parsing failed
        if execution_mode is None:
            execution_mode = ExecutionMode.SYNC
        if on_failure is None:
            on_failure = OnFailure.CONTINUE

        return cls(
            id=obj.get("id", ""),
            hook_id=obj.get("hookId", ""),
            n8n_workflow_config=n8n_workflow_config,
            name=obj.get("name", ""),
            type=hook_type,
            deployment_type=deployment_type,
            timeout=obj.get("timeout", DEFAULT_HOOK_TIMEOUT),
            execution_mode=execution_mode,
            on_failure=on_failure,
            order=obj.get("order", 0),
            can_short_circuit=obj.get("canShortCircuit", False),
        )


@dataclass
class ExtensionSourceInfo:
    """Attribution info for a single tool or hook contributed by an extension.

    Contains the extension's identity metadata so that telemetry spans and
    baggage can carry per-item attribution (which extension contributed this
    specific tool or hook).

    Attributes:
        extension_name: Human-readable name of the extension
            (e.g., ``"ap-invoice-extension"``).
        extension_version: Version number of the extension.
        extension_id: Unique identifier (UUID) of the extension.
        extension_url: Build extension URL, or empty string if not provided.
        solution_id: Build solution ID extracted from extension_url, or empty
            string if not available.
    """

    extension_name: str
    extension_version: str
    extension_id: str
    extension_url: str = ""
    solution_id: str = ""

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> ExtensionSourceInfo:
        """Parse an extension source info entry from the backend JSON response.

        Expected JSON shape::

            {
                "extensionName": "ap-invoice-extension",
                "extensionVersion": "1",
                "extensionId": "a1b2c3d4-...",
                "extensionUrl": "https://...",
                "solutionId": "f9cbd5c1-..."
            }

        Args:
            obj: Raw dict from a ``source.tools`` or ``source.hooks`` value.

        Returns:
            Parsed ``ExtensionSourceInfo`` instance.
        """
        return cls(
            extension_name=obj.get("extensionName", ""),
            extension_version=obj.get("extensionVersion", ""),
            extension_id=obj.get("extensionId", ""),
            extension_url=obj.get("extensionUrl") or "",
            solution_id=obj.get("solutionId") or "",
        )

    @classmethod
    def from_value(cls, value: Any) -> ExtensionSourceInfo:
        """Parse either a string (old format) or dict (new format).

        Provides backward compatibility with the old backend response format
        where ``source.tools`` and ``source.hooks`` values were plain extension
        name strings.

        Args:
            value: Either a plain string (extension name) or a dict with
                ``extensionName``, ``extensionVersion``, and ``extensionId``.

        Returns:
            Parsed ``ExtensionSourceInfo`` instance.
        """
        if isinstance(value, str):
            return cls(
                extension_name=value,
                extension_version="",
                extension_id="",
                extension_url="",
                solution_id="",
            )
        if isinstance(value, dict):
            return cls.from_dict(value)
        return cls(
            extension_name="",
            extension_version="",
            extension_id="",
            extension_url="",
            solution_id="",
        )


@dataclass
class ExtensionSourceMapping:
    """Source attribution mapping for tools and hooks.

    Maps individual tools and hooks back to the extension that contributed them.
    Returned by the extensibility backend when multiple extensions are merged
    into a single capability implementation response.

    Tool keys are prefixed tool names
    (e.g., ``"sap_mcp_servicenow_v1_create_ticket"``).
    Hook keys are hook IDs (UUIDs) (e.g.,
    ``"3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"``).
    Values are :class:`ExtensionSourceInfo` objects containing the extension's
    name, version, and unique identifier.

    Attributes:
        tools: Mapping of prefixed tool name to extension source info.
        hooks: Mapping of hook ID to extension source info.
    """

    tools: Dict[str, ExtensionSourceInfo] = field(default_factory=dict)
    hooks: Dict[str, ExtensionSourceInfo] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> ExtensionSourceMapping:
        """Parse a source mapping from the backend JSON response.

        Expected JSON shape (new format)::

            {
                "tools": {
                    "sap_mcp_taxvalidator_validate_validate_tax": {
                        "extensionName": "ap-invoice-extension",
                        "extensionVersion": "1",
                        "extensionId": "a1b2c3d4-..."
                    }
                },
                "hooks": {
                    "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": {
                        "extensionName": "ap-invoice-extension",
                        "extensionVersion": "1",
                        "extensionId": "a1b2c3d4-..."
                    }
                }
            }

        Also accepts the old format where values are plain extension name
        strings for backward compatibility.

        Args:
            obj: Raw dict from the backend ``source`` field.

        Returns:
            Parsed ``ExtensionSourceMapping`` instance.
        """
        raw_tools = obj.get("tools", {})
        raw_hooks = obj.get("hooks", {})
        return cls(
            tools={k: ExtensionSourceInfo.from_value(v) for k, v in raw_tools.items()},
            hooks={k: ExtensionSourceInfo.from_value(v) for k, v in raw_hooks.items()},
        )


@dataclass
class ExtensionCapability:
    """Declaration of an agent extension capability for A2A card serialization.

    Used by the agent developer to describe what parts of the agent
    can be extended. Passed to ``build_extension_capabilities()`` to populate
    the agent's A2A card. This is metadata -- it does not carry runtime data.

    Attributes:
        display_name: Human-readable name of the extension capability.
        description: Description of the extension capability.
        id: Internal identifier of the extension capability. Defaults to ``"default"``
            for v1 single-capability usage.
        tools: Tool-related configuration (additions, and future sub-options).
        instruction_supported: Whether the extension capability supports custom instructions.
        supported_hooks: List of supported hooks for this extension capability.
    """

    display_name: str
    description: str
    id: str = DEFAULT_EXTENSION_CAPABILITY_ID
    tools: Tools = field(default_factory=Tools)
    instruction_supported: bool = True
    supported_hooks: List[HookCapability] = field(default_factory=list)


@dataclass
class McpServer:
    """An MCP server contributed by an extension to a capability implementation.

    Groups one or more tools hosted on the same MCP server.

    Attributes:
        ord_id: MCP server ORD ID (e.g., ``"sap.mcp:apiResource:serviceNow:v1"``).
        global_tenant_id: Global tenant ID of the MCP server.
        tool_names: Approved tool names on this server. ``None`` means all
            tools on this server are approved for use (no filtering needed).
    """

    ord_id: str
    global_tenant_id: str
    tool_names: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> McpServer:
        """Parse an MCP server entry from the backend JSON response.

        Expected JSON shape::

            {
                "ordId": "sap.mcp:apiResource:serviceNow:v1",
                "globalTenantId": "tenant-abc-123",
                "toolNames": ["create_ticket"]
            }

        Args:
            obj: Raw dict from the backend ``mcpServers[]`` array.

        Returns:
            Parsed ``McpServer`` instance.
        """
        return cls(
            ord_id=obj.get("ordId", ""),
            global_tenant_id=obj.get("globalTenantId", ""),
            tool_names=obj.get("toolNames"),
        )


@dataclass
class ExtensionCapabilityImplementation:
    """A resolved extension capability implementation at runtime.

    Returned by :meth:`ExtensibilityClient.get_extension_capability_implementation`.
    Contains the contributing extensions' MCP servers, instruction, and hooks
    for a given extension capability.

    When multiple extensions are merged into a single response, the ``source``
    mapping tracks which extension contributed each tool and hook.  Use
    :meth:`get_extension_for_tool` and :meth:`get_extension_for_hook` for
    per-item attribution (e.g., telemetry span attributes).

    Attributes:
        capability_id: Extension capability ID (e.g., ``"default"``).
        extension_names: Names of all extensions that contributed to this
            response.  Empty when no extensions are active.
        mcp_servers: MCP servers contributed by the active extension(s).
        instruction: Custom instruction for this extension capability.
        hooks: List of hooks attached for this extension capability.
        source: Per-tool and per-hook attribution mapping. ``None`` when the
            backend does not provide source information.
    """

    capability_id: str
    extension_names: List[str] = field(default_factory=list)
    mcp_servers: List[McpServer] = field(default_factory=list)
    instruction: Optional[str] = None
    hooks: List[Hook] = field(default_factory=list)
    source: Optional[ExtensionSourceMapping] = None

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> ExtensionCapabilityImplementation:
        """Parse an extension capability implementation from the backend JSON response.

        Expected JSON shape::

            {
                "capabilityId": "default",
                "extensionNames": ["ServiceNow Extension"],
                "instruction": "Only use ...",
                "mcpServers": [
                    {
                        "ordId": "sap.mcp:apiResource:serviceNow:v1",
                        "toolNames": ["create_ticket"]
                    }
                ],
                "hooks": [
                    {
                        "id": "UUID",
                        "hookId": "before_tool_execution",
                        "name": "Before Tool Execution Hook",
                        "hookType": "BEFORE",
                        "deploymentType": "N8N",
                        "timeout": 30,
                        "executionMode": "SYNC",
                        "onFailure": "CONTINUE",
                        "order": 1,
                        "canShortCircuit": true,
                        "n8nWorkflowConfig": {
                            "workflowId": "unique_n8n_workflow_id",
                            "method": "POST"
                        }
                    }
                ],
                "source": {
                    "tools": {
                        "sap_mcp_servicenow_v1_create_ticket": {
                            "extensionName": "servicenow-ext",
                            "extensionVersion": "1",
                            "extensionId": "abc-123"
                        }
                    },
                    "hooks": {
                        "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": {
                            "extensionName": "workflow-ext",
                            "extensionVersion": "1",
                            "extensionId": "def-456"
                        }
                    }
                }
            }

        A plain string or a nested ``{"text": string}`` instruction value are
        both accepted.

        Fields not present in the backend response default to ``None`` or
        empty lists.  Unknown fields (e.g. ``agentOrdId``) are ignored.

        Args:
            obj: Raw dict from the backend response.

        Returns:
            Parsed ``ExtensionCapabilityImplementation`` instance.
        """
        mcp_servers_raw = obj.get("mcpServers", [])
        mcp_servers = [McpServer.from_dict(s) for s in mcp_servers_raw]

        hooks = obj.get("hooks", [])
        hooks_parsed = [Hook.from_dict(h) for h in hooks]

        # The schema defines instruction as {text: string}. Extract the text
        # value, but also accept a plain string for local transport compat.
        raw_instruction = obj.get("instruction")
        if isinstance(raw_instruction, dict):
            instruction = raw_instruction.get("text")
        else:
            instruction = raw_instruction

        source_raw = obj.get("source")
        source = ExtensionSourceMapping.from_dict(source_raw) if source_raw else None

        raw_names = obj.get("extensionNames", [])
        extension_names = [n for n in raw_names if isinstance(n, str)]

        return cls(
            capability_id=obj.get("capabilityId", DEFAULT_EXTENSION_CAPABILITY_ID),
            extension_names=extension_names,
            mcp_servers=mcp_servers,
            instruction=instruction,
            hooks=hooks_parsed,
            source=source,
        )

    def get_extension_for_tool(self, tool_name: str) -> Optional[str]:
        """Look up the extension name that contributed a specific tool.

        Args:
            tool_name: The prefixed tool name (e.g.,
                ``"sap_mcp_servicenow_v1_create_ticket"``).

        Returns:
            Extension name, or ``None`` if source mapping is not available
            or the tool is not found.
        """
        if self.source and tool_name in self.source.tools:
            return self.source.tools[tool_name].extension_name
        return None

    def get_extension_for_hook(self, hook_id: str) -> Optional[str]:
        """Look up the extension name that contributed a specific hook.

        Args:
            hook_id: The hook ID (UUID), e.g.
                ``"3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"``.

        Returns:
            Extension name, or ``None`` if source mapping is not available
            or the hook is not found.
        """
        if self.source and hook_id in self.source.hooks:
            return self.source.hooks[hook_id].extension_name
        return None

    def get_source_info_for_tool(self, tool_name: str) -> Optional[ExtensionSourceInfo]:
        """Look up the full source info for a specific tool.

        Returns the :class:`ExtensionSourceInfo` containing extension name,
        version, and ID for the extension that contributed this tool.  Returns
        ``None`` when source mapping is not available or the tool is not found.

        Args:
            tool_name: The prefixed tool name (e.g.,
                ``"sap_mcp_servicenow_v1_create_ticket"``).

        Returns:
            :class:`ExtensionSourceInfo` for the tool, or ``None``.
        """
        if self.source and tool_name in self.source.tools:
            return self.source.tools[tool_name]
        return None

    def get_source_info_for_hook(self, hook_id: str) -> Optional[ExtensionSourceInfo]:
        """Look up the full source info for a specific hook.

        Returns the :class:`ExtensionSourceInfo` containing extension name,
        version, and ID for the extension that contributed this hook.  Returns
        ``None`` when source mapping is not available or the hook is not found.

        Args:
            hook_id: The hook ID (UUID), e.g.
                ``"3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"``.

        Returns:
            :class:`ExtensionSourceInfo` for the hook, or ``None``.
        """
        if self.source and hook_id in self.source.hooks:
            return self.source.hooks[hook_id]
        return None
