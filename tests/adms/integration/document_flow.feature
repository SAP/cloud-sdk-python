Feature: ADMS Document Relation Flow
  As a developer using the SDK
  I want to manage document relations
  So that I can link documents to business objects

  Background:
    Given the ADMS service is available

  Scenario: Create a document relation
    Given I have a business object node type ID
    When I create a document relation named "IntegrationTest_Invoice.pdf"
    Then the relation should be created with a valid ID
    And I clean up the created relation

  Scenario: Query relations includes the created relation
    Given I have a business object node type ID
    And I have created a document relation named "QueryTest.pdf"
    When I query all document relations
    Then the created relation ID should appear in the results
    And I clean up the created relation

  Scenario: Get relation by ID
    Given I have a business object node type ID
    And I have created a document relation named "GetByIdTest.pdf"
    When I get the relation by its ID
    Then the retrieved relation ID should match the created ID
    And I clean up the created relation

  Scenario: Document scan state is PENDING or CLEAN after creation
    Given I have a business object node type ID
    And I have created a document relation named "ScanStateTest.pdf"
    When I get the document for the created relation
    Then the scan state should be PENDING or CLEAN
    And I clean up the created relation

  Scenario: Download is blocked when scan state is not CLEAN
    Given I have a business object node type ID
    And I have created a document relation named "DownloadTest.pdf"
    When I attempt to download the document
    Then the download should be blocked if not CLEAN
    And I clean up the created relation

  Scenario: Update document name
    Given I have a business object node type ID
    And I have created a document relation named "OriginalName.pdf"
    When I update the document name to "UpdatedName.pdf"
    Then the document name should be "UpdatedName.pdf"
    And I clean up the created relation

  Scenario: Delete a document relation
    Given I have a business object node type ID
    When I create a document relation named "DeleteTest.pdf"
    Then the relation should be created with a valid ID
    When I delete the created relation
    Then fetching the deleted relation should raise DocumentNotFoundError

  Scenario: Draft flow - create and activate
    Given I have a business object node type ID
    When I create a draft for business object node "PY-SDK-IT-DRAFT-001"
    And I validate the draft for "PY-SDK-IT-DRAFT-001"
    And I activate the draft for "PY-SDK-IT-DRAFT-001"
    Then the active relation list should not be empty
    And I clean up all active relations for "PY-SDK-IT-DRAFT-001"

  Scenario: Draft flow - create and discard
    Given I have a business object node type ID
    When I create a draft for business object node "PY-SDK-IT-DRAFT-002"
    And I discard the draft for "PY-SDK-IT-DRAFT-002"
    Then no active relations should exist for "PY-SDK-IT-DRAFT-002"

  Scenario: Fetch nonexistent document raises 404
    When I get a document with relation ID "a1b2c3d4-e5f6-4789-ab12-fedcba987654"
    Then a DocumentNotFoundError should be raised

  Scenario: Fetch nonexistent relation raises 404
    When I get a relation with ID "a1b2c3d4-e5f6-4789-ab12-fedcba987654"
    Then a DocumentNotFoundError should be raised
