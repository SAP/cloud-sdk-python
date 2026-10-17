Feature: Thread Registry Integration

  Background:
    Given a configured Thread Registry

  # ── Sync CRUD ─────────────────────────────────────────────────────────────────

  Scenario: Register and get a thread
    When I register a thread with agent "test-agent" and invoker "test-user"
    Then the thread should have a non-empty threadId
    And the thread should have agentId "test-agent"
    And the thread should have invokerId "test-user"
    When I get the thread by id
    Then the fetched thread should match the registered thread

  Scenario: Create a thread with server-assigned ID
    When I create a thread with agent "test-agent" and invoker "test-user"
    Then the thread should have a non-empty threadId
    And the thread should have agentId "test-agent"
    And the thread should have invokerId "test-user"

  Scenario: List threads filtered by agent_id
    Given a thread is registered with agent "test-agent" and invoker "test-user"
    When I list threads filtered by agent "test-agent"
    Then the result should contain at least one thread
    And all returned threads should have agentId "test-agent"

  Scenario: Update thread description
    Given a thread is registered with agent "test-agent" and invoker "test-user"
    When I update the thread description to "updated description"
    Then the thread should have description "updated description"

  Scenario: Delete a thread
    Given a thread is registered with agent "test-agent" and invoker "test-user"
    When I delete the thread
    Then getting the thread should raise AgentMemoryThreadNotFoundError

  Scenario: Re-registering same thread with same owner is idempotent
    Given a thread is registered with agent "test-agent" and invoker "test-user"
    When I register the same thread again with agent "test-agent" and invoker "test-user"
    Then no error should be raised
    And the thread should have agentId "test-agent"

  Scenario: Registering same thread with different owner raises a conflict
    Given a thread is registered with agent "test-agent" and invoker "test-user"
    When I register the same thread with agent "other-agent" and invoker "other-user"
    Then a AgentMemoryThreadConflictError should be raised
