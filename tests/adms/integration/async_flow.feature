Feature: ADMS Async Document Relation Flow
  As a developer using the async SDK
  I want to manage document relations via the async client
  So that I can use ADMS in async frameworks like FastAPI and LangGraph

  Background:
    Given the ADMS service is available

  Scenario: Create and query a relation using the async client
    Given I have a business object node type ID
    When I create a document relation using the async client named "AsyncIT_Invoice.pdf" for node "PY-SDK-ASYNC-IT-001"
    Then the async relation should be created with a valid ID
    When I query all relations using the async client for node "PY-SDK-ASYNC-IT-001"
    Then the created async relation ID should appear in the results
    And I clean up the async relation

  Scenario: Get relation by ID using the async client
    Given I have a business object node type ID
    When I create a document relation using the async client named "AsyncIT_Get.pdf" for node "PY-SDK-ASYNC-IT-001-GET"
    And I get the async relation by its ID
    Then the retrieved async relation ID should match
    And I clean up the async relation

  Scenario: Document scan state via async client
    Given I have a business object node type ID
    When I create a document relation using the async client named "AsyncIT_Scan.pdf" for node "PY-SDK-ASYNC-IT-001-SCAN"
    And I get the document using the async client
    Then the async scan state should be PENDING or CLEAN
    And I clean up the async relation

  Scenario: Download blocked when not CLEAN via async client
    Given I have a business object node type ID
    When I create a document relation using the async client named "AsyncIT_Download.pdf" for node "PY-SDK-ASYNC-IT-001-DL"
    And I attempt to download the document using the async client
    Then the async download should be blocked if not CLEAN
    And I clean up the async relation

  Scenario: Fetch nonexistent relation raises 404 via async client
    When I get an async relation with ID "a1b2c3d4-e5f6-4789-ab12-fedcba987654"
    Then a DocumentNotFoundError should be raised from the async client

  Scenario: Concurrent creates using the async client
    Given I have a business object node type ID
    When I concurrently create 3 relations using the async client for nodes "PY-SDK-ASYNC-IT-001-CONC"
    Then all 3 async relations should have unique IDs
    And I clean up all concurrent async relations
