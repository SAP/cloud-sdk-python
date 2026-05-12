"""Tests for extensibility data models."""

import pytest

from sap_cloud_sdk.extensibility._models import (
    DeploymentType,
    ExecutionMode,
    ExtensionCapability,
    ExtensionCapabilityImplementation,
    ExtensionSourceInfo,
    ExtensionSourceMapping,
    HookType,
    Hook,
    HookCapability,
    McpServer,
    N8nWorkflowConfig,
    OnFailure,
    ToolAdditions,
    Tools,
)
from http import HTTPMethod


class TestToolAdditions:
    """Tests for ToolAdditions dataclass."""

    def test_defaults(self):
        ta = ToolAdditions()
        assert ta.enabled is True

    def test_custom_values(self):
        ta = ToolAdditions(enabled=False)
        assert ta.enabled is False


class TestExtensionCapability:
    """Tests for ExtensionCapability dataclass."""

    def test_defaults(self):
        cap = ExtensionCapability(
            display_name="Onboarding",
            description="Add tools to the onboarding workflow.",
        )
        assert cap.display_name == "Onboarding"
        assert cap.description == "Add tools to the onboarding workflow."
        assert cap.id == "default"
        assert cap.instruction_supported is True
        assert isinstance(cap.tools, Tools)
        assert isinstance(cap.tools.additions, ToolAdditions)
        assert cap.tools.additions.enabled is True

    def test_custom_id(self):
        cap = ExtensionCapability(
            display_name="Doc Processing",
            description="Document processing pipeline.",
            id="doc-processing",
            instruction_supported=False,
        )
        assert cap.id == "doc-processing"
        assert cap.instruction_supported is False

    def test_custom_tool_additions(self):
        ta = ToolAdditions(enabled=False)
        cap = ExtensionCapability(
            display_name="Test",
            description="Test capability.",
            tools=Tools(additions=ta),
        )
        assert cap.tools.additions.enabled is False


class TestMcpServer:
    """Tests for McpServer dataclass."""

    def test_construction(self):
        server = McpServer(
            ord_id="sap.mcp:apiResource:serviceNow:v1",
            global_tenant_id="tenant-abc-123",
            tool_names=["create_ticket", "update_ticket"],
        )
        assert server.ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert server.global_tenant_id == "tenant-abc-123"
        assert server.tool_names == ["create_ticket", "update_ticket"]

    def test_defaults(self):
        server = McpServer(
            ord_id="test",
            global_tenant_id="tenant-xyz",
        )
        assert server.tool_names is None

    def test_from_dict(self):
        data = {
            "ordId": "sap.mcp:apiResource:serviceNow:v1",
            "globalTenantId": "tenant-abc-123",
            "toolNames": ["create_hardware_ticket_tool"],
        }
        server = McpServer.from_dict(data)
        assert server.ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert server.global_tenant_id == "tenant-abc-123"
        assert server.tool_names == ["create_hardware_ticket_tool"]

    def test_from_dict_missing_fields_uses_defaults(self):
        data = {}
        server = McpServer.from_dict(data)
        assert server.ord_id == ""
        assert server.global_tenant_id == ""
        assert server.tool_names is None

    def test_from_dict_with_null_tool_names(self):
        """toolNames: null in JSON maps to None (use all tools)."""
        data = {
            "ordId": "test",
            "globalTenantId": "tenant-xyz",
            "toolNames": None,
        }
        server = McpServer.from_dict(data)
        assert server.tool_names is None

    def test_from_dict_without_tool_names_key(self):
        """Absent toolNames key maps to None (use all tools)."""
        data = {
            "ordId": "test",
            "globalTenantId": "tenant-xyz",
        }
        server = McpServer.from_dict(data)
        assert server.tool_names is None


