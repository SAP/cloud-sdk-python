"""Tests for LocalTransport and local mode integration via create_client."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sap_cloud_sdk.extensibility import create_client
from sap_cloud_sdk.extensibility._local_transport import (
    CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV,
    LocalTransport,
)
from sap_cloud_sdk.extensibility._models import (
    ExtensionCapabilityImplementation,
    Hook,
    HookType,
    DeploymentType,
    ExecutionMode,
    N8nWorkflowConfig,
    OnFailure,
)
from http import HTTPMethod
from sap_cloud_sdk.extensibility.client import ExtensibilityClient
from sap_cloud_sdk.extensibility.exceptions import TransportError


# Sample data matching the backend response schema
SAMPLE_RESPONSE = {
    "capabilityId": "default",
    "extensionNames": ["my-local-extension"],
    "instruction": "Use these tools for local testing.",
    "mcpServers": [
        {
            "ordId": "sap.mcp:apiResource:myService:v1",
            "url": "http://localhost:8080/mcp",
            "toolPrefix": "sap_mcp_myservice_v1_",
            "toolNames": ["my_tool"],
        },
    ],
}

SAMPLE_EMPTY_RESPONSE = {
    "capabilityId": "default",
    "instruction": None,
    "mcpServers": [],
}

SAMPLE_MULTI_SERVER_RESPONSE = {
    "capabilityId": "onboarding",
    "extensionNames": ["multi-server-ext"],
    "instruction": {"text": "Handle onboarding with these tools."},
    "mcpServers": [
        {
            "ordId": "sap.mcp:apiResource:serviceNow:v1",
            "url": "http://localhost:9001/mcp",
            "toolPrefix": "sap_mcp_servicenow_v1_",
            "toolNames": ["create_ticket"],
        },
        {
            "ordId": "sap.mcp:apiResource:jira:v1",
            "url": "http://localhost:9002/mcp",
            "toolPrefix": "sap_mcp_jira_v1_",
            "toolNames": None,
        },
    ],
}

SAMPLE_RESPONSE_WITH_HOOKS = {
    "capabilityId": "default",
    "extensionNames": ["my-local-extension"],
    "instruction": "Use these tools for local testing.",
    "mcpServers": [],
    "hooks": [
        {
            "hookId": "before_tool_execution",
            "id": "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
            "name": "Before Tool Execution Hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-before-001", "method": "POST"},
            "timeout": 30,
            "executionMode": "SYNC",
            "onFailure": "CONTINUE",
            "order": 1,
            "canShortCircuit": True,
        }
    ],
}

SAMPLE_RESPONSE_WITH_INSTRUCTION_MCP_HOOKS = {
    "capabilityId": "default",
    "extensionNames": ["my-local-extension"],
    "instruction": "Use these tools for local testing.",
    "mcpServers": [
        {
            "ordId": "sap.mcp:apiResource:service1:v1",
            "url": "http://localhost:8080/mcp",
            "toolPrefix": "sap_mcp_service1_v1_",
            "toolNames": ["tool1", "tool2"],
        },
    ],
    "hooks": [
        {
            "hookId": "pre_execution",
            "id": "6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22",
            "name": "Pre Execution Hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-pre-001", "method": "POST"},
            "timeout": 20,
            "executionMode": "SYNC",
            "onFailure": "CONTINUE",
            "order": 0,
            "canShortCircuit": False,
        }
    ],
}

SAMPLE_RESPONSE_WITH_MULTIPLE_HOOKS = {
    "capabilityId": "advanced",
    "extensionNames": ["multi-hook-extension"],
    "instruction": "Extension with multiple hooks for testing.",
    "mcpServers": [
        {
            "ordId": "sap.mcp:apiResource:testService:v1",
            "url": "http://localhost:8080/mcp",
            "toolPrefix": "sap_mcp_testservice_v1_",
            "toolNames": ["test_tool"],
        },
    ],
    "hooks": [
        {
            "hookId": "before_tool_execution",
            "id": "11111111-1111-4111-8111-111111111111",
            "name": "Before Tool Execution Hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-before-001", "method": "POST"},
            "timeout": 30,
            "executionMode": "SYNC",
            "onFailure": "BLOCK",
            "order": 1,
            "canShortCircuit": True,
        },
        {
            "hookId": "after_tool_execution",
            "id": "22222222-2222-4222-8222-222222222222",
            "name": "After Tool Execution Hook",
            "hookType": "AFTER",
            "deploymentType": "SERVERLESS",
            "n8nWorkflowConfig": {"workflowId": "wf-after-001", "method": "POST"},
            "timeout": 60,
            "executionMode": "ASYNC",
            "onFailure": "CONTINUE",
            "order": 2,
            "canShortCircuit": False,
        },
        {
            "hookId": "validation_hook",
            "id": "33333333-3333-4333-8333-333333333333",
            "name": "Validation Hook",
            "hookType": "BEFORE",
            "deploymentType": "N8N",
            "n8nWorkflowConfig": {"workflowId": "wf-validate-001", "method": "POST"},
            "timeout": 15,
            "executionMode": "SYNC",
            "onFailure": "BLOCK",
            "order": 0,
            "canShortCircuit": True,
        },
    ],
}

HOOK_RESPONSE_SAMPLE = {
    "agent_pre_hook": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Extend agent"}],
        "messageId": "msg-response-pre-hook",
    },
    "hook_with_no_response": None,
    "hook_with_non_dict_response": "not a dict",
    "hook_with_empty_response": {},
    "hook_with_stop_execution": {
        "role": "user",
        "parts": [],
        "messageId": "msg-stop-execution",
        "metadata": {
            "stop_execution": True,
            "stop_execution_reason": "Hook requested to stop execution",
        },
    },
}


def _make_hook(
    hook_id: str = "before_tool_execution",
    hook_uuid: str = "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
) -> Hook:
    """Create a minimal Hook instance for testing."""
    return Hook(
        hook_id=hook_id,
        id=hook_uuid,
        n8n_workflow_config=N8nWorkflowConfig(
            workflow_id=f"wf-{hook_id}",
            method=HTTPMethod.POST,
        ),
        name=f"Test Hook {hook_id}",
        type=HookType.BEFORE,
        deployment_type=DeploymentType.N8N,
        timeout=30,
        execution_mode=ExecutionMode.SYNC,
        on_failure=OnFailure.CONTINUE,
        order=0,
        can_short_circuit=False,
    )


def _write_json(path: Path, data: dict) -> None:
    """Helper to write a dict as JSON to a file."""
    path.write_text(json.dumps(data), encoding="utf-8")


class TestLocalTransport:
    """Tests for LocalTransport reading from a JSON file."""

    def test_reads_full_response(self, tmp_path: Path):
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.capability_id == "default"
        assert result.extension_names == ["my-local-extension"]
        assert result.instruction == "Use these tools for local testing."
        assert len(result.mcp_servers) == 1
        assert result.mcp_servers[0].ord_id == "sap.mcp:apiResource:myService:v1"
        assert result.mcp_servers[0].tool_names == ["my_tool"]

    def test_reads_empty_response(self, tmp_path: Path):
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_EMPTY_RESPONSE)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert result.capability_id == "default"
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.extension_names == []

    def test_reads_multi_server_with_nested_instruction(self, tmp_path: Path):
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_MULTI_SERVER_RESPONSE)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert result.capability_id == "onboarding"
        assert result.extension_names == ["multi-server-ext"]
        assert result.instruction == "Handle onboarding with these tools."
        assert len(result.mcp_servers) == 2
        assert result.mcp_servers[0].tool_names == ["create_ticket"]
        assert result.mcp_servers[1].tool_names is None

    def test_file_not_found_raises_transport_error(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist" / "extensions.json"
        transport = LocalTransport(str(missing))
        with pytest.raises(TransportError, match="not found"):
            transport.get_extension_capability_implementation()

    def test_invalid_json_raises_transport_error(self, tmp_path: Path):
        file = tmp_path / "bad.json"
        file.write_text("not valid json {{{", encoding="utf-8")

        transport = LocalTransport(str(file))
        with pytest.raises(TransportError, match="Failed to parse"):
            transport.get_extension_capability_implementation()

    def test_empty_file_raises_transport_error(self, tmp_path: Path):
        file = tmp_path / "empty.json"
        file.write_text("", encoding="utf-8")

        transport = LocalTransport(str(file))
        with pytest.raises(TransportError, match="Failed to parse"):
            transport.get_extension_capability_implementation()

    def test_reads_response_with_hooks(self, tmp_path: Path):
        """Verify hooks are parsed from the response."""
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE_WITH_HOOKS)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.capability_id == "default"
        assert result.extension_names == ["my-local-extension"]
        assert len(result.hooks) == 1

        hook = result.hooks[0]
        assert hook.hook_id == "before_tool_execution"
        assert hook.id == "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11"
        assert hook.n8n_workflow_config.workflow_id == "wf-before-001"
        assert hook.name == "Before Tool Execution Hook"
        assert hook.type == HookType.BEFORE
        assert hook.deployment_type == DeploymentType.N8N
        assert hook.timeout == 30
        assert hook.execution_mode == ExecutionMode.SYNC
        assert hook.on_failure == OnFailure.CONTINUE
        assert hook.order == 1
        assert hook.can_short_circuit is True

    def test_reads_response_with_multiple_hooks(self, tmp_path: Path):
        """Verify multiple hooks with different types and configurations are parsed."""
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE_WITH_MULTIPLE_HOOKS)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert result.capability_id == "advanced"
        assert result.extension_names == ["multi-hook-extension"]
        assert len(result.hooks) == 3
        assert len(result.mcp_servers) == 1

        # Verify first hook (BEFORE, N8N, SYNC, BLOCK)
        hook1 = result.hooks[0]
        assert hook1.hook_id == "before_tool_execution"
        assert hook1.type == HookType.BEFORE
        assert hook1.deployment_type == DeploymentType.N8N
        assert hook1.execution_mode == ExecutionMode.SYNC
        assert hook1.on_failure == OnFailure.BLOCK
        assert hook1.order == 1
        assert hook1.can_short_circuit is True

        # Verify second hook (AFTER, SERVERLESS, ASYNC, CONTINUE)
        hook2 = result.hooks[1]
        assert hook2.hook_id == "after_tool_execution"
        assert hook2.type == HookType.AFTER
        assert hook2.deployment_type == DeploymentType.SERVERLESS
        assert hook2.execution_mode == ExecutionMode.ASYNC
        assert hook2.on_failure == OnFailure.CONTINUE
        assert hook2.timeout == 60
        assert hook2.order == 2
        assert hook2.can_short_circuit is False

        # Verify third hook (validation)
        hook3 = result.hooks[2]
        assert hook3.hook_id == "validation_hook"
        assert hook3.type == HookType.BEFORE
        assert hook3.timeout == 15
        assert hook3.order == 0

    def test_reads_response_with_empty_hooks(self, tmp_path: Path):
        """Verify response with empty hooks array returns empty list."""
        data = {**SAMPLE_RESPONSE, "hooks": []}
        file = tmp_path / "extensions.json"
        _write_json(file, data)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert result.hooks == []
        assert len(result.mcp_servers) == 1  # Other data should still be parsed

    def test_reads_response_without_hooks_field(self, tmp_path: Path):
        """Verify response without hooks field defaults to empty list."""
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE)  # No hooks field

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert result.hooks == []
        assert len(result.mcp_servers) == 1

    def test_reads_hooks_with_mcp_servers_and_instruction(self, tmp_path: Path):
        """Verify hooks are parsed alongside MCP servers and instructions."""
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE_WITH_INSTRUCTION_MCP_HOOKS)

        transport = LocalTransport(str(file))
        result = transport.get_extension_capability_implementation()

        assert result.capability_id == "default"
        assert result.extension_names == ["my-local-extension"]
        assert result.instruction == "Use these tools for local testing."
        assert len(result.mcp_servers) == 1
        assert result.mcp_servers[0].tool_names == ["tool1", "tool2"]
        assert len(result.hooks) == 1
        assert result.hooks[0].hook_id == "pre_execution"
        assert result.hooks[0].timeout == 20


class TestCreateClientLocalMode:
    """Tests for create_client() with CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE env var."""

    def test_env_var_activates_local_mode(self, tmp_path: Path):
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE_WITH_INSTRUCTION_MCP_HOOKS)

        with patch.dict(
            os.environ, {CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV: str(file)}
        ):
            client = create_client("sap.ai:agent:test:v1")

        assert isinstance(client, ExtensibilityClient)
        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.extension_names == ["my-local-extension"]
        assert len(result.mcp_servers) == 1
        assert len(result.hooks) == 1

    def test_env_var_takes_precedence_over_config(self, tmp_path: Path):
        """When env var is set, config is ignored (no destination resolution)."""
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE)

        with patch.dict(
            os.environ, {CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV: str(file)}
        ):
            # This would normally fail because destination service isn't available,
            # but local mode bypasses it entirely.
            from sap_cloud_sdk.extensibility.config import ExtensibilityConfig

            config = ExtensibilityConfig(
                destination_name="NONEXISTENT",
                destination_instance="bad",
            )
            client = create_client("sap.ai:agent:test:v1", config=config)

        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.extension_names == ["my-local-extension"]

    def test_no_env_var_uses_ums_transport(self):
        """Without the env var, create_client tries UmsTransport; on failure it returns a no-op client."""
        with patch.dict(os.environ, {}, clear=False):
            # Ensure the env var is not set
            os.environ.pop(CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV, None)
            # UmsTransport creation will fail without destination service,
            # but create_client gracefully degrades to a no-op client.
            client = create_client("sap.ai:agent:test:v1")

        # The no-op client returns empty results instead of raising.
        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.hooks == []

    def test_missing_file_via_env_var_graceful_degradation(self, tmp_path: Path):
        """Client still works via graceful degradation when the file doesn't exist."""
        bad_path = str(tmp_path / "does_not_exist.json")

        with patch.dict(os.environ, {CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV: bad_path}):
            client = create_client("sap.ai:agent:test:v1")

        # The client is created successfully (LocalTransport doesn't read at init time).
        # The read happens at get_extension_capability_implementation() and
        # the client's graceful degradation catches the TransportError.
        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.hooks == []

    def test_local_mode_logs_warning(self, tmp_path: Path, caplog):
        file = tmp_path / "extensions.json"
        _write_json(file, SAMPLE_RESPONSE)

        with patch.dict(
            os.environ, {CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV: str(file)}
        ):
            with caplog.at_level("WARNING", logger="sap_cloud_sdk.extensibility"):
                create_client("sap.ai:agent:test:v1")

        assert "local mock mode active" in caplog.text.lower()


