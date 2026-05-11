# Extensibility User Guide

This module enables SAP AI agents to be extended at runtime with third-party tools (delivered via MCP servers) and custom instructions. It communicates with UMS (Unified Metadata Service) via GraphQL to retrieve the active extension's contribution, and provides helpers to declare extensible capabilities in the agent's A2A card for discovery.

## Installation

This package is part of the `application_foundation` SDK. Import and use it directly in your application.

## Import

```python
from sap_cloud_sdk.extensibility import (
    # Runtime
    create_client,
    ExtensibilityClient,
    ExtensionCapabilityImplementation,
    McpServer,
    Hook,
    # A2A card
    build_extension_capabilities,
    ExtensionCapability,
    ToolAdditions,
    Tools,
    HookCapability,
    # Config & constants
    ExtensibilityConfig,
    DEFAULT_EXTENSION_CAPABILITY_ID,
    EXTENSION_CAPABILITY_SCHEMA_VERSION,
    # Enums
    HookType,
    DeploymentType,
    ExecutionMode,
    OnFailure,
    # Exceptions
    ClientCreationError,
    ExtensibilityError,
    TransportError,
)

# For hook payloads
from a2a.types import Message, Role
```

## Quick Start

### Retrieve Extension Tools at Runtime

Create a client with `create_client()`, then call `get_extension_capability_implementation()` on the client. If the service is unavailable, the method returns an empty result and the agent continues with built-in tools only.

```python
from sap_cloud_sdk.extensibility import create_client

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(
    tenant=tenant_id,
)

for server in ext.mcp_servers:
    print(server.ord_id)
    if server.tool_names:
        print("Approved tools:", server.tool_names)

for hook in ext.hooks:
    print(hook.id, hook.n8n_workflow_config.workflow_id)

if ext.instruction:
    print("Extension instruction:", ext.instruction)
```

Reuse the same client instance for multiple calls (e.g. per request lifecycle) to avoid rebuilding the destination-backed transport each time.

### Declare Extension Capabilities for A2A Discovery

Define what parts of the agent are extensible and serialize them into the agent's A2A card:

```python
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
agent_extensions = build_extension_capabilities(capabilities)
# Returns List[AgentExtension] for inclusion in AgentCapabilities.extensions
```

## Concepts

- **Extension Capability** (design-time): A declaration by the agent developer describing what parts of the agent can be extended. Serialized into the A2A card via `build_extension_capabilities()`. This is metadata only -- it carries no runtime data. Currently each agent supports a single extension capability (ID `"default"`). Support for multiple capabilities per agent is planned for a future release.

- **Extension Capability Implementation** (runtime): The active extension's contribution retrieved from the extensibility service at runtime. Contains MCP servers (with tool filtering) and an optional custom instruction.

- **MCP Server**: A Model Context Protocol server contributed by an extension. Each server has an ORD ID and an optional allowlist of approved tool names.

- **Hook**: A workflow to be executed before or after the agent execution. Each hook has a unique UUID `id`, a developer-facing `hook_id` (not guaranteed to be unique), and an `n8n_workflow_config` containing the workflow ID and HTTP method. Hook payloads and responses use the `Message` type from the `a2a.types` module for standardized agent-to-agent communication.

- **UMS (Unified Metadata Service)**: The SAP backend service that manages agent extensions. The module communicates with it via GraphQL over mTLS, using the BTP Destination Service for URL and credential resolution.

- **Graceful Degradation**: A core design principle. The extensibility module never prevents agent startup or causes agent failures. Both `create_client()` and `ExtensibilityClient.get_extension_capability_implementation()` handle errors internally:
  - If the client cannot be constructed (e.g. missing destination credentials in local development), `create_client()` logs the error and returns a client backed by a no-op transport that always returns empty results.
  - If the extensibility service is unavailable or any error occurs during `get_extension_capability_implementation()`, the client logs the error and returns an empty result (no MCP servers, no instruction).
  - In both cases, the agent continues operating with its built-in tools. No errors are raised to the caller.

## API

### `create_client()`

Factory that builds an `ExtensibilityClient` with a transport wired to your BTP destination configuration. This function never raises. If the client cannot be constructed (e.g. missing destination credentials in local development), it logs the error and returns a client backed by a no-op transport that always returns empty results.

