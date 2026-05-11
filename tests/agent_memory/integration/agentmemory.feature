Feature: Agent Memory Service Integration (v1 API)

  Background:
    Given a configured Agent Memory client

  # ── Memory CRUD ─────────────────────────────────────────────────────────────

  Scenario: Create a new memory
    When I create a memory with agent "test-agent" and invoker "test-user" and content "User prefers dark mode"
    Then the memory should have a non-empty id
    And the memory should have agent_id "test-agent"
    And the memory should have invoker_id "test-user"
    And the memory should have content "User prefers dark mode"

  Scenario: Get an existing memory
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "Test memory"
    When I get the memory by id
    Then the returned memory should match the created memory

  Scenario: Update memory content
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "Original content"
    When I update the memory content to "Updated content"
    Then the memory should have content "Updated content"

  Scenario: List memories with filter
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "Listed memory"
    When I list memories filtered by agent "test-agent"
    Then the result should contain at least one memory
    And the total count should be a positive number

  Scenario: Delete a memory
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "To be deleted"
    When I delete the memory
    Then the memory should no longer exist

  # ── Memory search ───────────────────────────────────────────────────────────

  Scenario: Search memories by semantic query
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "The user loves dark mode and dark themes"
    When I search for memories with query "dark mode preference"
    Then the search result should contain at least one result
    And each result should have a non-empty content

  # ── Message CRUD ────────────────────────────────────────────────────────────

  Scenario: Create and get a message
    When I create a message with agent "test-agent" invoker "test-user" group "conv-1" role "USER" content "Hello!"
    Then the message should have a non-empty id
    And the message should have role "USER"
    And the message should have content "Hello!"

  Scenario: List messages with filter
    Given a message exists with agent "test-agent" invoker "test-user" group "conv-list" role "USER" content "Listed message"
    When I list messages filtered by agent "test-agent" and group "conv-list"
    Then the result should contain at least one message
    And the total count should be a positive number

  Scenario: Delete a message
    Given a message exists with agent "test-agent" invoker "test-user" group "conv-del" role "USER" content "To be deleted"
    When I delete the message
    Then the message should no longer exist

  # ── Admin — Retention Config ────────────────────────────────────────────────

  Scenario: Get retention config
    When I get the retention config
    Then the retention config should have a non-empty id

  Scenario: Update retention config
    When I update the retention config with message_days 30 and memory_days 90
    Then the retention config should have message_days 30
    And the retention config should have memory_days 90

  # ── Bulk / utility operations ────────────────────────────────────────────────

  Scenario: Count memories for an agent and invoker
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "Count test memory"
    When I count memories for agent "test-agent" and invoker "test-user"
    Then the memory count should be a positive number

  # ── Filter ───────────────────────────────────────────────────────────────────

  Scenario: Filter memories by content substring
    Given a memory exists with agent "test-agent" and invoker "test-user" and content "The user prefers dark mode"
    When I list memories filtered by content containing "dark mode"
    Then the result should contain the memory with content "The user prefers dark mode"

  Scenario: Filter messages by metadata substring
    Given a message exists with agent "test-agent" invoker "test-user" group "conv-filter" role "USER" content "filter-test-message" and metadata "filter-marker"
    When I list messages filtered by metadata containing "filter-marker"
    Then the result should contain the message with content "filter-test-message"