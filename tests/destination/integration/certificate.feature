Feature: Destination Service Integration - Certificates
  As a developer using the SDK
  I want to manage destination certificates
  So that I can configure external system connections

  Background:
    Given the destination service is available
    And I have valid destination clients

  Scenario: Create and read certificate
    Given I have a certificate named "test-cert.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level
    Then the certificate creation should be successful
    When I get subaccount certificate "test-cert.pem" with "PROVIDER_ONLY" access strategy
    Then the certificate should be retrieved successfully
    And the certificate type should be "PEM"
    And I clean up the subaccount certificate "test-cert.pem"

  Scenario: Update certificate
    Given I have a certificate named "test-cert-update.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level
    Then the certificate creation should be successful
    When I update the certificate content
    And I update the certificate at subaccount level
    Then the certificate update should be successful
    When I get subaccount certificate "test-cert-update.pem" with "PROVIDER_ONLY" access strategy
    Then the certificate should have updated content
    And I clean up the subaccount certificate "test-cert-update.pem"

  Scenario: Delete certificate
    Given I have a certificate named "test-cert-delete.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level
    Then the certificate creation should be successful
    When I delete the subaccount certificate "test-cert-delete.pem"
    Then the certificate deletion should be successful
    When I get subaccount certificate "test-cert-delete.pem" with "PROVIDER_ONLY" access strategy
    Then the certificate should not be found

  Scenario: Get non-existent instance certificate
    When I get instance certificate "non-existent-cert.pem"
    Then the certificate should not be found

  Scenario: Get non-existent subaccount certificate
    When I get subaccount certificate "non-existent-cert.pem" with "PROVIDER_ONLY" access strategy
    Then the certificate should not be found

  Scenario: Get certificate using subscriber first strategy
    Given I use tenant "1776453780"
    And I have a certificate named "subscriber-dest-test.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I get subaccount certificate "subscriber-dest-test.pem" with "SUBSCRIBER_FIRST" access strategy
    Then the certificate should be retrieved successfully

  Scenario: Get certificate using subscriber only strategy
    Given I use tenant "1776453780"
    And I have a certificate named "subscriber-dest-test.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I get subaccount certificate "subscriber-dest-test.pem" with "SUBSCRIBER_ONLY" access strategy
    Then the certificate should be retrieved successfully

  Scenario: Get certificate using provider first strategy
    Given I use tenant "1776453780"
    And I have a certificate named "subscriber-dest-test.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I get subaccount certificate "subscriber-dest-test.pem" with "PROVIDER_FIRST" access strategy
    Then the certificate should be retrieved successfully

  Scenario: Get certificate using provider only strategy
    Given I use tenant "1776453780"
    And I have a certificate named "subscriber-dest-test.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I get subaccount certificate "subscriber-dest-test.pem" with "PROVIDER_ONLY" access strategy
    Then the certificate should not be found

  Scenario: Create and list instance certificates
    Given I have multiple subaccount certificates:
      | name                 | type |
      | test-cert-list-1.pem | PEM  |
      | test-cert-list-2.pem | PEM  |
    And I use tenant "1776453780"
    When I create all instance certificates
    Then all certificate creations should be successful
    When I list instance certificates
    Then the certificate list should contain at least 2 certificates
    And the certificate "test-cert-list-1.pem" should be in the list
    And the certificate "test-cert-list-2.pem" should be in the list
    And I clean up all subaccount certificates

  Scenario: Create and list subaccount certificates (provider access)
    Given I have multiple subaccount certificates:
      | name                 | type |
      | test-cert-list-1.pem | PEM  |
      | test-cert-list-2.pem | PEM  |
    And I use tenant "1776453780"
    When I create all subaccount certificates
    Then all certificate creations should be successful
    When I list subaccount certificates with "PROVIDER_FIRST" access strategy
    Then the certificate list should contain at least 2 certificates
    And the certificate "test-cert-list-1.pem" should be in the list
    And the certificate "test-cert-list-2.pem" should be in the list
    When I list subaccount certificates with "PROVIDER_ONLY" access strategy
    Then the certificate list should contain at least 2 certificates
    And the certificate "test-cert-list-1.pem" should be in the list
    And the certificate "test-cert-list-2.pem" should be in the list
    And I clean up all subaccount certificates

  Scenario: List certificates using subscriber first strategy
    Given I use tenant "1776453780"
    And I have a certificate named "subscriber-dest-test.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I list subaccount certificates with "SUBSCRIBER_FIRST" access strategy
    Then the certificate "subscriber-dest-test.pem" should be in the list

  Scenario: List certificates using subscriber only strategy
    Given I use tenant "1776453780"
    And I have a certificate named "subscriber-dest-test.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I list subaccount certificates with "SUBSCRIBER_ONLY" access strategy
    Then the certificate "subscriber-dest-test.pem" should be in the list

  Scenario: List certificates using provider first strategy
    Given I use tenant "1776453780"
    When I list subaccount certificates with "PROVIDER_FIRST" access strategy
    Then the certificate list should be retrieved successfully

  Scenario: List certificates using provider only strategy
    Given I use tenant "1776453780"
    When I list subaccount certificates with "PROVIDER_ONLY" access strategy
    Then the certificate "subscriber-dest-test.pem" should not be in the list

  Scenario: Manage labels for subaccount certificate
    Given I have a certificate named "test-cert-labels.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level
    Then the certificate creation should be successful
    When I update labels on the certificate "test-cert-labels.pem" at subaccount level: key "env" values "prod"
    Then the certificate label operation should be successful
    When I get labels for the certificate "test-cert-labels.pem" at subaccount level
    Then the certificate should have label key "env" with value "prod"
    When I patch labels on the certificate "test-cert-labels.pem" at subaccount level with action "ADD": key "team" values "platform"
    Then the certificate label operation should be successful
    When I get labels for the certificate "test-cert-labels.pem" at subaccount level
    Then the certificate should have label key "team" with value "platform"
    And I clean up the subaccount certificate "test-cert-labels.pem"

  Scenario: List subaccount certificates filtered by label
    Given I have a certificate named "test-cert-list-by-label.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level
    Then the certificate creation should be successful
    When I update labels on the certificate "test-cert-list-by-label.pem" at subaccount level: key "list-filter-env" values "prod"
    Then the certificate label operation should be successful
    When I list subaccount certificates with "PROVIDER_ONLY" access strategy and label filter key "list-filter-env" values "prod"
    Then the certificate list should be retrieved successfully
    And the certificate "test-cert-list-by-label.pem" should be in the list
    And I clean up the subaccount certificate "test-cert-list-by-label.pem"

  # ==================== SUBSCRIBER WRITE SCENARIOS ====================

  Scenario: Create certificate at subaccount level for subscriber
    Given I use tenant "1776453780"
    And I have a certificate named "test-cert-sub-write.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I get subaccount certificate "test-cert-sub-write.pem" with "SUBSCRIBER_ONLY" access strategy
    Then the certificate should be retrieved successfully
    And the certificate type should be "PEM"

  Scenario: Update certificate at subaccount level for subscriber
    Given I use tenant "1776453780"
    And I have a certificate named "test-cert-sub-update.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I update the certificate content
    And I update the certificate at subaccount level for subscriber
    Then the certificate update should be successful
    When I get subaccount certificate "test-cert-sub-update.pem" with "SUBSCRIBER_ONLY" access strategy
    Then the certificate should have updated content

  Scenario: Delete certificate at subaccount level for subscriber
    Given I use tenant "1776453780"
    And I have a certificate named "test-cert-sub-delete.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I delete the subaccount certificate "test-cert-sub-delete.pem" for subscriber
    Then the certificate deletion should be successful
    When I get subaccount certificate "test-cert-sub-delete.pem" with "SUBSCRIBER_ONLY" access strategy
    Then the certificate should not be found

  Scenario: Subscriber certificate not visible in provider-only context
    Given I use tenant "1776453780"
    And I have a certificate named "test-cert-sub-isolation.pem"
    And the certificate has type "PEM"
    And the certificate has valid PEM content
    When I create the certificate at subaccount level for subscriber
    Then the certificate creation should be successful
    When I get subaccount certificate "test-cert-sub-isolation.pem" with "PROVIDER_ONLY" access strategy
    Then the certificate should not be found
