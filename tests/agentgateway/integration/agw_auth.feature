Feature: Agent Gateway Auth Integration
  As a developer using the SDK
  I want to fetch auth credentials from the Agent Gateway
  So that I can make authenticated requests to MCP servers

  Background:
    Given the Agent Gateway client is available

  Scenario: Get system auth returns a valid AuthResult
    When I call get_system_auth
    Then the result should be an AuthResult
    And the access_token should be a non-empty string
    And the gateway_url should be a non-empty string
    And the gateway_url should have no trailing slash
    And the access_token should not start with "Bearer "

  Scenario: Get user auth returns a valid AuthResult
    Given I have a valid user token
    When I call get_user_auth with the user token
    Then the result should be an AuthResult
    And the access_token should be a non-empty string
    And the gateway_url should be a non-empty string
    And the gateway_url should have no trailing slash
    And the access_token should not start with "Bearer "

  Scenario: Get user auth accepts a callable user token
    Given I have a valid user token
    When I call get_user_auth with a callable returning the user token
    Then the result should be an AuthResult
    And the access_token should be a non-empty string

  Scenario: System auth and user auth return the same gateway URL
    Given I have a valid user token
    When I call get_system_auth
    And I call get_user_auth with the user token
    Then both gateway URLs should match

  Scenario: Get user auth fails when user token is empty
    When I call get_user_auth with an empty user token
    Then the operation should fail with AgentGatewaySDKError
    And the error message should mention "user_token is required"

  Scenario: List MCP tools returns a non-empty list of tools
    When I call list_mcp_tools
    Then the result should be a list of MCPTool
    And the list should be non-empty
    And each tool should have a non-empty name
    And each tool should have a non-empty url

  Scenario: Call search_workflows tool returns a non-empty result
    Given I have a valid user token
    When I call list_mcp_tools
    And I call call_mcp_tool with "search_workflows" and the user token
    Then the tool result should be a non-empty string