```python
def create_client(
    agent_ord_id: str,
    *,
    config: Optional[ExtensibilityConfig] = None,
) -> ExtensibilityClient: ...
```

- `agent_ord_id`: ORD ID of the agent (e.g., `"sap.ai:agent:myAgent:v1"`). Required for the backend transport to identify the agent when querying the extensibility service. Ignored when local mode is active.
- `config`: Optional overrides for destination name and instance. Defaults to `ExtensibilityConfig()`.

### `ExtensibilityClient.get_extension_capability_implementation()`

Retrieves the active extension's MCP servers and instruction from the extensibility service.

```python
def get_extension_capability_implementation(
    self,
    *,
    tenant: str,
    capability_id: str = "default",
    skip_cache: bool = False,
) -> ExtensionCapabilityImplementation: ...
```

- `tenant`: Tenant ID for the request. Used to filter extensions in the UMS GraphQL query and sent as the `X-Tenant` HTTP header. Also used as a cache isolation key. Typically extracted from the incoming request's JWT.
- `capability_id`: Extension capability to look up. Defaults to `"default"`, which is the only supported value currently. The parameter exists to support multiple capabilities per agent in a future release.
- `skip_cache`: When `True`, bypasses the transport-level cache and fetches a fresh result from UMS. The fresh result is still written back into the cache. Defaults to `False`.
- Returns an `ExtensionCapabilityImplementation`. On any error during the request, returns an instance with an empty `mcp_servers` list.

### `ExtensibilityClient.call_hook()`

Executes a hook endpoint with the provided payload.

```python
def call_hook(
    self,
    hook: Hook,
    hook_config: HookConfig,
) -> Optional[Message]: ...
```

- `hook`: Hook configuration object containing workflow config (`n8n_workflow_config`), timeout, and other settings.
- `hook_config`: Hook invocation configuration (`endpoint`, optional `auth_token`, and optional `payload`).
- Returns the response data as a `Message` object, or `None` if no message is produced.
- Raises `TransportError` if the HTTP request fails or the response cannot be parsed as a valid `Message`.
- The hook's `timeout` setting is used for the HTTP request timeout.
- The hook HTTP method is taken from `hook.n8n_workflow_config.method`.
- The workflow ID is taken from `hook.n8n_workflow_config.workflow_id`.

#### `N8nWorkflowConfig`

Workflow configuration embedded in each `Hook`.

```python
@dataclass
class N8nWorkflowConfig:
    workflow_id: str                # Workflow ID
    method: HTTPMethod              # HTTP method used by webhook execution
```

#### `HookConfig`

Runtime invocation config required by `call_hook()`.

```python
@dataclass
class HookConfig:
    endpoint: str                   # Full URL of the hook MCP endpoint
    auth_token: Optional[str]       # Bearer token for authentication
    payload: Optional[dict]         # Optional JSON payload
```

### `build_extension_capabilities()`

Converts extension capability declarations into A2A `AgentExtension` objects.

```python
def build_extension_capabilities(
    extension_capabilities: List[ExtensionCapability],
) -> List[AgentExtension]: ...
```

Each capability is mapped to an `AgentExtension` with:

- `uri`: `urn:sap:extension-capability:v{version}:{id}`
- `description`: from the capability
- `params`: camelCase dict with `capabilityId`, `displayName`, `instructionSupported`, `tools` (serialized `Tools`) and `supportedHooks` (serialized `HookCapability`)
- `required`: always `False`

Validates inputs and logs warnings for empty lists, duplicate IDs, or empty IDs, but always produces output.

### Models

#### `ExtensionCapability`

Design-time declaration for A2A card serialization.

```python
@dataclass
class ExtensionCapability:
    display_name: str                    # Human-readable name
    description: str                     # Description of the capability
    id: str = "default"                  # Capability identifier (only "default" currently supported)
    tools: Tools = ...                   # Tool config (default: Tools(additions=ToolAdditions(enabled=True)))
    instruction_supported: bool = True   # Whether custom instructions are supported
    supported_hooks: List[HookCapability] # List of supported hooks
```

#### `Tools`

Tool-related configuration for an extension capability. Groups all tool options; mirrors the wire format.

```python
@dataclass
class Tools:
    additions: ToolAdditions = ...  # Tool addition config (default: enabled=True)
```

