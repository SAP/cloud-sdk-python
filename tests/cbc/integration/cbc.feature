Feature: CBC (Central Business Configuration) Integration

  Background:
    Given a configured CBC client and tenant context

  # ── Consumption Versions ─────────────────────────────────────────────────────

  Scenario: Fetch consumption versions returns at least one version
    When I call get_consumption_versions
    Then the result should contain at least one version

  Scenario: Latest consumption version is non-empty
    When I call get_consumption_versions
    Then the latest version should have a non-empty version string

  # ── Configuration ────────────────────────────────────────────────────────────

  Scenario: Fetch full configuration returns ConfigData
    When I call get_configuration
    Then the result should be a ConfigData with a non-empty consumption_version
    And the tenant_context should match the configured tenant

  Scenario: Full configuration contains at least one config object
    When I call get_configuration
    Then the result should contain at least one config object

  Scenario: Every entity within each config object has an entity_id and data
    When I call get_configuration
    Then every entity should have a non-empty entity_id
    And every entity data should be accessible as a list or object
