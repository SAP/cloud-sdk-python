"""Tests for UMS response parsing helpers."""

from http import HTTPMethod

from sap_cloud_sdk.extensibility._models import (
    DeploymentType,
    ExecutionMode,
    HookType,
    OnFailure,
)
from sap_cloud_sdk.extensibility._ums_transport import (
    _build_hook,
    _build_mcp_server,
    _build_source_mapping,
    _transform_ums_response,
)

from tests.extensibility.unit._ums_test_helpers import (
    UMS_RESPONSE_SINGLE,
    UMS_RESPONSE_MULTIPLE,
    UMS_RESPONSE_EMPTY,
    UMS_RESPONSE_NO_INSTRUCTION,
    UMS_RESPONSE_EMPTY_INSTRUCTION,
    UMS_RESPONSE_DIFFERENT_CAPABILITY,
)


class TestBuildMcpServer:
    def test_basic(self):
        addition = {
            "type": "MCP",
            "mcpConfig": {
                "globalTenantId": "tenant-abc-123",
                "ordId": "sap.mcp:apiResource:serviceNow:v1",
                "toolNames": ["create_ticket", "update_ticket"],
            },
        }
        server = _build_mcp_server(addition)
        assert server.ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert server.global_tenant_id == "tenant-abc-123"
        assert server.tool_names == ["create_ticket", "update_ticket"]

    def test_missing_tool_names(self):
        addition = {
            "mcpConfig": {
                "globalTenantId": "tenant-xyz",
                "ordId": "sap.mcp:apiResource:x:v1",
            }
        }
        server = _build_mcp_server(addition)
        assert server.ord_id == "sap.mcp:apiResource:x:v1"
        assert server.global_tenant_id == "tenant-xyz"
        assert server.tool_names is None

    def test_empty_dict(self):
        server = _build_mcp_server({})
        assert server.ord_id == ""
        assert server.global_tenant_id == ""
        assert server.tool_names is None


# ---------------------------------------------------------------------------
# Tests: _build_hook
# ---------------------------------------------------------------------------


class TestBuildHook:
    def test_before_hook(self):
        raw = {
            "hookId": "before_tool_execution",
            "type": "BEFORE",
            "name": "Before Tool Execution",
            "onFailure": "CONTINUE",
            "timeout": 30,
            "deploymentType": "N8N",
            "canShortCircuit": False,
            "n8nWorkflowConfig": {"workflowId": "wf-before-001", "method": "POST"},
        }
        hook = _build_hook(raw)
        assert hook is not None
        assert hook.id == ""
        assert hook.hook_id == "before_tool_execution"
        assert hook.name == "Before Tool Execution"
        assert hook.type == HookType.BEFORE
        assert hook.deployment_type == DeploymentType.N8N
        assert hook.n8n_workflow_config.workflow_id == "wf-before-001"
        assert hook.n8n_workflow_config.method == HTTPMethod.POST
        assert hook.timeout == 30
        assert hook.execution_mode == ExecutionMode.SYNC
        assert hook.on_failure == OnFailure.CONTINUE
        assert hook.order == 0
        assert hook.can_short_circuit is False

    def test_after_hook(self):
        raw = {
            "hookId": "after_tool_execution",
            "type": "AFTER",
            "name": "After Tool Execution",
            "onFailure": "BLOCK",
            "timeout": 60,
            "deploymentType": "SERVERLESS",
            "canShortCircuit": True,
            "n8nWorkflowConfig": {"workflowId": "wf-after-001", "method": "POST"},
        }
        hook = _build_hook(raw)
        assert hook is not None
        assert hook.type == HookType.AFTER
        assert hook.on_failure == OnFailure.BLOCK
        assert hook.timeout == 60
        assert hook.deployment_type == DeploymentType.SERVERLESS
        assert hook.can_short_circuit is True

    def test_unknown_type_returns_none(self):
        raw = {"hookId": "x", "type": "UNKNOWN"}
        hook = _build_hook(raw)
        assert hook is None

    def test_missing_type_returns_none(self):
        raw = {"hookId": "x"}
        hook = _build_hook(raw)
        assert hook is None

    def test_empty_dict(self):
        hook = _build_hook({})
        assert hook is None


# ---------------------------------------------------------------------------
# Tests: _build_source_mapping
# ---------------------------------------------------------------------------