#### `ToolAdditions`

Configuration for tool additions at an extension capability.

```python
@dataclass
class ToolAdditions:
    enabled: bool = True  # Whether tool additions are enabled
```

### `HookCapability`

Configuration for supported hook addition at an extension capability.

```python
@dataclass
class HookCapability:

    id: str
    type: str
    display_name: str
    description: str
```

#### `ExtensionCapabilityImplementation`

Runtime result returned by `ExtensibilityClient.get_extension_capability_implementation()`.

```python
@dataclass
class ExtensionCapabilityImplementation:
    capability_id: str                          # e.g. "default"
    extension_names: List[str] = []             # Names of contributing extensions
    mcp_servers: List[McpServer] = []           # MCP servers from the extension(s)
    instruction: Optional[str] = None           # Custom instruction text
    hooks: List[Hook] = []                     # Custom hooks registered as BEFORE or AFTER
```

#### `McpServer`

An MCP server contributed by an extension.

```python
@dataclass
class McpServer:
    ord_id: str                                  # ORD ID, e.g. "sap.mcp:apiResource:serviceNow:v1"
    global_tenant_id: str                        # Global tenant ID of the MCP server
    tool_names: Optional[List[str]] = None       # Approved tools (None = all approved)
```

- `global_tenant_id` is the global tenant ID of the MCP server.
- `tool_names=None` means all tools on this server are approved for use (no filtering needed).
- `tool_names=["create_ticket", "get_ticket"]` means only those tools are approved.

### `Hook`

A workflow created as a hook to be executed.

```python
@dataclass
class Hook:
    hook_id: str                                 # Developer-facing hook key (not guaranteed unique)
    id: str                                      # Hook ID (UUID)
    name: str                                    # Human-readable name
    type: HookType                               # Hook type (BEFORE, AFTER)
    deployment_type: DeploymentType              # Deployment type (N8N, SERVERLESS)
    n8n_workflow_config: N8nWorkflowConfig       # Workflow config (workflow ID + HTTP method)
    timeout: int                                 # Timeout in seconds
    execution_mode: ExecutionMode                # Execution mode (SYNC, ASYNC)
    on_failure: OnFailure                        # Failure behavior (CONTINUE, BLOCK)
    order: int                                   # Execution order
    can_short_circuit: bool                      # Whether hook can short-circuit execution
```

#### Hook Enums

The `Hook` class uses several enums for type-safe field values:

**HookType**

```python
class HookType(Enum):
    BEFORE = "BEFORE"      # Hook executed before an operation
    AFTER = "AFTER"        # Hook executed after an operation
```

**DeploymentType**

```python
class DeploymentType(Enum):
    N8N = "N8N"                    # Hook deployed on N8N platform
    SERVERLESS = "SERVERLESS"      # Hook deployed as Serverless function
```

**ExecutionMode**

```python
class ExecutionMode(Enum):
    SYNC = "SYNC"      # Synchronous execution - waits for hook to complete
    ASYNC = "ASYNC"    # Asynchronous execution - does not wait for completion
```

**OnFailure**

```python
class OnFailure(Enum):
    CONTINUE = "CONTINUE"  # Continue execution despite hook failure
    BLOCK = "BLOCK"        # Block execution when hook fails
```

**HTTPMethod**

```python
from http import HTTPMethod

# Standard Python HTTP methods enum with values:
# GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, CONNECT, TRACE
```

These enums provide type safety and validation. When parsing from JSON, the `Hook.from_dict()` method validates that enum field values match known types and raises `ValueError` if invalid values are encountered.

#### `ExtensibilityConfig`

Optional configuration overrides for the extensibility service connection.

```python
@dataclass
class ExtensibilityConfig:
    destination_name: Optional[str] = None           # Optional destination name override
    destination_instance: str = "default"             # Destination service instance name
```

### Constants

- `DEFAULT_EXTENSION_CAPABILITY_ID = "default"` -- The only supported capability ID currently. Each agent declares a single extension capability.
- `EXTENSION_CAPABILITY_SCHEMA_VERSION = 1` -- Schema version embedded in extension capability URNs.

## Usage Examples

### Custom Configuration

