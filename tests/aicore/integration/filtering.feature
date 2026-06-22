Feature: Content filtering integration with SAP AI Core Orchestration v2
  As an SDK user
  I want Azure Content Safety and Prompt Shield to apply automatically
  So that harmful prompts and jailbreak attempts are blocked at the orchestration layer

  Background:
    Given AI Core credentials are configured
    And the test model is configured

  Scenario: Filtering OFF — benign prompt returns a completion
    Given filtering is disabled
    When I send the benign prompt
    Then the response should contain a non-empty completion
    And no ContentFilteredError is raised

  Scenario: Filtering ON with defaults — benign prompt returns a completion
    Given filtering is enabled with default thresholds
    When I send the benign prompt
    Then the response should contain a non-empty completion
    And no ContentFilteredError is raised

  Scenario: Input filter blocks a harmful prompt at STRICT threshold
    Given filtering is enabled with all categories set to STRICT
    When I send the self-harm test prompt
    Then a ContentFilteredError is raised
    And the error direction is "input"
    And the error details mention "self_harm"
    And the error has a non-empty request_id

  Scenario: Prompt Shield blocks a jailbreak attempt
    Given filtering is enabled with prompt_shield on
    When I send the jailbreak test prompt
    Then a ContentFilteredError is raised
    And the error direction is "input"
    And the error details mention prompt_shield or jailbreak
    And the error has a non-empty request_id
