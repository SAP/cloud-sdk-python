"""BDD step definitions for Agent Gateway auth integration tests.

Run against a live BTP tenant:

    CLOUD_SDK_CFG_AGW_DEFAULT_TENANT_SUBDOMAIN=<tenant-subdomain> \\
    CLOUD_SDK_CFG_AGW_DEFAULT_LANDSCAPE=<landscape> \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE=... \\
    AGW_USER_TOKEN=<user-jwt> \\
    pytest tests/agentgateway/integration/ -v
"""

import asyncio
import os
from typing import Optional

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.agentgateway import AgentGatewayClient, AuthResult, AgentGatewaySDKError
from sap_cloud_sdk.agentgateway._models import MCPTool

scenarios("agw_auth.feature")


# ==================== HELPERS ====================


def run(coro):
    """Run a coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ==================== CONTEXT ====================


class ScenarioContext:
    """Context to store test state between steps."""

    def __init__(self):
        self.system_auth_result: Optional[AuthResult] = None
        self.user_auth_result: Optional[AuthResult] = None
        self.last_result: Optional[AuthResult] = None
        self.operation_error: Optional[Exception] = None
        self.user_token: Optional[str] = None
        self.tools: Optional[list[MCPTool]] = None
        self.tool_result: Optional[str] = None


@pytest.fixture
def context():
    """Provide a fresh context for each scenario."""
    return ScenarioContext()


# ==================== GIVEN ====================


@given("the Agent Gateway client is available")
def agent_gateway_client_available(agw_client: AgentGatewayClient):
    """Verify that the Agent Gateway client is available."""
    assert agw_client is not None


@given("I have a valid user token")
def have_valid_user_token(context: ScenarioContext):
    """Load user token from environment variable."""
    token = os.environ.get("AGW_USER_TOKEN", "")
    if not token:
        pytest.skip("AGW_USER_TOKEN is not set — skipping user auth scenario")
    context.user_token = token


# ==================== WHEN ====================


@when("I call get_system_auth")
def call_get_system_auth(context: ScenarioContext, agw_client: AgentGatewayClient):
    """Call get_system_auth and store the result."""
    context.system_auth_result = run(agw_client.get_system_auth())
    context.last_result = context.system_auth_result


@when("I call get_user_auth with the user token")
def call_get_user_auth(context: ScenarioContext, agw_client: AgentGatewayClient):
    """Call get_user_auth with the user token and store the result."""
    context.user_auth_result = run(
        agw_client.get_user_auth(user_token=context.user_token)
    )
    context.last_result = context.user_auth_result


@when("I call get_user_auth with a callable returning the user token")
def call_get_user_auth_callable(context: ScenarioContext, agw_client: AgentGatewayClient):
    """Call get_user_auth with a callable and store the result."""
    token = context.user_token
    assert token is not None
    context.last_result = run(
        agw_client.get_user_auth(user_token=lambda: token)
    )


@when("I call get_user_auth with an empty user token")
def call_get_user_auth_empty_token(context: ScenarioContext, agw_client: AgentGatewayClient):
    """Call get_user_auth with an empty token and capture the error."""
    try:
        run(agw_client.get_user_auth(user_token=""))
    except AgentGatewaySDKError as e:
        context.operation_error = e


@when("I call list_mcp_tools")
def call_list_mcp_tools(context: ScenarioContext, agw_client: AgentGatewayClient):
    """Call list_mcp_tools and store the result."""
    context.tools = run(agw_client.list_mcp_tools())


@when(parsers.parse('I call call_mcp_tool with "{tool_name}" and the user token'))
def call_call_mcp_tool(
    context: ScenarioContext, agw_client: AgentGatewayClient, tool_name: str
):
    """Find tool by name from list_mcp_tools result and call it."""
    assert context.tools is not None, "call list_mcp_tools before calling a tool"
    tool = next((t for t in context.tools if t.name == tool_name), None)
    if tool is None:
        pytest.fail(f"Tool '{tool_name}' not found in list_mcp_tools result")
    context.tool_result = run(
        agw_client.call_mcp_tool(tool, user_token=context.user_token)
    )


# ==================== THEN ====================


@then("the result should be an AuthResult")
def result_is_auth_result(context: ScenarioContext):
    """Verify the result is an AuthResult instance."""
    assert isinstance(context.last_result, AuthResult)


@then("the access_token should be a non-empty string")
def access_token_non_empty(context: ScenarioContext):
    """Verify access_token is a non-empty string."""
    assert context.last_result is not None
    assert isinstance(context.last_result.access_token, str)
    assert context.last_result.access_token.strip()


@then("the gateway_url should be a non-empty string")
def gateway_url_non_empty(context: ScenarioContext):
    """Verify gateway_url is a non-empty string."""
    assert context.last_result is not None
    assert isinstance(context.last_result.gateway_url, str)
    assert context.last_result.gateway_url.strip()


@then("the gateway_url should have no trailing slash")
def gateway_url_no_trailing_slash(context: ScenarioContext):
    """Verify gateway_url does not end with a slash."""
    assert context.last_result is not None
    assert not context.last_result.gateway_url.endswith("/")


@then(parsers.parse('the access_token should not start with "{prefix}"'))
def access_token_not_starts_with(context: ScenarioContext, prefix: str):
    """Verify access_token does not start with the given prefix."""
    assert context.last_result is not None
    assert not context.last_result.access_token.startswith(prefix), (
        f"Expected access_token NOT to start with '{prefix}', "
        f"got: {context.last_result.access_token[:40]}..."
    )


@then("both gateway URLs should match")
def gateway_urls_match(context: ScenarioContext):
    """Verify system auth and user auth return the same gateway URL."""
    assert context.system_auth_result is not None
    assert context.user_auth_result is not None
    assert context.system_auth_result.gateway_url == context.user_auth_result.gateway_url


@then("the operation should fail with AgentGatewaySDKError")
def operation_fails_with_sdk_error(context: ScenarioContext):
    """Verify the operation raised an AgentGatewaySDKError."""
    assert isinstance(context.operation_error, AgentGatewaySDKError), (
        f"Expected AgentGatewaySDKError, got: {context.operation_error}"
    )


@then(parsers.parse('the error message should mention "{expected}"'))
def error_message_mentions(context: ScenarioContext, expected: str):
    """Verify the error message contains the expected text."""
    assert expected in str(context.operation_error), (
        f"Expected '{expected}' in error: {context.operation_error}"
    )


@then("the result should be a list of MCPTool")
def result_is_list_of_mcp_tool(context: ScenarioContext):
    """Verify the result is a list of MCPTool instances."""
    assert isinstance(context.tools, list)
    for tool in context.tools:
        assert isinstance(tool, MCPTool), f"Expected MCPTool, got {type(tool)}"


@then("the list should be non-empty")
def list_is_non_empty(context: ScenarioContext):
    """Verify the tools list is not empty."""
    assert context.tools is not None
    assert len(context.tools) > 0, "Expected at least one MCP tool"


@then("each tool should have a non-empty name")
def each_tool_has_non_empty_name(context: ScenarioContext):
    """Verify every tool has a non-empty name."""
    assert context.tools is not None
    for tool in context.tools:
        assert isinstance(tool.name, str) and tool.name.strip(), (
            f"Tool has empty name: {tool}"
        )


@then("each tool should have a non-empty url")
def each_tool_has_non_empty_url(context: ScenarioContext):
    """Verify every tool has a non-empty url."""
    assert context.tools is not None
    for tool in context.tools:
        assert isinstance(tool.url, str) and tool.url.strip(), (
            f"Tool '{tool.name}' has empty url"
        )


@then("the tool result should be a non-empty string")
def tool_result_is_non_empty_string(context: ScenarioContext):
    """Verify the tool invocation returned a non-empty string."""
    assert context.tool_result is not None
    assert isinstance(context.tool_result, str)
    assert context.tool_result.strip(), "Expected a non-empty tool result"
