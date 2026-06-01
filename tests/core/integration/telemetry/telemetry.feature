Feature: SDK telemetry instrumentation

  Background:
    Given auto_instrument is initialized

  Scenario: invoke_agent_span emits a span with required GenAI attributes
    When I invoke an agent with provider "test" and name "bot" and conversation_id "c1"
    Then a span named "invoke_agent bot" is recorded
    And the span has attribute "gen_ai.operation.name" equal to "invoke_agent"
    And the span has attribute "gen_ai.provider.name" equal to "test"
    And the span has attribute "gen_ai.agent.name" equal to "bot"
    And the span has attribute "gen_ai.conversation.id" equal to "c1"

  Scenario: invoke_agent_span without optional fields
    When I invoke an agent with provider "test" only
    Then a span named "invoke_agent" is recorded
    And the span has attribute "gen_ai.operation.name" equal to "invoke_agent"
    And the span has attribute "gen_ai.provider.name" equal to "test"
    And the span does not have attribute "gen_ai.agent.name"

  Scenario: invoke_agent_span records errors
    When I invoke an agent that raises an exception
    Then the span status is ERROR
    And the span has an exception event

  Scenario: spans carry SDK resource attributes
    When I invoke an agent with provider "test" and name "sdk-resource-test"
    Then a span named "invoke_agent sdk-resource-test" is recorded
    And the span resource has attribute "sap.cloud_sdk.name" equal to "SAP Cloud SDK for Python"
    And the span resource has attribute "sap.cloud_sdk.language" equal to "python"
    And the span resource has attribute "sap.cloud_sdk.version" set
    And the span resource has attribute "service.name" set

  Scenario: spans carry environment resource attributes
    When I invoke an agent with provider "test" and name "env-resource-test"
    Then a span named "invoke_agent env-resource-test" is recorded
    And the span resource has attribute "service.name" set
    And the span resource has attribute "cloud.region" set
    And the span resource has attribute "deployment.environment.name" set

  Scenario: propagate=True flows attributes to child spans via ContextVar
    When I invoke an agent with propagate=True and attribute "custom.key" equal to "val"
    Then the child span has attribute "custom.key" equal to "val"

  Scenario: propagate=False does not leak attributes to child spans
    When I invoke an agent with propagate=False and attribute "custom.key" equal to "val"
    Then the child span does not have attribute "custom.key"

  Scenario: baggage attributes appear on spans
    Given baggage key "sap.extension.capabilityId" is set to "cap-1"
    When I invoke an agent with provider "test" and name "baggage-test"
    Then a span named "invoke_agent baggage-test" is recorded
    And the span has attribute "sap.extension.capabilityId" equal to "cap-1"

  @aicore
  Scenario: LangGraph agent run produces an invoke_agent span with LangChain child spans
    Given AI Core is configured via set_aicore_config
    When I run a LangGraph agent with provider "sap-aicore" and name "test-agent"
    Then a span named "invoke_agent test-agent" is recorded
    And at least one descendant span with attribute "gen_ai.operation.name" equal to "chat" is recorded
    And at least one descendant span has attribute "gen_ai.request.model" set
    And at least one descendant span has attribute "gen_ai.usage.input_tokens" set
    And at least one descendant span has attribute "gen_ai.usage.output_tokens" set
    And no descendant span has an attribute starting with "llm.usage."
    And no descendant span has attribute "traceloop.association.properties.ls_model_name"
    And no descendant span has attribute "traceloop.association.properties.ls_provider"
