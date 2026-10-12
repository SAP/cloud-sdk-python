"""BDD step definitions for Agent Gateway connected-systems integration tests.

Run against a live BTP tenant (same env vars as agw_auth.feature):

    CLOUD_SDK_CFG_AGW_DEFAULT_TENANT_SUBDOMAIN=<tenant-subdomain> \\
    CLOUD_SDK_CFG_AGW_DEFAULT_LANDSCAPE=<landscape> \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE=... \\
    pytest tests/agentgateway/integration/test_connected_systems_bdd.py -v
"""

import os
from typing import Optional
from unittest.mock import patch

import pytest
from pytest_bdd import scenarios, given, when, then

from sap_cloud_sdk.agentgateway import (
    AgentGatewayClient,
    AgentGatewaySDKError,
    ConnectedSystem,
    MCPTool,
    MCPToolFilter,
    create_client,
)

scenarios("connected_systems.feature")


# ==================== CONTEXT ====================


class ConnectedSystemsContext:
    """State shared across steps within a scenario."""

    def __init__(self):
        self.integrations: Optional[list[ConnectedSystem]] = None
        self.tools: Optional[list[MCPTool]] = None
        self.operation_error: Optional[Exception] = None
        self.customer_client: Optional[AgentGatewayClient] = None


@pytest.fixture
def context():
    return ConnectedSystemsContext()


# ==================== GIVEN ====================


@given("the Agent Gateway client is available")
def agent_gateway_client_available(agw_client: AgentGatewayClient):
    assert agw_client is not None


@given("a customer agent client is configured")
def customer_agent_client(context: ConnectedSystemsContext):
    """Create a client that mimics the customer agent flow by faking credential detection."""
    context.customer_client = create_client(tenant_subdomain="irrelevant")


# ==================== WHEN ====================


@when("I call list_active_integrations")
def call_list_active_integrations(context: ConnectedSystemsContext, agw_client: AgentGatewayClient):
    context.integrations = agw_client.list_active_integrations()


@when("at least one connected system is present")
def at_least_one_connected_system(context: ConnectedSystemsContext):
    if not context.integrations:
        pytest.skip("No connected systems found for this tenant — skipping GTID filter scenario")


@when("I call list_mcp_tools filtered by the first connected system gtid")
def call_list_mcp_tools_filtered_by_gtid(
    context: ConnectedSystemsContext, agw_client: AgentGatewayClient
):
    import asyncio

    assert context.integrations
    gtid = context.integrations[0].get("global_tenant_id")
    if not gtid:
        pytest.skip("First connected system has no global_tenant_id — skipping")

    loop = asyncio.new_event_loop()
    try:
        context.tools = loop.run_until_complete(
            agw_client.list_mcp_tools(filter=MCPToolFilter(gtids=[gtid]))
        )
    finally:
        loop.close()


@when("I call list_active_integrations with the customer agent client")
def call_list_active_integrations_customer(context: ConnectedSystemsContext):
    assert context.customer_client is not None
    try:
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/fake/credentials.json",
        ):
            context.customer_client.list_active_integrations()
    except AgentGatewaySDKError as e:
        context.operation_error = e


# ==================== THEN ====================


@then("the result should be a list of ConnectedSystem")
def result_is_list_of_connected_system(context: ConnectedSystemsContext):
    assert isinstance(context.integrations, list), (
        f"Expected list, got {type(context.integrations)}"
    )
    for item in context.integrations:
        assert isinstance(item, dict), f"Expected dict (TypedDict), got {type(item)}"
        assert "global_tenant_id" in item
        assert "system_type" in item
        assert "integration_dependency" in item


@then("each connected system should have a non-empty global_tenant_id")
def each_system_has_gtid(context: ConnectedSystemsContext):
    assert context.integrations is not None
    for system in context.integrations:
        assert system.get("global_tenant_id"), (
            f"Connected system missing global_tenant_id: {system}"
        )


@then("each connected system should have a non-null integration_dependency or system_type")
def each_system_has_at_least_one_label(context: ConnectedSystemsContext):
    assert context.integrations is not None
    for system in context.integrations:
        has_data = system.get("integration_dependency") or system.get("system_type")
        assert has_data, (
            f"Connected system has neither integration_dependency nor system_type: {system}"
        )


@then("fragments with missing labels should appear with None values")
def fragments_with_missing_labels_have_none(context: ConnectedSystemsContext):
    """Verify the SDK does not drop fragments that are missing optional labels."""
    assert context.integrations is not None
    # Every returned item must be a dict with the three expected keys, even if values are None.
    for item in context.integrations:
        assert "global_tenant_id" in item, f"Key 'global_tenant_id' missing from {item}"
        assert "system_type" in item, f"Key 'system_type' missing from {item}"
        assert "integration_dependency" in item, f"Key 'integration_dependency' missing from {item}"


@then("the result should be a list of MCPTool")
def result_is_list_of_mcp_tool(context: ConnectedSystemsContext):
    assert isinstance(context.tools, list), f"Expected list, got {type(context.tools)}"
    for tool in context.tools:
        assert isinstance(tool, MCPTool), f"Expected MCPTool, got {type(tool)}"


@then("the operation should fail with AgentGatewaySDKError")
def operation_fails_with_sdk_error(context: ConnectedSystemsContext):
    assert isinstance(context.operation_error, AgentGatewaySDKError), (
        f"Expected AgentGatewaySDKError, got: {context.operation_error}"
    )


@then('the error message should mention "not supported for customer agents"')
def error_mentions_customer_agents(context: ConnectedSystemsContext):
    assert "not supported for customer agents" in str(context.operation_error), (
        f"Unexpected error message: {context.operation_error}"
    )
