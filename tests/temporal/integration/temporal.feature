Feature: Temporal Workflow Integration
  As a developer using the SDK
  I want to manage Temporal workflows
  So that I can orchestrate long-running processes reliably

  Background:
    Given the Temporal service is available
    And I have a valid Temporal client

  Scenario: Start and execute a workflow successfully
    Given I have a workflow id "wf-greet-1"
    And I have a task queue "greetings"
    When I execute the greeting workflow with input "World"
    Then the workflow should complete successfully
    And the result should be "Hello, World!"

  Scenario: Start a workflow without waiting for result
    Given I have a workflow id "wf-greet-async-1"
    And I have a task queue "greetings"
    When I start the greeting workflow with input "Async"
    Then the workflow handle should be returned
    When I wait for the workflow result
    Then the result should be "Hello, Async!"

  Scenario: Get a handle to an existing workflow
    Given I have a workflow id "wf-handle-1"
    And I have a task queue "greetings"
    When I execute the greeting workflow with input "Handle"
    And I get a handle to workflow "wf-handle-1"
    Then the workflow handle should be returned

  Scenario: Start a workflow with a duplicate id using ALLOW_DUPLICATE policy
    Given I have a workflow id "wf-duplicate-1"
    And I have a task queue "greetings"
    When I execute the greeting workflow with input "First"
    And I execute the greeting workflow with input "Second" using ALLOW_DUPLICATE policy
    Then the second workflow should complete successfully

  Scenario: Cancel a running workflow
    Given I have a workflow id "wf-cancel-1"
    And I have a task queue "long-running"
    When I start the long-running workflow
    And I cancel the workflow "wf-cancel-1"
    Then the workflow should be cancelled

  Scenario: Terminate a running workflow
    Given I have a workflow id "wf-terminate-1"
    And I have a task queue "long-running"
    When I start the long-running workflow
    And I terminate the workflow "wf-terminate-1" with reason "cleanup"
    Then the workflow should be terminated

  Scenario: Send a signal to a running workflow
    Given I have a workflow id "wf-signal-1"
    And I have a task queue "signalable"
    When I start the signalable workflow
    And I send signal "proceed" to workflow "wf-signal-1"
    Then the workflow should complete successfully

  Scenario: Query a running workflow state
    Given I have a workflow id "wf-query-1"
    And I have a task queue "queryable"
    When I start the queryable workflow
    And I query workflow "wf-query-1" for "current_status"
    Then the query result should be "running"

  Scenario: List workflows by type
    Given I have a task queue "greetings"
    When I execute the greeting workflow with input "List1" and id "wf-list-1"
    And I execute the greeting workflow with input "List2" and id "wf-list-2"
    And I list workflows with query 'WorkflowType = "GreetingWorkflow"'
    Then the workflow list should contain at least 2 entries

  Scenario: Execute a workflow with activity retry
    Given I have a workflow id "wf-retry-1"
    And I have a task queue "retryable"
    When I execute the retryable workflow that fails twice then succeeds
    Then the workflow should complete successfully
    And the activity should have been retried

  Scenario: Execute a workflow that times out
    Given I have a workflow id "wf-timeout-1"
    And I have a task queue "greetings"
    When I attempt to execute a workflow with execution timeout of 1 millisecond
    Then the execution should fail with a timeout error

  Scenario: Create a Temporal client with missing configuration
    When I attempt to create a client without required environment variables
    Then the client creation should fail with a configuration error

  Scenario: Create a worker with no workflows or activities
    Given I have a valid Temporal client
    When I attempt to create a worker with no workflows and no activities
    Then the worker creation should fail with a validation error

  Scenario: Schedule a recurring workflow
    Given I have a schedule id "sched-daily-greet"
    And I have a task queue "greetings"
    When I create a schedule that runs the greeting workflow every 24 hours
    Then the schedule should be created successfully
    And I delete the schedule "sched-daily-greet"

  Scenario: Execute workflows concurrently
    Given I have a task queue "greetings"
    When I execute 5 greeting workflows concurrently
    Then all concurrent workflows should complete successfully
    And no errors should occur during concurrent execution

  Scenario: Concurrent workflows with mixed success and failure
    Given I have a task queue "greetings"
    When I execute 6 workflows concurrently with some invalid inputs
    Then the valid workflows should complete successfully
    And the invalid workflows should fail with errors
    And no data inconsistencies should occur