```python
from sap_cloud_sdk.extensibility import create_client, ExtensibilityConfig

config = ExtensibilityConfig(
    destination_name="MY_EXTENSIBILITY_DESTINATION",
    destination_instance="staging",
)
client = create_client("sap.ai:agent:myAgent:v1", config=config)
ext = client.get_extension_capability_implementation(tenant=tenant_id)
```

### Multiple Capabilities (Future)

Currently each agent supports a single extension capability with the default ID `"default"`. Support for multiple capabilities per agent is planned for a future release. The `capability_id` parameter and the `id` field on `ExtensionCapability` exist to prepare for this. For now, use the defaults:

```python
from sap_cloud_sdk.extensibility import (
    ExtensionCapability,
    build_extension_capabilities,
    create_client,
)

# Design-time: declare a single capability for A2A card
capabilities = [
    ExtensionCapability(
        display_name="Agent Extensions",
        description="Extend the agent with additional tools.",
    ),
]
agent_extensions = build_extension_capabilities(capabilities)

# Runtime: retrieve the extension (uses default capability ID)
client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)
```

### Using MCP Server Data

```python
from sap_cloud_sdk.extensibility import create_client

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

for server in ext.mcp_servers:
    # Connect to the MCP server
    print(f"Server: {server.ord_id}")

    # Filter tools if an allowlist is specified
    if server.tool_names is not None:
        print(f"Approved tools: {server.tool_names}")
    else:
        print("All tools on this server are approved")
```

### Using Hooks

Hooks allow you to execute custom workflows before or after agent operations. The extensibility client provides a `call_hook()` method to invoke hook endpoints.

```python
from sap_cloud_sdk.extensibility import create_client

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

for hook in ext.hooks:
    print(f"Hook ID: {hook.id}")
    print(f"Hook Key: {hook.hook_id}")
    print(f"Type: {hook.type}")
    print(f"Execution mode: {hook.execution_mode}")
    print(f"On failure: {hook.on_failure}")
```

### Calling Hook Endpoints

Use the `call_hook()` method to execute a hook with a custom payload. Payloads use the `Message` type from `a2a.types`.

```python
from sap_cloud_sdk.extensibility import create_client, HookType
from sap_cloud_sdk.extensibility.config import HookConfig
from a2a.types import Message, Role, TextPart

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

# Find a specific hook by type
before_hooks = [h for h in ext.hooks if h.type == HookType.BEFORE]

if before_hooks:
    hook = before_hooks[0]

    hook_config = HookConfig(
        endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
        auth_token="my-secret-token",
        payload=Message(
            message_id="msg-hook-call-001",
            role=Role.user,
            parts=[TextPart(text="Tool execution starting: create_ticket with priority=high")],
        ),
    )

    try:
        response = client.call_hook(hook, hook_config)
        if response:
            print(f"Hook response: {response}")
        else:
            print("Hook returned no content (204)")
    except Exception as e:
        print(f"Hook execution failed: {e}")
```

### Hook Execution Patterns

#### HTTP Methods for Hooks

Hooks support configurable HTTP methods via `hook.n8n_workflow_config.method`. By default, hooks use POST, but can be configured to use GET, PUT, PATCH, or DELETE based on the hook's purpose:

```python
from sap_cloud_sdk.extensibility import create_client
from sap_cloud_sdk.extensibility.config import HookConfig
from http import HTTPMethod
from a2a.types import Message, Role, TextPart

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

for hook in ext.hooks:
    print(f"Hook {hook.name} uses HTTP {hook.n8n_workflow_config.method}")

    hook_config = HookConfig(
        endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
        auth_token="my-secret-token",
        payload=Message(
            message_id="msg-hook-payload-001",
            role=Role.user,
            parts=[TextPart(text="Hook payload")],
        ),
    )

    # The client uses hook.n8n_workflow_config.method internally
    response = client.call_hook(hook, hook_config)
```

The `HTTPMethod` enum ensures type safety:

- `HTTPMethod.GET` - Retrieve data from the hook endpoint
- `HTTPMethod.POST` - Send data to create or process (default)
- `HTTPMethod.PUT` - Update or replace data
- `HTTPMethod.PATCH` - Partially update data
- `HTTPMethod.DELETE` - Delete or cancel an operation

The workflow used for execution comes from `hook.n8n_workflow_config.workflow_id`.

