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

  Scenario: Fetch full configuration returns ConfigurationData
    When I call get_configuration
    Then the result should be a ConfigurationData with a non-empty consumption_version
    And the app_tenant_id should match the configured tenant

  Scenario: Full configuration contains at least one config object
    When I call get_configuration
    Then the result should contain at least one config object

  Scenario: Every entity within each config object has an entity_id and data
    When I call get_configuration
    Then every entity should have a non-empty entity_id
    And every entity data should be accessible as a list or object

  # ── Single entity fetch ──────────────────────────────────────────────────────

  Scenario: Fetch a single entity directly returns EntityData
    When I call get_entity_data for the first entity in the first config object
    Then the result should be EntityData accessible as a list or object

  # ── Feature status ───────────────────────────────────────────────────────────

  Scenario: Fetch feature statuses returns FeatureStatuses
    When I call get_feature_statuses
    Then the result should be FeatureStatuses
    And every feature should have a non-empty feature_id

  Scenario: Look up a single feature status by id
    When I call get_feature_statuses
    And I call get_feature_status for the first feature id
    Then the result should be a FeatureStatus for the requested feature id
