Feature: Model fallback with SAP AI Core Orchestration v2
  As an SDK user
  I want orchestration to transparently retry with a fallback model when the primary fails
  So that my application is resilient to transient errors and region-unsupported models

  Background:
    Given AI Core credentials are configured
    And primary and fallback test models are configured

  Scenario: Fallback OFF — primary call succeeds with no intermediate_failures
    Given fallback is disabled
    When I send a benign prompt to the fallback test model
    Then the response should contain a non-empty completion
    And the response has no intermediate_failures

  Scenario: Primary model unsupported — fallback model is used
    Given fallback is configured with the test fallback model
    When I send a benign prompt to the unsupported primary model
    Then the response should contain a non-empty completion
    And the response has a non-empty intermediate_failures list

  Scenario: Filtering composes with fallback — call succeeds, no filter rejection
    Given fallback is configured with the test fallback model
    And filtering is enabled with default thresholds
    When I send a benign prompt to the unsupported primary model
    Then the response should contain a non-empty completion
    And no ContentFilteredError is raised

  Scenario: Streaming with fallback — fallback fires when primary unsupported
    Given fallback is configured with the test fallback model
    When I send a benign streaming prompt to the unsupported primary model
    Then the streamed response should contain non-empty content