#### Synchronous Hook Execution

For hooks with `execution_mode=ExecutionMode.SYNC`, the call waits for the hook to complete:

```python
from sap_cloud_sdk.extensibility import create_client, ExecutionMode
from sap_cloud_sdk.extensibility.config import HookConfig
from a2a.types import Message, Role, TextPart

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

for hook in ext.hooks:
    if hook.execution_mode == ExecutionMode.SYNC:
        hook_config = HookConfig(
            endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
            auth_token="my-secret-token",
            payload=Message(
                message_id="msg-sync-hook-001",
                role=Role.user,
                parts=[TextPart(text="Processing sync hook")],
            ),
        )
        response = client.call_hook(hook, hook_config)
        # Process response immediately
        if response:
            print(f"Sync hook completed: {response}")
```

#### Handling Hook Failures

Hooks can be configured with different failure behaviors via the `on_failure` field:

```python
from sap_cloud_sdk.extensibility import create_client, OnFailure
from sap_cloud_sdk.extensibility.config import HookConfig
from sap_cloud_sdk.extensibility.exceptions import TransportError
from a2a.types import Message, Role, TextPart

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

for hook in ext.hooks:
    hook_config = HookConfig(
        endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
        auth_token="my-secret-token",
        payload=Message(
            message_id="msg-validate-001",
            role=Role.user,
            parts=[TextPart(text="Validating operation")],
        ),
    )

    try:
        response = client.call_hook(hook, hook_config)
        if response:
            print(f"Hook succeeded: {response}")
    except TransportError as e:
        if hook.on_failure == OnFailure.BLOCK:
            # Hook is configured to block on failure
            print(f"Critical hook failed, blocking: {e}")
            raise
        else:  # OnFailure.CONTINUE
            # Hook is configured to continue on failure
            print(f"Hook failed but continuing: {e}")
```

#### Executing Hooks in Order

Hooks have an `order` field that specifies their execution sequence:

```python
from sap_cloud_sdk.extensibility import create_client
from sap_cloud_sdk.extensibility.config import HookConfig
from a2a.types import Message, Role, TextPart

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

# Sort hooks by order
sorted_hooks = sorted(ext.hooks, key=lambda h: h.order)

for hook in sorted_hooks:
    print(f"Executing hook {hook.name} (order: {hook.order})")
    hook_config = HookConfig(
        endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
        auth_token="my-secret-token",
        payload=Message(
            message_id=f"msg-step-{hook.order}",
            role=Role.user,
            parts=[TextPart(text=f"Step {hook.order}")],
        ),
    )
    response = client.call_hook(hook, hook_config)
    if response:
        print(f"Response: {response}")
```

#### Short-Circuit Execution

Some hooks can short-circuit the main execution flow:

```python
from sap_cloud_sdk.extensibility import create_client, HookType
from sap_cloud_sdk.extensibility.config import HookConfig
from a2a.types import Message, Role, TextPart

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

for hook in ext.hooks:
    if hook.type == HookType.BEFORE:
        hook_config = HookConfig(
            endpoint="https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}",
            auth_token="my-secret-token",
            payload=Message(
                message_id="msg-pre-validation-001",
                role=Role.user,
                parts=[TextPart(text="Pre-validation check")],
            ),
        )
        response = client.call_hook(hook, hook_config)

        # Check if hook wants to short-circuit
        if hook.can_short_circuit and response and response.metadata:
            if response.metadata.get("stop_execution"):
                reason = response.metadata.get("stop_execution_reason", "Unknown")
                print(f"Hook requested short-circuit: {reason}")
                break
```

### Integrating the Extension Instruction

```python
from sap_cloud_sdk.extensibility import create_client

client = create_client("sap.ai:agent:myAgent:v1")
ext = client.get_extension_capability_implementation(tenant=tenant_id)

system_prompt = "You are a helpful assistant."

if ext.instruction:
    system_prompt += f"\n\nExtension instruction:\n{ext.instruction}"
```

## Error Handling

The extensibility module uses graceful degradation throughout: neither `create_client()` nor `get_extension_capability_implementation()` raise exceptions to the caller. The agent always starts and always gets a usable result.

### `create_client()`

On any failure (e.g. missing destination credentials in local development), the function:

