Feature: Object Store Integration
  As a developer using the SDK
  I want to manage objects in object storage
  So that I can store, retrieve, and manage files

  Background:
    Given the object store service is available
    And I have a valid object store client

  Scenario: Upload object from bytes
    Given I have test content as bytes "Hello, Object Store, from a byte slice!!!"
    And I have an object named "memory-asset.txt"
    When I upload the object from bytes with content type "text/plain"
    Then the upload should be successful
    And the object should exist in the store
    And I clean up the object

  Scenario: Upload object with network failure
    Given I have test content as bytes "Network failure test content"
    And I have an object named "network-fail-test.txt"
    And the object store service is configured with an unreachable endpoint
    When I attempt to upload the object from bytes with content type "text/plain"
    Then the upload should fail with a network error

  Scenario: Upload object from file
    Given I have a temporary file with JSON content:
      """
      {"status": "ok", "test_id": "file-upload-test"}
      """
    And I have an object named "file-asset.json"
    When I upload the object from file with content type "application/json"
    Then the upload should be successful
    And the object should exist in the store
    And I clean up the object

  Scenario: Upload file that doesn't exist
    Given I have a non-existent file path "/tmp/non-existent-file.txt"
    And I have an object named "non-existent-upload.txt"
    When I attempt to upload the object from file with content type "text/plain"
    Then the upload should fail with a file not found error

  Scenario: Download object
    Given I have test content as bytes "Test content for retrieval"
    And I have an object named "test-content.txt"
    And I upload the object from bytes with content type "text/plain"
    When I download the object
    Then the download should be successful
    And the downloaded content should match the original content
    And I clean up the object

  Scenario: Download non-existent object
    Given I have an object named "non-existent-object.txt"
    When I attempt to download the object
    Then the download should fail with an object not found error

  Scenario: Download with permission denied
    Given I have an object named "permission-denied-object.txt"
    And the object store service returns permission denied for downloads
    When I attempt to download the object
    Then the download should fail with a permission denied error

  Scenario: Get object metadata
    Given I have test content as bytes "Content for metadata testing"
    And I have an object named "metadata-test.txt"
    And I upload the object from bytes with content type "text/plain"
    When I get the object metadata
    Then the metadata should be retrieved successfully
    And the object size should match the content size
    And the ETag should not be empty
    And I clean up the object

  Scenario: Get metadata for non-existent object
    Given I have an object named "non-existent-metadata.txt"
    When I attempt to get the object metadata
    Then the metadata retrieval should fail with an object not found error

  Scenario: Get metadata with permission denied
    Given I have an object named "permission-denied-metadata.txt"
    And the object store service returns permission denied for metadata requests
    When I attempt to get the object metadata
    Then the metadata retrieval should fail with a permission denied error

  Scenario: List objects with prefix
    Given I have multiple test objects:
      | name      | content                    |
      | file1.txt | Test content for file1.txt |
      | file2.txt | Test content for file2.txt |
      | file3.txt | Test content for file3.txt |
    When I upload all test objects with content type "text/plain"
    And I list objects with the test prefix
    Then the list should contain 3 objects
    And all uploaded objects should be in the list
    And I clean up all test objects

  Scenario: List objects with invalid permissions
    Given the object store service returns permission denied for list operations
    When I attempt to list objects with prefix "test-prefix"
    Then the list operation should fail with a permission denied error

  Scenario: List objects with network failure
    Given the object store service is configured with an unreachable endpoint
    When I attempt to list objects with prefix "test-prefix"
    Then the list operation should fail with a network error

  Scenario: Check object existence
    Given I have test content as bytes "This object exists"
    And I have an object named "existing-object.txt"
    And I upload the object from bytes with content type "text/plain"
    When I check if the object exists
    Then the object should exist
    When I check if a non-existent object "non-existent-object.txt" exists
    Then the non-existent object should not exist
    And I clean up the object

  Scenario: Check existence with network errors
    Given I have an object named "network-error-check.txt"
    And the object store service is configured with an unreachable endpoint
    When I attempt to check if the object exists
    Then the existence check should fail with a network error

  Scenario: Delete object
    Given I have test content as bytes "This object will be deleted"
    And I have an object named "to-be-deleted.txt"
    And I upload the object from bytes with content type "text/plain"
    And the object should exist in the store
    When I delete the object
    Then the deletion should be successful
    And the object should not exist in the store

  Scenario: Delete non-existent object
    Given I have an object named "non-existent-delete.txt"
    When I attempt to delete the object
    Then the deletion should be successful

  Scenario: Delete with permission denied
    Given I have an object named "permission-denied-delete.txt"
    And the object store service returns permission denied for delete operations
    When I attempt to delete the object
    Then the deletion should fail with a permission denied error

  Scenario: Concurrent object operations
    Given I have multiple objects to upload simultaneously
    When I perform concurrent upload operations
    Then all concurrent uploads should be successful
    And the expected number of objects should be created
    And I clean up all concurrent test objects

  Scenario: Concurrent operations with mixed failures
    Given I have multiple objects to upload simultaneously
    And the object store service has intermittent connectivity issues
    When I perform concurrent upload operations with mixed conditions
    Then some concurrent uploads should succeed and some should fail
    And the successful uploads should be properly stored
    And the failed uploads should have appropriate error messages
    And I clean up all successful test objects

  Scenario: Object store timeout handling
    Given I have test content as bytes "Testing timeout behavior"
    And I have an object named "timeout-test.txt"
    When I upload the object with a reasonable timeout
    Then the upload should complete within the timeout
    And I clean up the object

  Scenario Outline: Upload different file types
    Given I have test content as bytes "<content>"
    And I have an object named "<filename>"
    When I upload the object from bytes with content type "<content_type>"
    Then the upload should be successful
    And the object should exist in the store
    And I clean up the object

    Examples:
      | filename  | content                         | content_type     |
      | test.txt  | Plain text content              | text/plain       |
      | test.json | {"key": "value"}                | application/json |
      | test.xml  | <root><item>data</item></root>  | application/xml  |
      | test.html | <html><body>Hello</body></html> | text/html        |

  Scenario Outline: Object operation validation failures
    Given I have test content as bytes "Validation test content"
    And I have an object named "<object_name>"
    When I attempt to perform "<operation>" with "<invalid_condition>"
    Then the operation should fail with "<expected_error>"

    Examples:
      | operation | object_name           | invalid_condition     | expected_error           |
      | upload    | invalid/object/name   | invalid object name   | invalid object name      |
      | upload    | valid-object.txt      | invalid credentials   | authentication failed    |
      | download  |                       | empty object name     | invalid object name      |
      | delete    | invalid-chars<>.txt   | invalid object name   | invalid object name      |
      | metadata  | /invalid/path.txt     | invalid object path   | invalid object name      |
