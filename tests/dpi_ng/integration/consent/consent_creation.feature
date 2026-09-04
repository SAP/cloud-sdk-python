Feature: Consent SDK Integration
  As a developer using the SAP Consent SDK
  I want to create and activate consent configuration entities, purposes, templates, and records
  So that I can manage end-to-end consent lifecycle for data subjects

  Background:
    Given a configured consent client

  Scenario: Set up configuration entities
    When I create a controller
    Then the controller should have a valid id
    When I create an application
    Then the application should have a valid id
    When I reuse or create a jurisdiction named "India"
    Then the jurisdiction should have a valid id
    When I create a data subject type
    Then the data subject type should have a valid id
    When I create a third party
    Then the third party should have a valid id

  Scenario: Set up consent purpose
    When I create a purpose
    Then the purpose should have a valid id
    When I add an English explanatory text to the purpose
    Then the purpose text should be saved successfully
    When I activate the purpose
    Then the purpose lifecycle status should be "active"

  Scenario: Set up consent template
    When I create a consent template using the purpose, controller, and application
    Then the template should have a valid id
    When I assign the third party as a "RECIPIENT" to the template
    Then the third party recipient assignment should succeed
    When I assign the third party as a "SOURCE" to the template
    Then the third party source assignment should succeed
    When I activate the template
    Then the template lifecycle status should be "active"

  Scenario: Create consent record from template
    When I create a consent from the template for data subject "DS-IT-CREATION-001"
    Then at least one consent record should be returned