1. Logs the error at `ERROR` level with full traceback (`exc_info=True`)
2. Returns an `ExtensibilityClient` backed by a no-op transport
3. Subsequent calls to `get_extension_capability_implementation()` on this client return empty results immediately

No `try/except` wrapper is needed around this call.

### `ExtensibilityClient.get_extension_capability_implementation()`

On any failure (network error, destination resolution failure, service unavailability), the method:

1. Logs the error at `ERROR` level with full traceback (`exc_info=True`)
2. Returns an `ExtensionCapabilityImplementation` with an empty `mcp_servers` list and no instruction
3. The agent continues operating with built-in tools only

No `try/except` wrapper is needed around this call for those failures.

### `build_extension_capabilities()`

Validates inputs and logs warnings for:

- Empty capability lists
- Duplicate capability IDs
- Empty or whitespace-only IDs

Validation issues produce log warnings but never prevent output generation.

### Exception Hierarchy

- `ExtensibilityError` -- Base exception for all extensibility module errors.
- `ClientCreationError(ExtensibilityError)` -- Represents a client construction failure. Not raised by `create_client()` (which handles it internally), but available for use in custom client-construction logic.
- `TransportError(ExtensibilityError)` -- Raised by the transport layer on failure. Not seen when using the client, which catches all transport errors and returns an empty result.

## Service Binding

The module resolves the extensibility service URL and credentials through the SAP BTP Destination Service. The destination is looked up at the subaccount level.

- **Default destination name resolution**: (1) `APPFND_UMS_DESTINATION_NAME` env var, (2) `sap-managed-runtime-ums-{APPFND_CONHOS_LANDSCAPE}`, (3) `EXTENSIBILITY_SERVICE` fallback.
- **Default destination instance**: `default`
- Override via `ExtensibilityConfig(destination_name=...)` when the destination uses a non-standard name.

## Local Development Mode

When running locally (without access to the extensibility service), `create_client()` can be backed by a local JSON file instead of the remote backend. No credentials or network access are required.

### Activation

Local mode is activated in two ways, checked in order:

| Priority | Mechanism | How to activate |
|---|---|---|
| 1 | **Environment variable** | Set `CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE` to a file path |
| 2 | **File-presence detection** | Place a file at `mocks/extensibility.json` in the repository root |

The environment variable takes precedence when both are present. In either case, the JSON file must follow the same schema as the backend response.

> **WARNING: Local mode is for local development only.**
> The local transport performs no authentication and reads data from a plain JSON file on disk. Never use local mode in a deployed or production environment. A warning is logged at `WARNING` level when file-presence detection is used; an info message is logged when the environment variable is used.

### Using file-presence detection (recommended)

Copy the example file to `mocks/extensibility.json`:

```bash
mkdir -p mocks
cp src/sap_cloud_sdk/extensibility/local_extensibility_example.json mocks/extensibility.json
```

Then use `create_client()` as usual -- it will automatically detect the file:

```python
from sap_cloud_sdk.extensibility import create_client

client = create_client("sap.ai:agent:myAgent:v1")  # Uses mocks/extensibility.json automatically
ext = client.get_extension_capability_implementation(tenant=tenant_id)
```

The `mocks/` directory is already in `.gitignore` to prevent accidental commits.

### Using the environment variable

For CI pipelines or switching between multiple fixture files:

```bash
export CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE=path/to/my/extensions.json
```

```python
from sap_cloud_sdk.extensibility import create_client

client = create_client("sap.ai:agent:myAgent:v1")  # Uses the file from the environment variable
ext = client.get_extension_capability_implementation(tenant=tenant_id)
```

### Mock file format

The JSON file uses the same schema as the extensibility backend response:

```json
{
    "capabilityId": "default",
    "extensionNames": ["employee-onboarding-tools"],
    "instruction": "Use the ServiceNow tools for hardware provisioning tasks during onboarding.",
    "mcpServers": [
        {
            "ordId": "sap.mcp:apiResource:serviceNow:v1",
            "toolNames": ["create_hardware_ticket_tool"]
        }
    ],
    "hooks": [
        {
            "hookId": "hook-123",
            "id": "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
            "name": "Currency Conversion",
            "type": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {
                "workflowId": "wf-currency-conversion-001",
                "method": "POST"
            },
            "timeout": 30,
            "executionMode": "SYNC",
            "onFailure": "CONTINUE",
            "order": 0,
            "canShortCircuit": false
        }
    ]
}
```

