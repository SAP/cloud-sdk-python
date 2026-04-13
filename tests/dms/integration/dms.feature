Feature: Document Management Service Integration
  As a developer using the SDK
  I want to manage repositories, folders, documents, and ACLs
  So that I can store and organize documents in the DMS service

  Background:
    Given the DMS service is available
    And I have a valid DMS client

  # ==================== Repository Management ====================

  Scenario: List all repositories
    When I list all repositories
    Then the repository list should be retrieved successfully
    And the list should contain at least 1 repository

  Scenario: Get repository details
    Given I select the first available repository
    When I get repository details
    Then the repository details should be retrieved successfully
    And the repository should have a CMIS repository ID
    And the repository should have a name

  # ==================== Configuration Management ====================

  Scenario: Create and delete a configuration
    Given I have a config named "tempspaceMaxContentSize" with value "1073741824"
    When I create the configuration
    Then the configuration creation should be successful
    And the configuration should have the expected name and value
    When I delete the created configuration
    Then the configuration deletion should be successful

  Scenario: List all configurations
    When I list all configurations
    Then the configuration list should be retrieved successfully

  # ==================== Folder Operations ====================

  Scenario: Create a folder
    Given I select the first available repository
    And I use the root folder as parent
    When I create a folder named "sdk-integration-test-folder"
    Then the folder creation should be successful
    And the created folder should have the correct name
    And I clean up the created folder

  Scenario: Create a folder with description
    Given I select the first available repository
    And I use the root folder as parent
    When I create a folder named "sdk-test-described-folder" with description "Integration test folder"
    Then the folder creation should be successful
    And the created folder should have the correct name
    And I clean up the created folder

  # ==================== Document Operations ====================

  Scenario: Upload a document
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Hello from SAP Cloud SDK Python integration tests!"
    When I upload a document named "sdk-integration-test.txt" with mime type "text/plain"
    Then the document upload should be successful
    And the uploaded document should have the correct name
    And the document should have mime type "text/plain"
    And I clean up the created document

  Scenario: Upload a document without explicit mime type
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Binary content simulation"
    When I upload a document named "sdk-test-no-mime.bin" without specifying mime type
    Then the document upload should be successful
    And the document should have a mime type assigned by the server
    And I clean up the created document

  # ==================== Read Operations ====================

  Scenario: Get object details for a document
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Content for get-object test"
    And I upload a document named "sdk-get-object-test.txt" with mime type "text/plain"
    When I get the object by its ID
    Then the object should be retrieved successfully
    And the object should be a Document
    And the object name should be "sdk-get-object-test.txt"
    And I clean up the created document

  Scenario: Get object details for a folder
    Given I select the first available repository
    And I use the root folder as parent
    And I create a folder named "sdk-get-folder-test"
    When I get the folder object by its ID
    Then the object should be retrieved successfully
    And the object should be a Folder
    And I clean up the created folder

  Scenario: Get object with ACL included
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "ACL test content"
    And I upload a document named "sdk-acl-object-test.txt" with mime type "text/plain"
    When I get the object by its ID with ACL included
    Then the object should be retrieved successfully
    And I clean up the created document

  Scenario: Download document content
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Download me!"
    And I upload a document named "sdk-download-test.txt" with mime type "text/plain"
    When I download the document content
    Then the download should be successful
    And the downloaded content should match "Download me!"
    And I clean up the created document

  Scenario: List children of a folder
    Given I select the first available repository
    And I use the root folder as parent
    And I create a folder named "sdk-children-parent"
    And I create a child document "sdk-child-doc.txt" in the folder
    When I list children of the folder
    Then the children list should be retrieved successfully
    And the children should contain at least 1 item
    And I clean up the children folder

  Scenario: List children with pagination
    Given I select the first available repository
    And I use the root folder as parent
    When I list children of the root folder with max items 5
    Then the children list should be retrieved successfully

  # ==================== Update Operations ====================

  Scenario: Update document properties
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Update properties test"
    And I upload a document named "sdk-update-props-test.txt" with mime type "text/plain"
    When I update the object name to "sdk-updated-name.txt"
    Then the update should be successful
    And the updated object name should be "sdk-updated-name.txt"
    And I clean up the updated document

  # ==================== Versioning ====================

  Scenario: Check out and cancel check out
    Given I select a version-enabled repository
    And I use the root folder as parent
    And I have document content "Versioning test content"
    And I upload a document named "sdk-versioning-test.txt" with mime type "text/plain"
    When I check out the document
    Then the check out should be successful
    And the PWC should be a private working copy
    When I cancel the check out
    Then the cancel check out should be successful
    And I clean up the created document

  Scenario: Check out and check in a new version
    Given I select a version-enabled repository
    And I use the root folder as parent
    And I have document content "Version 1 content"
    And I upload a document named "sdk-checkin-test.txt" with mime type "text/plain"
    When I check out the document
    Then the check out should be successful
    When I check in with content "Version 2 content" and comment "Updated via integration test"
    Then the check in should be successful
    And the new version label should not be empty
    And I clean up the created document

  # ==================== ACL Operations ====================

  Scenario: Get ACL for an object
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "ACL read test"
    And I upload a document named "sdk-acl-read-test.txt" with mime type "text/plain"
    When I get the ACL for the document
    Then the ACL should be retrieved successfully
    And I clean up the created document

  # ==================== Error Handling ====================

  Scenario: Get non-existent object
    Given I select the first available repository
    When I attempt to get a non-existent object
    Then the operation should fail with a not found error

  Scenario: Download non-existent document
    Given I select the first available repository
    When I attempt to download a non-existent document
    Then the operation should fail with a not found error

  # ==================== Delete & Restore Operations ====================

  Scenario: Delete a document
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Delete me!"
    And I upload a document named "sdk-delete-test.txt" with mime type "text/plain"
    When I delete the document
    Then the delete should be successful
    When I attempt to get the deleted document
    Then the operation should fail with a not found error

  Scenario: Delete and restore a document
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Delete and restore me!"
    And I upload a document named "sdk-restore-test.txt" with mime type "text/plain"
    When I delete the document
    Then the delete should be successful
    When I restore the deleted document
    Then the restore should be successful
    And I clean up the created document

  # ==================== Append Content Stream ====================

  Scenario: Append content to a document
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Initial content"
    And I upload a document named "sdk-append-test.txt" with mime type "text/plain"
    When I append content "Additional content" to the document
    Then the append should be successful
    And the appended document should be a Document
    And I clean up the created document

  Scenario: Append content as last chunk
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Base content"
    And I upload a document named "sdk-append-last-test.txt" with mime type "text/plain"
    When I append content "Final chunk" as the last chunk
    Then the append should be successful
    And I clean up the created document

  # ==================== CMIS Query ====================

  Scenario: Execute a simple CMIS query
    Given I select the first available repository
    And I use the root folder as parent
    And I have document content "Query test content"
    And I upload a document named "sdk-query-test.txt" with mime type "text/plain"
    When I execute a CMIS query for documents named "sdk-query-test"
    Then the query should be successful
    And the query results should contain at least 1 item
    And I clean up the created document

  Scenario: Execute a CMIS query with pagination
    Given I select the first available repository
    When I execute a CMIS query for all documents with max items 5
    Then the query should be successful