class TestBuildSourceMapping:
    def test_maps_tools_by_tool_name(self):
        nodes = [
            {
                "id": "ext-1",
                "title": "My Extension",
                "extensionVersion": "1.2.3",
                "capabilityImplementations": [
                    {
                        "capabilityId": "default",
                        "tools": {
                            "additions": [
                                {
                                    "mcpConfig": {
                                        "globalTenantId": "tenant-ext-1",
                                        "toolNames": ["tool_a", "tool_b"],
                                    }
                                },
                            ]
                        },
                        "hooks": [],
                    }
                ],
            }
        ]
        mapping = _build_source_mapping(nodes, [], [])
        assert "tool_a" in mapping.tools
        assert mapping.tools["tool_a"].extension_name == "My Extension"
        assert mapping.tools["tool_a"].extension_id == "ext-1"
        assert mapping.tools["tool_a"].extension_version == "1.2.3"
        assert "tool_b" in mapping.tools

    def test_maps_hooks_by_id(self):
        nodes = [
            {
                "id": "ext-1",
                "title": "Hook Extension",
                "extensionVersion": "4.0.0",
                "capabilityImplementations": [
                    {
                        "capabilityId": "default",
                        "tools": {"additions": []},
                        "hooks": [
                            {
                                "id": "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
                                "hookId": "before_tool_execution",
                            }
                        ],
                    }
                ],
            }
        ]
        mapping = _build_source_mapping(nodes, [], [])
        assert "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11" in mapping.hooks
        assert (
            mapping.hooks["9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"].extension_name
            == "Hook Extension"
        )
        assert (
            mapping.hooks["9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"].extension_version
            == "4.0.0"
        )

    def test_empty_nodes(self):
        mapping = _build_source_mapping([], [], [])
        assert mapping.tools == {}
        assert mapping.hooks == {}

    def test_null_hooks_in_capability(self):
        """hooks: null should not crash _build_source_mapping."""
        nodes = [
            {
                "id": "ext-1",
                "title": "Null hooks",
                "capabilityImplementations": [
                    {
                        "capabilityId": "default",
                        "tools": {"additions": []},
                        "hooks": None,
                    }
                ],
            }
        ]
        mapping = _build_source_mapping(nodes, [], [])
        assert mapping.hooks == {}

    def test_missing_extension_version_defaults_to_empty(self):
        """Node without extensionVersion should default to empty string."""
        nodes = [
            {
                "id": "ext-1",
                "title": "No Version",
                "capabilityImplementations": [
                    {
                        "capabilityId": "default",
                        "tools": {
                            "additions": [
                                {
                                    "mcpConfig": {
                                        "globalTenantId": "tenant-nv-1",
                                        "toolNames": ["tool_x"],
                                    }
                                }
                            ],
                        },
                        "hooks": [],
                    }
                ],
            }
        ]
        mapping = _build_source_mapping(nodes, [], [])
        assert mapping.tools["tool_x"].extension_version == ""

# ---------------------------------------------------------------------------
# Tests: _transform_ums_response
# ---------------------------------------------------------------------------


