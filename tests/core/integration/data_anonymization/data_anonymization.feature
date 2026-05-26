Feature: Data Anonymization SDK Integration
  As a developer using the SAP Cloud SDK
  I want to anonymize and pseudonymize text and files
  So that I can safely process sensitive content

  Background:
    Given the data anonymization service is available
    And I have a valid data anonymization client

  Scenario: Anonymize text successfully
    When I anonymize the text "John Doe lives at john.doe@example.com and phone +1-555-123-4567"
    Then the text result should contain "<person>"
    And the text result should contain "<email>"
    And the text result should contain "<phone_number>"

  Scenario: Pseudonymize text successfully
    When I pseudonymize the text "John Doe lives at john.doe@example.com"
    Then the text result should contain "<<person>:"
    And the text result should contain "<<email>:"
    And the text result should not equal the original text

  Scenario: Anonymize file successfully
    Given I have a text file named "sample.txt" containing "John Doe lives at john.doe@example.com and phone +1-555-123-4567"
    When I anonymize the prepared file
    Then the text result should contain "<person>"
    And the text result should contain "<email>"
    And the text result should contain "<phone_number>"

  Scenario: Reject an empty text payload
    When I anonymize an empty text payload
    Then the operation should fail with validation error "text must not be empty"

  Scenario: Wrap transport failures during anonymization
    Given a data anonymization client with network failure
    When I anonymize the text "John Doe"
    Then the operation should fail with transport error "Network error calling anonymize_text"
