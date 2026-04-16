Feature: Audit Log Integration
  As a developer using the SDK
  I want to log audit events
  So that I can track security, data access, and configuration changes

  Background:
    Given the audit log service is available
    And I have a valid audit logger

  Scenario: Log a security event
    Given I have a user "test-user-security"
    And I have a tenant subscriber
    When I create a security event with message "User login attempt"
    And I add user information to the event
    And I add tenant information to the event
    And I add IP address "192.168.1.100"
    And I add attribute "action" with value "login"
    And I log the security event
    Then the event should be logged successfully

  Scenario: Log a security event with network failure
    Given I have a user "test-user-security-network-fail"
    And I have a tenant subscriber
    And the audit log service is configured with an unreachable endpoint
    When I create a security event with message "Network failure test"
    And I add user information to the event
    And I add tenant information to the event
    And I add IP address "192.168.1.100"
    And I attempt to log the security event
    Then the logging should fail with a network error

  Scenario: Log a security event without required fields
    When I create a security event with message ""
    And I log the security event
    Then the operation should fail with the following errors:
      | SecurityEvent data must not be empty |


  Scenario: Log a data access event
    Given I have a user "test-user-data-access"
    And I have a tenant provider
    When I create a data access event
    And I add user information to the event
    And I add tenant information to the event
    And I add data object "s3-object" with properties:
      | bucket | test-bucket |
      | key    | test-file.txt |
    And I add data subject "user" with properties:
      | username | john.doe |
    And I add attribute "operation" with boolean value true
    And I log the data access event
    Then the event should be logged successfully

  Scenario: Log a data access event with transport failure
    Given I have a user "test-user-data-access-transport-fail"
    And I have a tenant provider
    And the audit log service returns Service Unavailable
    When I create a data access event
    And I add user information to the event
    And I add tenant information to the event
    And I add data object "s3-object" with properties:
      | bucket | test-bucket |
      | key    | test-file.txt |
    And I add data subject "user" with properties:
      | username | john.doe |
    And I add attribute "operation" with value "true"
    And I attempt to log the data access event
    Then the logging should fail with a transport error

  Scenario: Log a data access event without required fields
    When I create a data access event
    And I log the data access event
    Then the operation should fail with the following errors:
      | DataAccessEvent object_type must not be empty |
      | DataAccessEvent subject_type must not be empty |
      | DataAccessEvent must have at least one attribute |

  Scenario: Log a data modification event
    Given I have a user "test-user-data-mod"
    And I have a tenant provider
    When I create a data modification event
    And I add user information to the event
    And I add tenant information to the event
    And I add data object "database-record" with properties:
      | table | users |
      | id    | 123   |
    And I add data subject "user" with properties:
      | username | john.doe |
    And I add attribute change from "old@example.com" to "new@example.com" for "email"
    And I add attribute change from "active" to "inactive" for "status"
    And I log the data modification event
    Then the event should be logged successfully

  Scenario: Log a data modification event without required fields
    When I create a data modification event
    And I log the data modification event
    Then the operation should fail with the following errors:
      | DataModificationEvent object_type must not be empty |
      | DataModificationEvent subject_type must not be empty |
      | DataModificationEvent must have at least one attribute |


  Scenario: Log a configuration change event
    Given I have a user "test-user-config"
    And I have a tenant provider
    When I create a configuration change event
    And I add user information to the event
    And I add tenant information to the event
    And I set configuration ID "config-123"
    And I add data object "application-config" with properties:
      | component | auth        |
      | file      | config.yaml |
    And I add attribute change from "30s" to "60s" for "timeout"
    And I add attribute change from "3" to "5" for "max_retries"
    And I log the configuration change event
    Then the event should be logged successfully

  Scenario: Log a configuration change event without required fields
    When I create a configuration change event
    And I log the configuration change event
    Then the operation should fail with the following errors:
      | ConfigurationChangeEvent object_type must not be empty |
      | ConfigurationChangeEvent must have at least one attribute |
    And I log a configuration change event with ID "config-multiple"
    Then all events should be logged successfully

  Scenario: Log multiple events with mixed success and failures
    Given I have a user "test-user-mixed-results"
    And I have a tenant subscriber
    And the audit log service has intermittent connectivity issues
    When I attempt to log a security event with message "Mixed results test - security"
    And I attempt to log a data access event for object "test-object-mixed"
    And I attempt to log a data modification event for object "test-record-mixed"
    And I attempt to log a configuration change event with ID "config-mixed"
    Then some events should succeed and some should fail
    And the failed events should have error messages

  Scenario: Concurrent audit logging
    Given I have multiple users for concurrent testing
     And I have a tenant subscriber
    When I log events simultaneously from multiple operations
    Then all concurrent events should be logged successfully
    And no errors should occur during concurrent logging

  Scenario: Concurrent logging with network failures
    Given I have multiple users for concurrent testing
    And I have a tenant subscriber
    And the audit log service has network connectivity issues
    When I attempt to log events simultaneously from multiple operations
    Then some concurrent events should fail with network errors
    And the successful events should be logged correctly
    And no data corruption should occur

  Scenario: Concurrent logging with validation errors
    Given I have multiple users for concurrent testing
    And I have a tenant subscriber
    When I attempt to log events simultaneously with mixed valid and invalid events
    Then the valid events should be logged successfully
    And the invalid events should fail with validation errors
    And no data inconsistencies should occur during validation

  Scenario: Log a data deletion event
    Given I have a user "test-user-data-deletion"
    And I have a tenant provider
    When I create a data deletion event
    And I add user information to the event
    And I add tenant information to the event
    And I add data object "database-record" with properties:
      | table | users |
      | id    | 123   |
    And I add data subject "user" with properties:
      | username | john.doe |
    And I delete attribute "email" with previous value "john.doe@example.com"
    And I delete attribute "phone" with previous value "+1-555-0123"
    And I log the data deletion event
    Then the event should be logged successfully

  Scenario: Log a data deletion event without required fields
    When I create a data deletion event
    And I log the data deletion event
    Then the operation should fail with the following errors:
      | DataDeletionEvent object_type must not be empty |
      | DataDeletionEvent subject_type must not be empty |
      | DataDeletionEvent must have at least one attribute |

  Scenario: Log a data deletion event with transport failure
    Given I have a user "test-user-data-deletion-transport-fail"
    And I have a tenant provider
    And the audit log service returns Service Unavailable
    When I create a data deletion event
    And I add user information to the event
    And I add tenant information to the event
    And I add data object "database-record" with properties:
      | table | users |
      | id    | 456   |
    And I add data subject "user" with properties:
      | username | jane.doe |
    And I delete attribute "profile_data" with previous value "sensitive_info"
    And I attempt to log the data deletion event
    Then the logging should fail with a transport error

  Scenario: Log a configuration deletion event
    Given I have a user "test-user-config-deletion"
    And I have a tenant provider
    When I create a configuration deletion event
    And I add user information to the event
    And I add tenant information to the event
    And I set configuration ID "config-to-delete-456"
    And I add data object "application-config" with properties:
      | component | security    |
      | file      | auth.yaml   |
    And I delete attribute "encryption_key" with previous value "****"
    And I delete attribute "session_timeout" with previous value "3600"
    And I log the configuration deletion event
    Then the event should be logged successfully

  Scenario: Log a configuration deletion event without required fields
    When I create a configuration deletion event
    And I log the configuration deletion event
    Then the operation should fail with the following errors:
      | ConfigurationDeletionEvent object_type must not be empty |
      | ConfigurationDeletionEvent must have at least one attribute |

  Scenario: Log a configuration deletion event with network failure
    Given I have a user "test-user-config-deletion-network-fail"
    And I have a tenant provider
    And the audit log service is configured with an unreachable endpoint
    When I create a configuration deletion event
    And I add user information to the event
    And I add tenant information to the event
    And I set configuration ID "config-network-fail-789"
    And I add data object "system-config" with properties:
      | service | authentication |
      | version | 2.1           |
    And I delete attribute "api_keys" with previous value "[redacted]"
    And I attempt to log the configuration deletion event
    Then the logging should fail with a network error

  Scenario: Event with complex data structures
    Given I have a user "test-user-complex"
     And I have a tenant subscriber
    When I create a security event with message "Event with complex data structures"
    And I add user information to the event
    And I add tenant information to the event
    And I add complex custom details with nested objects and arrays
    And I log the security event
    Then the event should be logged successfully