class TestCreateClientMockFileMode:
    """Tests for create_client() with file-presence detection at mocks/extensibility.json."""

    def test_mock_file_activates_local_mode(self, tmp_path: Path):
        """When mocks/extensibility.json exists, local mode is activated."""
        mock_file = tmp_path / "mocks" / "extensibility.json"
        mock_file.parent.mkdir(parents=True)
        _write_json(mock_file, SAMPLE_RESPONSE)

        with (
            patch.dict(os.environ, {}, clear=False),
            patch(
                "os.getcwd",
                return_value=str(tmp_path),
            ),
        ):
            os.environ.pop(CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV, None)
            client = create_client("sap.ai:agent:test:v1")

        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.extension_names == ["my-local-extension"]
        assert len(result.mcp_servers) == 1

    def test_env_var_takes_precedence_over_mock_file(self, tmp_path: Path):
        """Env var wins when both env var and mock file are present."""
        # Mock file with one extension name
        mock_file = tmp_path / "mocks" / "extensibility.json"
        mock_file.parent.mkdir(parents=True)
        _write_json(
            mock_file,
            {**SAMPLE_RESPONSE, "extensionNames": ["from-mock-file"]},
        )

        # Env var file with a different extension name
        env_file = tmp_path / "env_extensions.json"
        _write_json(
            env_file,
            {**SAMPLE_RESPONSE, "extensionNames": ["from-env-var"]},
        )

        with (
            patch.dict(
                os.environ,
                {CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV: str(env_file)},
            ),
            patch(
                "os.getcwd",
                return_value=str(tmp_path),
            ),
        ):
            client = create_client("sap.ai:agent:test:v1")

        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.extension_names == ["from-env-var"]

    def test_no_mock_file_no_env_var_falls_through(self, tmp_path: Path):
        """Without env var or mock file, falls through to cloud mode (then no-op)."""

        with (
            patch.dict(os.environ, {}, clear=False),
            patch(
                "os.getcwd",
                return_value=str(tmp_path),
            ),
        ):
            os.environ.pop(CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV, None)
            client = create_client("sap.ai:agent:test:v1")

        # Falls through to cloud mode, which fails without credentials,
        # so graceful degradation returns no-op client.
        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.mcp_servers == []
        assert result.instruction is None

    def test_mock_file_logs_warning(self, tmp_path: Path, caplog):
        """File-presence detection logs at WARNING level."""
        mock_file = tmp_path / "mocks" / "extensibility.json"
        mock_file.parent.mkdir(parents=True)
        _write_json(mock_file, SAMPLE_RESPONSE)

        with (
            patch.dict(os.environ, {}, clear=False),
            patch(
                "os.getcwd",
                return_value=str(tmp_path),
            ),
        ):
            os.environ.pop(CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV, None)
            with caplog.at_level("WARNING", logger="sap_cloud_sdk.extensibility"):
                create_client("sap.ai:agent:test:v1")

        assert "local mock mode active" in caplog.text.lower()