class TestTransformUmsResponse:
    def test_single_extension(self):
        result = _transform_ums_response(UMS_RESPONSE_SINGLE["data"], "default")
        assert result.capability_id == "default"
        assert result.extension_names == ["ServiceNow Extension"]
        assert result.instruction == "Use ServiceNow tools for ticket management."
        assert len(result.mcp_servers) == 1
        assert result.mcp_servers[0].ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert result.mcp_servers[0].tool_names == ["create_ticket", "update_ticket"]
        assert len(result.hooks) == 1
        assert result.hooks[0].hook_id == "before_tool_execution"
        assert result.hooks[0].type == HookType.BEFORE

    def test_multiple_extensions(self):
        result = _transform_ums_response(UMS_RESPONSE_MULTIPLE["data"], "default")
        assert result.extension_names == ["ServiceNow Extension", "Jira Extension"]
        assert len(result.mcp_servers) == 2
        assert result.mcp_servers[0].ord_id == "sap.mcp:apiResource:serviceNow:v1"
        assert result.mcp_servers[1].ord_id == "sap.mcp:apiResource:jira:v1"
        assert len(result.hooks) == 1
        assert result.hooks[0].type == HookType.AFTER
        # Instructions from all extensions are joined
        assert result.instruction == "ServiceNow instruction.\n\nJira instruction."

    def test_empty_edges(self):
        result = _transform_ums_response(UMS_RESPONSE_EMPTY["data"], "default")
        assert result.capability_id == "default"
        assert result.extension_names == []
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.hooks == []

    def test_no_instruction(self):
        result = _transform_ums_response(UMS_RESPONSE_NO_INSTRUCTION["data"], "default")
        assert result.instruction is None
        assert len(result.mcp_servers) == 1

    def test_empty_instruction_text(self):
        result = _transform_ums_response(
            UMS_RESPONSE_EMPTY_INSTRUCTION["data"], "default"
        )
        # Empty string is falsy, so instruction stays None
        assert result.instruction is None

    def test_filters_by_capability_id(self):
        result = _transform_ums_response(
            UMS_RESPONSE_DIFFERENT_CAPABILITY["data"], "onboarding"
        )
        assert result.capability_id == "onboarding"
        assert result.instruction == "Onboarding instruction."
        assert len(result.mcp_servers) == 1
        assert result.mcp_servers[0].ord_id == "sap.mcp:apiResource:onboarding:v1"

    def test_filters_excludes_non_matching_capability(self):
        result = _transform_ums_response(
            UMS_RESPONSE_DIFFERENT_CAPABILITY["data"], "default"
        )
        assert result.capability_id == "default"
        assert result.instruction == "Default instruction."
        assert len(result.mcp_servers) == 1
        assert result.mcp_servers[0].ord_id == "sap.mcp:apiResource:general:v1"

    def test_nonexistent_capability_id(self):
        result = _transform_ums_response(UMS_RESPONSE_SINGLE["data"], "nonexistent")
        assert result.capability_id == "nonexistent"
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.hooks == []
        # Extension names are still populated (from node titles)
        assert result.extension_names == ["ServiceNow Extension"]

    def test_source_mapping_populated(self):
        result = _transform_ums_response(UMS_RESPONSE_SINGLE["data"], "default")
        assert result.source is not None
        assert "create_ticket" in result.source.tools
        assert (
            result.source.tools["create_ticket"].extension_name
            == "ServiceNow Extension"
        )
        assert result.source.tools["create_ticket"].extension_id == "ext-instance-1"
        assert result.source.tools["create_ticket"].extension_version == "2.1.0"
        assert "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11" in result.source.hooks

    def test_hooks_with_unknown_type_skipped(self):
        data = {
            "EXTHUB__ExtCapImplementationInstances": {
                "edges": [
                    {
                        "node": {
                            "id": "ext-1",
                            "title": "Test",
                            "capabilityImplementations": [
                                {
                                    "capabilityId": "default",
                                    "hooks": [
                                        {
                                            "hookId": "valid_hook",
                                            "type": "BEFORE",
                                            "name": "Valid",
                                            "onFailure": "CONTINUE",
                                            "timeout": 30,
                                            "deploymentType": "N8N",
                                            "canShortCircuit": False,
                                            "n8nWorkflowConfig": {
                                                "workflowId": "wf-valid",
                                                "method": "POST",
                                            },
                                        },
                                        {
                                            "hookId": "invalid_hook",
                                            "type": "UNKNOWN",
                                            "name": "Invalid",
                                        },
                                    ],
                                    "tools": {"additions": []},
                                }
                            ],
                        }
                    }
                ]
            }
        }
        result = _transform_ums_response(data, "default")
        assert len(result.hooks) == 1
        assert result.hooks[0].hook_id == "valid_hook"

    def test_node_without_title(self):
        data = {
            "EXTHUB__ExtCapImplementationInstances": {
                "edges": [
                    {
                        "node": {
                            "id": "ext-1",
                            "capabilityImplementations": [
                                {
                                    "capabilityId": "default",
                                    "instruction": {"text": "hello"},
                                    "tools": {"additions": []},
                                    "hooks": [],
                                }
                            ],
                        }
                    }
                ]
            }
        }
        result = _transform_ums_response(data, "default")
        # Empty titles are not added to extension_names
        assert result.extension_names == []
        assert result.instruction == "hello"

    def test_hooks_null_in_response(self):
        """GraphQL may return hooks: null instead of an empty list."""
        data = {
            "EXTHUB__ExtCapImplementationInstances": {
                "edges": [
                    {
                        "node": {
                            "id": "ext-1",
                            "title": "Null Hooks Extension",
                            "capabilityImplementations": [
                                {
                                    "capabilityId": "default",
                                    "instruction": {"text": "Do stuff."},
                                    "tools": {
                                        "additions": [
                                            {
                                                "type": "MCP",
                                                "mcpConfig": {
                                                    "globalTenantId": "tenant-test-1",
                                                    "ordId": "sap.mcp:apiResource:test:v1",
                                                    "toolNames": ["my_tool"],
                                                },
                                            }
                                        ]
                                    },
                                    "hooks": None,
                                }
                            ],
                        }
                    }
                ]
            }
        }
        result = _transform_ums_response(data, "default")
        assert result.hooks == []
        assert len(result.mcp_servers) == 1
        assert result.instruction == "Do stuff."

    def test_tools_key_missing(self):
        """capabilityImplementations with no 'tools' key."""
        data = {
            "EXTHUB__ExtCapImplementationInstances": {
                "edges": [
                    {
                        "node": {
                            "id": "ext-1",
                            "title": "No tools",
                            "capabilityImplementations": [
                                {
                                    "capabilityId": "default",
                                    "hooks": [],
                                }
                            ],
                        }
                    }
                ]
            }
        }
        result = _transform_ums_response(data, "default")
        assert result.mcp_servers == []