class TestExtensionCapabilityImplementation:
    """Tests for ExtensionCapabilityImplementation dataclass."""

    def test_defaults(self):
        impl = ExtensionCapabilityImplementation(capability_id="default")
        assert impl.capability_id == "default"
        assert impl.extension_names == []
        assert impl.mcp_servers == []
        assert impl.instruction is None

    def test_full_construction(self):
        server = McpServer(
            ord_id="sap.mcp:apiResource:serviceNow:v1",
            global_tenant_id="tenant-abc-123",
            tool_names=["create_ticket"],
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            extension_names=["servicenow-extension"],
            mcp_servers=[server],
            instruction="Use the create_ticket tool carefully.",
        )
        assert impl.capability_id == "default"
        assert impl.extension_names == ["servicenow-extension"]
        assert len(impl.mcp_servers) == 1
        assert impl.mcp_servers[0].ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert impl.instruction == "Use the create_ticket tool carefully."

    def test_from_dict_full_backend_response(self):
        """Parse a complete backend response matching the confirmed schema."""
        data = {
            "agentOrdId": "sap.ai:agent:employeeOnboarding:v1",
            "extensionNames": ["employee-onboarding-tools"],
            "capabilityId": "onboarding",
            "instruction": "Restored onboarding instruction for E2E.",
            "mcpServers": [
                {
                    "ordId": "sap.mcp:apiResource:serviceNow:v1",
                    "globalTenantId": "tenant-abc-123",
                    "toolNames": ["create_hardware_ticket_tool"],
                },
            ],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.capability_id == "onboarding"
        assert impl.extension_names == ["employee-onboarding-tools"]
        assert impl.instruction == "Restored onboarding instruction for E2E."
        assert len(impl.mcp_servers) == 1

        s1 = impl.mcp_servers[0]
        assert s1.ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert s1.tool_names == ["create_hardware_ticket_tool"]

    def test_from_dict_empty_mcp_servers(self):
        """Handle response with no active extension (empty mcpServers)."""
        data = {
            "capabilityId": "default",
            "instruction": None,
            "mcpServers": [],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.capability_id == "default"
        assert impl.mcp_servers == []
        assert impl.instruction is None

    def test_from_dict_missing_mcp_servers_key(self):
        """Handle response where mcpServers key is absent."""
        data = {"capabilityId": "default"}
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.mcp_servers == []
        assert impl.instruction is None

    def test_from_dict_with_extension_names(self):
        """Handle response that includes extensionNames."""
        data = {
            "capabilityId": "default",
            "extensionNames": ["jira-confluence"],
            "instruction": {"text": "Use Jira tools."},
            "mcpServers": [],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.extension_names == ["jira-confluence"]
        assert impl.instruction == "Use Jira tools."

    def test_from_dict_minimal(self):
        """Handle minimal/empty response."""
        data = {}
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.capability_id == "default"
        assert impl.extension_names == []
        assert impl.mcp_servers == []
        assert impl.instruction is None

    def test_mutable_default_isolation(self):
        """Verify each instance gets its own mcp_servers list."""
        i1 = ExtensionCapabilityImplementation(capability_id="a")
        i2 = ExtensionCapabilityImplementation(capability_id="b")
        i1.mcp_servers.append(McpServer(ord_id="x", global_tenant_id="t1"))
        assert i2.mcp_servers == []

    def test_from_dict_instruction_nested_object(self):
        """Instruction as nested {text: string} is extracted to a flat string."""
        data = {
            "capabilityId": "default",
            "instruction": {"text": "Use these tools carefully."},
            "mcpServers": [],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.instruction == "Use these tools carefully."

    def test_from_dict_instruction_plain_string(self):
        """Plain string instruction is accepted for backwards compatibility."""
        data = {
            "capabilityId": "default",
            "instruction": "Use these tools carefully.",
            "mcpServers": [],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.instruction == "Use these tools carefully."

    def test_from_dict_instruction_nested_empty_text(self):
        """Instruction object with missing text key results in None."""
        data = {
            "capabilityId": "default",
            "instruction": {},
            "mcpServers": [],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.instruction is None

    def test_from_dict_with_hooks(self):
        """Handle response that includes hooks."""
        data = {
            "capabilityId": "default",
            "mcpServers": [],
            "hooks": [
                {
                    "hookId": "before_tool_execution",
                    "id": "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
                    "name": "Before Tool Execution Hook",
                    "hookType": "BEFORE",
                    "deploymentType": "N8N",
                    "n8nWorkflowConfig": {"workflowId": "wf-001", "method": "POST"},
                    "timeout": 30,
                    "executionMode": "SYNC",
                    "onFailure": "CONTINUE",
                    "order": 1,
                    "canShortCircuit": True,
                }
            ],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert len(impl.hooks) == 1
        hook = impl.hooks[0]
        assert hook.hook_id == "before_tool_execution"
        assert hook.id == "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"
        assert hook.name == "Before Tool Execution Hook"
        assert hook.type == HookType.BEFORE
        assert hook.deployment_type == DeploymentType.N8N
        assert hook.n8n_workflow_config.workflow_id == "wf-001"
        assert hook.timeout == 30
        assert hook.execution_mode == ExecutionMode.SYNC
        assert hook.on_failure == OnFailure.CONTINUE
        assert hook.order == 1
        assert hook.can_short_circuit is True

    def test_from_dict_empty_hooks(self):
        """Handle response with empty hooks array."""
        data = {"capabilityId": "default", "mcpServers": [], "hooks": []}
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.hooks == []

    def test_from_dict_missing_hooks_key(self):
        """Handle response where hooks key is absent."""
        data = {"capabilityId": "default", "mcpServers": []}
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.hooks == []

    def test_from_dict_multiple_hooks(self):
        """Handle response with multiple hooks."""
        data = {
            "capabilityId": "default",
            "mcpServers": [],
            "hooks": [
                {
                    "hookId": "before_hook",
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Before Hook",
                    "hookType": "BEFORE",
                    "deploymentType": "N8N",
                    "n8nWorkflowConfig": {"workflowId": "wf-before", "method": "POST"},
                    "timeout": 30,
                    "executionMode": "SYNC",
                    "onFailure": "CONTINUE",
                    "order": 1,
                    "canShortCircuit": True,
                },
                {
                    "hookId": "after_hook",
                    "id": "22222222-2222-4222-8222-222222222222",
                    "name": "After Hook",
                    "hookType": "AFTER",
                    "deploymentType": "N8N",
                    "n8nWorkflowConfig": {"workflowId": "wf-after", "method": "POST"},
                    "timeout": 60,
                    "executionMode": "ASYNC",
                    "onFailure": "BLOCK",
                    "order": 2,
                    "canShortCircuit": False,
                },
            ],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert len(impl.hooks) == 2
        assert impl.hooks[0].hook_id == "before_hook"
        assert impl.hooks[1].hook_id == "after_hook"


class TestHookCapability:
    """Tests for HookCapability dataclass."""

    def test_construction(self):
        hook_cap = HookCapability(
            id="before_tool_execution",
            type=HookType.BEFORE,
            display_name="Before Tool Execution",
            description="Hook that runs before tool execution",
        )
        assert hook_cap.id == "before_tool_execution"
        assert hook_cap.type == "BEFORE"
        assert hook_cap.display_name == "Before Tool Execution"
        assert hook_cap.description == "Hook that runs before tool execution"

    def test_construction_with_different_types(self):
        """Test construction with different hook types."""
        after_hook = HookCapability(
            id="after_tool_execution",
            type=HookType.AFTER,
            display_name="After Tool Execution",
            description="Hook that runs after tool execution",
        )
        assert after_hook.type == "AFTER"

        before_hook = HookCapability(
            id="validation_hook",
            type=HookType.BEFORE,
            display_name="Before Hook",
            description="Hook for validation",
        )
        assert before_hook.type == "BEFORE"


class TestHook:
    """Tests for Hook dataclass."""

    def test_construction(self):
        hook = Hook(
            hook_id="before_tool_execution",
            id="9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
            n8n_workflow_config=N8nWorkflowConfig(
                workflow_id="wf-001",
                method=HTTPMethod.POST,
            ),
            name="Before Tool Execution Hook",
            type=HookType.BEFORE,
            deployment_type=DeploymentType.N8N,
            timeout=30,
            execution_mode=ExecutionMode.SYNC,
            on_failure=OnFailure.CONTINUE,
            order=1,
            can_short_circuit=True,
        )
        assert hook.hook_id == "before_tool_execution"
        assert hook.id == "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"
        assert hook.n8n_workflow_config.workflow_id == "wf-001"
        assert hook.n8n_workflow_config.method == HTTPMethod.POST
        assert hook.name == "Before Tool Execution Hook"
        assert hook.type == "BEFORE"
        assert hook.deployment_type == "N8N"
        assert hook.timeout == 30
        assert hook.execution_mode == "SYNC"
        assert hook.on_failure == "CONTINUE"
        assert hook.order == 1
        assert hook.can_short_circuit is True

    def test_from_dict_complete(self):
        """Parse a complete hook entry from backend JSON."""
        data = {
            "hookId": "before_tool_execution",
            "id": "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
            "name": "Before Tool Execution Hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-001", "method": "POST"},
            "timeout": 30,
            "executionMode": "SYNC",
            "onFailure": "CONTINUE",
            "order": 1,
            "canShortCircuit": True,
        }
        hook = Hook.from_dict(data)
        assert hook.hook_id == "before_tool_execution"
        assert hook.id == "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"
        assert hook.name == "Before Tool Execution Hook"
        assert hook.type == HookType.BEFORE
        assert hook.deployment_type == DeploymentType.N8N
        assert hook.n8n_workflow_config.workflow_id == "wf-001"
        assert hook.n8n_workflow_config.method == HTTPMethod.POST
        assert hook.timeout == 30
        assert hook.execution_mode == ExecutionMode.SYNC
        assert hook.on_failure == OnFailure.CONTINUE
        assert hook.order == 1
        assert hook.can_short_circuit is True

    def test_from_dict_missing_fields_uses_defaults(self):
        """Missing required enum fields raises ValueError."""
        data = {}
        with pytest.raises(ValueError, match="Invalid or missing hookType"):
            Hook.from_dict(data)

    def test_from_dict_partial_fields(self):
        """Parse hook with only some fields present but required enums provided."""
        data = {
            "hookId": "partial_hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-partial", "method": "POST"},
        }
        hook = Hook.from_dict(data)
        assert hook.hook_id == "partial_hook"
        assert hook.n8n_workflow_config.workflow_id == "wf-partial"
        assert hook.type == HookType.BEFORE
        assert hook.deployment_type == DeploymentType.N8N
        # Other fields should use defaults
        assert hook.id == ""
        assert hook.timeout == 30

    def test_from_dict_async_execution_mode(self):
        """Parse hook with ASYNC execution mode."""
        data = {
            "hookId": "async_hook",
            "id": "6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22",
            "name": "Async Hook",
            "hookType": "AFTER",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-async-001", "method": "POST"},
            "timeout": 60,
            "executionMode": "ASYNC",
            "onFailure": "BLOCK",
            "order": 2,
            "canShortCircuit": False,
        }
        hook = Hook.from_dict(data)
        assert hook.execution_mode == ExecutionMode.ASYNC
        assert hook.on_failure == OnFailure.BLOCK
        assert hook.timeout == 60
        assert hook.order == 2
        assert hook.can_short_circuit is False

    def test_from_dict_different_deployment_types(self):
        """Parse Hook with different deployment types."""
        n8n_data = {
            "hookId": "n8n_hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-n8n", "method": "POST"},
        }
        n8n_hook = Hook.from_dict(n8n_data)
        assert n8n_hook.deployment_type == DeploymentType.N8N

        serverless_data = {
            "hookId": "lambda_hook",
            "hookType": "AFTER",
            "deploymentType": "SERVERLESS",
            "n8nWorkflowConfig": {
                "workflowId": "wf-serverless",
                "method": "POST",
            },
        }
        serverless_hook = Hook.from_dict(serverless_data)
        assert serverless_hook.deployment_type == DeploymentType.SERVERLESS

    def test_from_dict_different_hook_types(self):
        """Parse Hook with different hook types."""
        before_data = {
            "hookId": "before",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-before", "method": "POST"},
        }
        before_hook = Hook.from_dict(before_data)
        assert before_hook.type == HookType.BEFORE

        after_data = {
            "hookId": "after",
            "hookType": "AFTER",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-after", "method": "POST"},
        }
        after_hook = Hook.from_dict(after_data)
        assert after_hook.type == HookType.AFTER

    def test_from_dict_can_short_circuit_true(self):
        """Parse hook with canShortCircuit set to true."""
        data = {
            "hookId": "short_circuit",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "canShortCircuit": True,
            "n8nWorkflowConfig": {"workflowId": "wf-short", "method": "POST"},
        }
        hook = Hook.from_dict(data)
        assert hook.can_short_circuit is True

    def test_from_dict_can_short_circuit_false(self):
        """Parse hook with canShortCircuit explicitly set to false."""
        data = {
            "hookId": "no_short_circuit",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "canShortCircuit": False,
            "n8nWorkflowConfig": {"workflowId": "wf-no-short", "method": "POST"},
        }
        hook = Hook.from_dict(data)
        assert hook.can_short_circuit is False

    def test_from_dict_workflow_config_preserved(self):
        """Parse hook with n8nWorkflowConfig."""
        data = {
            "hookId": "wf_hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-special-123", "method": "PUT"},
        }
        hook = Hook.from_dict(data)
        assert hook.n8n_workflow_config.workflow_id == "wf-special-123"
        assert hook.n8n_workflow_config.method == HTTPMethod.PUT

    def test_from_dict_empty_string_values(self):
        """Parse hook with empty string enum values raises ValueError."""
        data = {
            "hookId": "",
            "id": "",
            "name": "",
            "hookType": "",
            "deploymentType": "",
            "n8nWorkflowConfig": {"workflowId": "", "method": "POST"},
        }
        with pytest.raises(ValueError, match="Invalid or missing hookType"):
            Hook.from_dict(data)

    def test_from_dict_different_http_methods(self):
        """Parse hook with different HTTP methods."""
        for method_str, method_enum in [
            ("GET", HTTPMethod.GET),
            ("POST", HTTPMethod.POST),
            ("PUT", HTTPMethod.PUT),
            ("PATCH", HTTPMethod.PATCH),
            ("DELETE", HTTPMethod.DELETE),
        ]:
            data = {
                "hookId": f"{method_str.lower()}_hook",
                "hookType": "BEFORE",
                "deploymentType": "N8N",
                "n8nWorkflowConfig": {
                    "workflowId": f"wf-{method_str.lower()}",
                    "method": method_str,
                },
            }
            hook = Hook.from_dict(data)
            assert hook.n8n_workflow_config.method == method_enum

    def test_from_dict_method_defaults_to_post(self):
        """When method field is missing, it defaults to POST."""
        data = {
            "hookId": "hook_without_method",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-no-method"},
        }
        hook = Hook.from_dict(data)
        assert hook.n8n_workflow_config.method == HTTPMethod.POST

    def test_from_dict_invalid_hook_type_raises_error(self):
        """Invalid hookType value raises ValueError."""
        data = {
            "hookId": "invalid_hook",
            "hookType": "INVALID_TYPE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-invalid-type", "method": "POST"},
        }
        with pytest.raises(
            ValueError, match="Invalid or missing hookType.*INVALID_TYPE"
        ):
            Hook.from_dict(data)

    def test_from_dict_invalid_deployment_type_raises_error(self):
        """Invalid deploymentType value raises ValueError."""
        data = {
            "hookId": "invalid_hook",
            "hookType": "BEFORE",
            "deploymentType": "INVALID_DEPLOYMENT",
            "n8nWorkflowConfig": {
                "workflowId": "wf-invalid-deployment",
                "method": "POST",
            },
        }
        with pytest.raises(
            ValueError, match="Invalid or missing deploymentType.*INVALID_DEPLOYMENT"
        ):
            Hook.from_dict(data)


class TestExtensionSourceInfo:
    """Tests for ExtensionSourceInfo dataclass."""

    def test_construction(self):
        """Construct with explicit fields."""
        info = ExtensionSourceInfo(
            extension_name="my-ext",
            extension_version="2",
            extension_id="uuid-123",
        )
        assert info.extension_name == "my-ext"
        assert info.extension_version == "2"
        assert info.extension_id == "uuid-123"

    def test_from_dict(self):
        """Parse from backend JSON shape."""
        data = {
            "extensionName": "ap-invoice-extension",
            "extensionVersion": "3",
            "extensionId": "a1b2c3d4-e5f6",
        }
        info = ExtensionSourceInfo.from_dict(data)
        assert info.extension_name == "ap-invoice-extension"
        assert info.extension_version == "3"
        assert info.extension_id == "a1b2c3d4-e5f6"

    def test_from_dict_defaults(self):
        """Parse from empty dict uses defaults."""
        info = ExtensionSourceInfo.from_dict({})
        assert info.extension_name == ""
        assert info.extension_version == ""
        assert info.extension_id == ""

    def test_from_dict_partial(self):
        """Parse from partial dict fills missing fields with defaults."""
        data = {"extensionName": "my-ext"}
        info = ExtensionSourceInfo.from_dict(data)
        assert info.extension_name == "my-ext"
        assert info.extension_version == ""
        assert info.extension_id == ""

    def test_from_value_string(self):
        """Plain string (old format) creates info with name only."""
        info = ExtensionSourceInfo.from_value("servicenow-ext")
        assert info.extension_name == "servicenow-ext"
        assert info.extension_version == ""
        assert info.extension_id == ""

    def test_from_value_dict(self):
        """Dict (new format) creates full info."""
        data = {
            "extensionName": "my-ext",
            "extensionVersion": "5",
            "extensionId": "uuid-abc",
        }
        info = ExtensionSourceInfo.from_value(data)
        assert info.extension_name == "my-ext"
        assert info.extension_version == "5"
        assert info.extension_id == "uuid-abc"

    def test_from_value_unexpected_type(self):
        """Unexpected type produces empty info."""
        info = ExtensionSourceInfo.from_value(42)
        assert info.extension_name == ""
        assert info.extension_version == ""
        assert info.extension_id == ""


class TestExtensionSourceMapping:
    """Tests for ExtensionSourceMapping dataclass."""

    def test_defaults(self):
        """Default construction produces empty dicts."""
        mapping = ExtensionSourceMapping()
        assert mapping.tools == {}
        assert mapping.hooks == {}

    def test_construction(self):
        """Construct with explicit tools and hooks."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        info_b = ExtensionSourceInfo(
            extension_name="ext-b", extension_version="2", extension_id="id-b"
        )
        mapping = ExtensionSourceMapping(
            tools={"prefix_tool_a": info_a, "prefix_tool_b": info_b},
            hooks={"9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11": info_a},
        )
        assert mapping.tools["prefix_tool_a"].extension_name == "ext-a"
        assert mapping.tools["prefix_tool_b"].extension_name == "ext-b"
        assert (
            mapping.hooks["9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"].extension_name
            == "ext-a"
        )

    def test_from_dict_full_new_format(self):
        """Parse a complete source mapping from backend JSON (new format)."""
        data = {
            "tools": {
                "sap_mcp_servicenow_v1_create_ticket": {
                    "extensionName": "servicenow-ext",
                    "extensionVersion": "2",
                    "extensionId": "uuid-sn",
                },
                "sap_mcp_jira_v1_create_issue": {
                    "extensionName": "jira-ext",
                    "extensionVersion": "1",
                    "extensionId": "uuid-jira",
                },
            },
            "hooks": {
                "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": {
                    "extensionName": "workflow-ext",
                    "extensionVersion": "3",
                    "extensionId": "uuid-wf",
                },
                "6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22": {
                    "extensionName": "audit-ext",
                    "extensionVersion": "1",
                    "extensionId": "uuid-audit",
                },
            },
        }
        mapping = ExtensionSourceMapping.from_dict(data)
        assert (
            mapping.tools["sap_mcp_servicenow_v1_create_ticket"].extension_name
            == "servicenow-ext"
        )
        assert (
            mapping.tools["sap_mcp_servicenow_v1_create_ticket"].extension_version
            == "2"
        )
        assert (
            mapping.tools["sap_mcp_servicenow_v1_create_ticket"].extension_id
            == "uuid-sn"
        )
        assert (
            mapping.tools["sap_mcp_jira_v1_create_issue"].extension_name == "jira-ext"
        )
        assert (
            mapping.hooks["3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"].extension_name
            == "workflow-ext"
        )
        assert (
            mapping.hooks["6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22"].extension_name
            == "audit-ext"
        )

    def test_from_dict_old_format_backward_compat(self):
        """Parse old format where values are plain strings."""
        data = {
            "tools": {
                "sap_mcp_servicenow_v1_create_ticket": "servicenow-ext",
            },
            "hooks": {
                "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": "workflow-ext",
            },
        }
        mapping = ExtensionSourceMapping.from_dict(data)
        assert (
            mapping.tools["sap_mcp_servicenow_v1_create_ticket"].extension_name
            == "servicenow-ext"
        )
        assert (
            mapping.tools["sap_mcp_servicenow_v1_create_ticket"].extension_version == ""
        )
        assert mapping.tools["sap_mcp_servicenow_v1_create_ticket"].extension_id == ""
        assert (
            mapping.hooks["3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"].extension_name
            == "workflow-ext"
        )

    def test_from_dict_empty(self):
        """Parse empty dict produces empty mappings."""
        mapping = ExtensionSourceMapping.from_dict({})
        assert mapping.tools == {}
        assert mapping.hooks == {}

    def test_from_dict_only_tools(self):
        """Parse with only tools key present."""
        data = {
            "tools": {
                "prefix_tool": {
                    "extensionName": "my-ext",
                    "extensionVersion": "1",
                    "extensionId": "id-1",
                }
            }
        }
        mapping = ExtensionSourceMapping.from_dict(data)
        assert mapping.tools["prefix_tool"].extension_name == "my-ext"
        assert mapping.hooks == {}

    def test_from_dict_only_hooks(self):
        """Parse with only hooks key present."""
        data = {
            "hooks": {
                "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11": {
                    "extensionName": "my-ext",
                    "extensionVersion": "1",
                    "extensionId": "id-1",
                }
            }
        }
        mapping = ExtensionSourceMapping.from_dict(data)
        assert mapping.tools == {}
        assert (
            mapping.hooks["9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"].extension_name
            == "my-ext"
        )

    def test_mutable_default_isolation(self):
        """Verify each instance gets its own tools and hooks dicts."""
        m1 = ExtensionSourceMapping()
        m2 = ExtensionSourceMapping()
        m1.tools["new_tool"] = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        m1.hooks["new_hook"] = ExtensionSourceInfo(
            extension_name="ext-b", extension_version="1", extension_id="id-b"
        )
        assert m2.tools == {}
        assert m2.hooks == {}


class TestExtensionCapabilityImplementationSource:
    """Tests for source mapping on ExtensionCapabilityImplementation."""

    def test_from_dict_with_source_new_format(self):
        """Parse a backend response that includes a source mapping (new format)."""
        data = {
            "capabilityId": "default",
            "extensionNames": ["servicenow-ext"],
            "mcpServers": [
                {
                    "ordId": "sap.mcp:apiResource:serviceNow:v1",
                    "url": "https://example.com/mcp",
                    "toolPrefix": "sap_mcp_servicenow_v1_",
                    "toolNames": ["create_ticket"],
                }
            ],
            "hooks": [
                {
                    "hookId": "before_hook",
                    "id": "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e",
                    "name": "Before Hook",
                    "hookType": "BEFORE",
                    "deploymentType": "N8N",
                    "n8nWorkflowConfig": {
                        "workflowId": "wf-before-001",
                        "method": "POST",
                    },
                    "timeout": 30,
                    "executionMode": "SYNC",
                    "onFailure": "CONTINUE",
                    "order": 1,
                    "canShortCircuit": False,
                }
            ],
            "source": {
                "tools": {
                    "sap_mcp_servicenow_v1_create_ticket": {
                        "extensionName": "servicenow-ext",
                        "extensionVersion": "2",
                        "extensionId": "uuid-sn",
                    }
                },
                "hooks": {
                    "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": {
                        "extensionName": "workflow-ext",
                        "extensionVersion": "1",
                        "extensionId": "uuid-wf",
                    }
                },
            },
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.source is not None
        assert (
            impl.source.tools["sap_mcp_servicenow_v1_create_ticket"].extension_name
            == "servicenow-ext"
        )
        assert (
            impl.source.tools["sap_mcp_servicenow_v1_create_ticket"].extension_version
            == "2"
        )
        assert (
            impl.source.tools["sap_mcp_servicenow_v1_create_ticket"].extension_id
            == "uuid-sn"
        )
        assert (
            impl.source.hooks["3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"].extension_name
            == "workflow-ext"
        )

    def test_from_dict_with_source_old_format(self):
        """Parse a backend response with old string-based source mapping."""
        data = {
            "capabilityId": "default",
            "mcpServers": [],
            "source": {
                "tools": {"sap_mcp_servicenow_v1_create_ticket": "servicenow-ext"},
                "hooks": {"3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": "workflow-ext"},
            },
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.source is not None
        assert (
            impl.source.tools["sap_mcp_servicenow_v1_create_ticket"].extension_name
            == "servicenow-ext"
        )
        assert (
            impl.source.tools["sap_mcp_servicenow_v1_create_ticket"].extension_version
            == ""
        )
        assert (
            impl.source.hooks["3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e"].extension_name
            == "workflow-ext"
        )

    def test_from_dict_without_source(self):
        """Absent source key results in None."""
        data = {
            "capabilityId": "default",
            "mcpServers": [],
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.source is None

    def test_from_dict_with_null_source(self):
        """Explicit null source results in None."""
        data = {
            "capabilityId": "default",
            "mcpServers": [],
            "source": None,
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.source is None

    def test_from_dict_with_empty_source(self):
        """Empty source object is treated as absent (no attribution data)."""
        data = {
            "capabilityId": "default",
            "mcpServers": [],
            "source": {},
        }
        impl = ExtensionCapabilityImplementation.from_dict(data)
        assert impl.source is None

    def test_get_extension_for_tool_with_source(self):
        """Tool in source mapping returns the specific extension name."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        info_b = ExtensionSourceInfo(
            extension_name="ext-b", extension_version="2", extension_id="id-b"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={
                    "prefix_tool_a": info_a,
                    "prefix_tool_b": info_b,
                },
            ),
        )
        assert impl.get_extension_for_tool("prefix_tool_a") == "ext-a"
        assert impl.get_extension_for_tool("prefix_tool_b") == "ext-b"

    def test_get_extension_for_tool_not_in_source(self):
        """Tool NOT in source mapping returns None."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={"prefix_tool_a": info_a},
            ),
        )
        assert impl.get_extension_for_tool("unknown_tool") is None

    def test_get_extension_for_tool_no_source(self):
        """No source mapping returns None."""
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
        )
        assert impl.get_extension_for_tool("any_tool") is None

    def test_get_extension_for_hook_with_source(self):
        """Hook in source mapping returns the specific extension name."""
        info_wf = ExtensionSourceInfo(
            extension_name="workflow-ext", extension_version="1", extension_id="id-wf"
        )
        info_audit = ExtensionSourceInfo(
            extension_name="audit-ext", extension_version="2", extension_id="id-audit"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                hooks={
                    "3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": info_wf,
                    "6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22": info_audit,
                },
            ),
        )
        assert (
            impl.get_extension_for_hook("3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e")
            == "workflow-ext"
        )
        assert (
            impl.get_extension_for_hook("6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22")
            == "audit-ext"
        )

    def test_get_extension_for_hook_not_in_source(self):
        """Hook NOT in source mapping returns None."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                hooks={"9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11": info_a},
            ),
        )
        assert (
            impl.get_extension_for_hook("00000000-0000-4000-8000-000000000000") is None
        )

    def test_get_extension_for_hook_no_source(self):
        """No source mapping returns None."""
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
        )
        assert (
            impl.get_extension_for_hook("00000000-0000-4000-8000-000000000000") is None
        )

    def test_get_extension_for_hook_no_source_no_names(self):
        """No source mapping and no extension_names returns None."""
        impl = ExtensionCapabilityImplementation(capability_id="default")
        assert (
            impl.get_extension_for_hook("00000000-0000-4000-8000-000000000000") is None
        )

    def test_get_source_info_for_tool_with_source(self):
        """Tool in source mapping returns full ExtensionSourceInfo."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="3", extension_id="uuid-a"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={"prefix_tool_a": info_a},
            ),
        )
        result = impl.get_source_info_for_tool("prefix_tool_a")
        assert result is not None
        assert result.extension_name == "ext-a"
        assert result.extension_version == "3"
        assert result.extension_id == "uuid-a"

    def test_get_source_info_for_tool_not_found(self):
        """Tool NOT in source mapping returns None."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={"prefix_tool_a": info_a},
            ),
        )
        assert impl.get_source_info_for_tool("unknown_tool") is None

    def test_get_source_info_for_tool_no_source(self):
        """No source mapping returns None."""
        impl = ExtensionCapabilityImplementation(capability_id="default")
        assert impl.get_source_info_for_tool("any_tool") is None

    def test_get_source_info_for_hook_with_source(self):
        """Hook in source mapping returns full ExtensionSourceInfo."""
        info_wf = ExtensionSourceInfo(
            extension_name="workflow-ext", extension_version="5", extension_id="uuid-wf"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                hooks={"3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e": info_wf},
            ),
        )
        result = impl.get_source_info_for_hook("3f5c8c8a-7b4d-4f9c-a4c0-7d5cb1a39f7e")
        assert result is not None
        assert result.extension_name == "workflow-ext"
        assert result.extension_version == "5"
        assert result.extension_id == "uuid-wf"

    def test_get_source_info_for_hook_not_found(self):
        """Hook NOT in source mapping returns None."""
        info_a = ExtensionSourceInfo(
            extension_name="ext-a", extension_version="1", extension_id="id-a"
        )
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                hooks={"9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11": info_a},
            ),
        )
        assert (
            impl.get_source_info_for_hook("00000000-0000-4000-8000-000000000000")
            is None
        )

    def test_get_source_info_for_hook_no_source(self):
        """No source mapping returns None."""
        impl = ExtensionCapabilityImplementation(capability_id="default")
        assert (
            impl.get_source_info_for_hook("00000000-0000-4000-8000-000000000000")
            is None
        )