See `src/sap_cloud_sdk/extensibility/local_extensibility_example.json` for a ready-to-use template.

## ORD Document Integration

> **Note**: This feature should only be used for the system-instance ORD document. It is not intended for use with other ORD documents.

The `add_extension_integration_dependencies()` function injects extension capability MCP servers into the ORD (Open Resource Discovery) document at runtime. This enables the agent to dynamically expose MCP servers from the extensibility service in its ORD document for discovery.

### Import

```python
from sap_cloud_sdk.extensibility import (
    add_extension_integration_dependencies,
    create_client,
)
```

### Usage

```python
from sap_cloud_sdk.extensibility import (
    add_extension_integration_dependencies,
    create_client,
)

# Create an extensibility client
ext_client = create_client("sap.ai:agent:myAgent:v1")

# Load your ORD document (system-instance)
document = load_ord_document(ORD_SYSTEM_INSTANCE_PATH)

# Inject extension integration dependencies
add_extension_integration_dependencies(
    document=document,
    local_tenant_id=local_tenant_id,
    ext_client=ext_client,
)
```

### Parameters

- `document`: The ORD document dict. Modified in-place.
- `local_tenant_id`: Optional tenant ID for fetching tenant-specific extensions.
- `ext_client`: The extensibility client. If not provided, no extension dependencies will be added.

### What It Does

1. Fetches the extension capability implementation from the extensibility service via the client
2. Checks each MCP server against existing document-level integration dependencies
3. Filters out MCP servers that are already present in base integration dependencies
4. Creates a new IntegrationDependency with aspects for only the new MCP servers
5. Injects the IntegrationDependency at document level (full object)
6. Injects the IntegrationDependency ordId reference at agent level (string array)

### Duplicate Filtering

The function checks if an MCP server's ordId already exists in any base integration dependency's aspects. If it exists, that MCP server is skipped to avoid duplication.

If ALL extended MCP servers are already present in base integration dependencies, no extension integration dependency is created.

### Example: Full ORD Endpoint Integration

```python
from sap_cloud_sdk.extensibility import (
    add_extension_integration_dependencies,
    create_client,
)
import json
from pathlib import Path

ORD_SYSTEM_INSTANCE_PATH = Path(__file__).parent / "document-system-instance.json"


def load_ord_document(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def ord_document_system_instance(request: Request) -> JSONResponse:
    local_tenant_id = request.query_params.get("local-tenant-id", "")

    document = load_ord_document(ORD_SYSTEM_INSTANCE_PATH)

    # Replace tenant placeholder
    doc_str = json.dumps(document)
    doc_str = doc_str.replace("{{LOCAL_TENANT_ID}}", local_tenant_id)
    document = json.loads(doc_str)

    # Create extensibility client
    ext_client = create_client("sap.ai:agent:myAgent:v1")

    # Add extension integration dependencies
    add_extension_integration_dependencies(
        document=document,
        local_tenant_id=local_tenant_id,
        ext_client=ext_client,
    )

    return JSONResponse(content=document)
```

### Important Notes

- This function modifies the `document` dict in-place.
- If an MCP server is already defined in a base integration dependency, it will not be duplicated in the extension integration dependency.
- If all MCP servers from extensibility are duplicates, the function returns without adding anything.
- On failure (e.g., extensibility service unavailable), the function logs a warning and continues without adding extension dependencies. The agent continues with its base ORD document.
- The `lastUpdate` field is set to the current timestamp to trigger re-aggregation.

## Notes

- Create one `ExtensibilityClient` (via `create_client()`) and reuse it for multiple capability lookups where appropriate.
- The `instruction` field in the service response accepts both a plain string (`"Use these tools carefully."`) and a nested object (`{"text": "Use these tools carefully."}`).
- Hook payloads and responses use the `Message` type from `a2a.types` for type-safe, structured communication. This ensures compatibility with the Agent-to-Agent (A2A) protocol.
- OpenTelemetry metrics are recorded automatically for `ExtensibilityClient.get_extension_capability_implementation()` and `ExtensibilityClient.call_hook()` calls.
