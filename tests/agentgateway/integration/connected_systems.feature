Feature: Agent Gateway Connected Systems Integration
  As a LoB agent developer using the SDK
  I want to discover which backend systems are connected for my tenant
  So that I can scope MCP tool discovery to specific systems

  Background:
    Given the Agent Gateway client is available

  Scenario: List connected systems returns a list
    When I call list_active_integrations
    Then the result should be a list of ConnectedSystem

  Scenario: Each connected system has required fields
    When I call list_active_integrations
    Then each connected system should have a non-empty global_tenant_id
    And each connected system should have a non-null integration_dependency or system_type

  Scenario: Connected systems with missing labels are still returned
    When I call list_active_integrations
    Then fragments with missing labels should appear with None values

  Scenario: List MCP tools filtered by GTID from connected system
    When I call list_active_integrations
    And at least one connected system is present
    When I call list_mcp_tools filtered by the first connected system gtid
    Then the result should be a list of MCPTool

  Scenario: Customer agent cannot call list_active_integrations
    Given a customer agent client is configured
    When I call list_active_integrations with the customer agent client
    Then the operation should fail with AgentGatewaySDKError
    And the error message should mention "not supported for customer agents"
