Feature: Destination Service Integration
  As a developer using the SDK
  I want to manage destinations
  So that I can configure external system connections

  Background:
    Given the destination service is available
    And I have valid destination clients

  Scenario: Create and read instance-level destination
    Given I have a destination named "test-dest-instance" of type "HTTP"
    And the destination has URL "https://api.example.com"
    And the destination has proxy type "Internet"
    And the destination has authentication "NoAuthentication"
    When I create the destination at instance level
    Then the destination creation should be successful
    When I get instance destination "test-dest-instance"
    Then the destination should be retrieved successfully
    And the destination URL should be "https://api.example.com"
    And I clean up the instance destination "test-dest-instance"

  Scenario: Create and read subaccount-level destination with provider access
    Given I have a destination named "test-dest-subaccount" of type "HTTP"
    And the destination has URL "https://provider-api.example.com"
    And the destination has proxy type "Internet"
    And the destination has authentication "BasicAuthentication"
    And the destination has property "User" with value "testuser"
    And the destination has property "Password" with value "testpass"
    When I create the destination at subaccount level
    Then the destination creation should be successful
    When I get subaccount destination "test-dest-subaccount" with "PROVIDER_ONLY" access strategy
    Then the destination should be retrieved successfully
    And the destination URL should be "https://provider-api.example.com"
    And I clean up the subaccount destination "test-dest-subaccount"

  Scenario: Update destination
    Given I have a destination named "test-dest-update" of type "HTTP"
    And the destination has URL "https://original.example.com"
    And the destination has authentication "NoAuthentication"
    When I create the destination at subaccount level
    Then the destination creation should be successful
    When I update the destination URL to "https://updated.example.com"
    And I update the destination at subaccount level
    Then the destination update should be successful
    When I get subaccount destination "test-dest-update" with "PROVIDER_ONLY" access strategy
    Then the destination URL should be "https://updated.example.com"
    And I clean up the subaccount destination "test-dest-update"

  Scenario: Delete destination
    Given I have a destination named "test-dest-delete" of type "HTTP"
    And the destination has URL "https://delete.example.com"
    And the destination has authentication "NoAuthentication"
    When I create the destination at subaccount level
    Then the destination creation should be successful
    When I delete the subaccount destination "test-dest-delete"
    Then the destination deletion should be successful
    When I get subaccount destination "test-dest-delete" with "PROVIDER_ONLY" access strategy
    Then the destination should not be found

  Scenario: Create destination with network failure
    Given I have a destination named "test-dest-network-fail" of type "HTTP"
    And the destination has URL "https://network-fail.example.com"
    And the destination service is configured with an unreachable endpoint
    When I attempt to create the destination at subaccount level
    Then the destination creation should fail with a network error

  Scenario: Get non-existent destination
    When I get instance destination "non-existent-destination"
    Then the destination should not be found

  Scenario: Get non-existent destination
    When I get subaccount destination "non-existent-destination" with "PROVIDER_ONLY" access strategy
    Then the destination should not be found

  # Scenario: Get destination using subscriber first strategy
  #   Given I use tenant "1776453780"
  #   When I get subaccount destination "subscriber-dest-test" with "SUBSCRIBER_FIRST" access strategy
  #   Then the destination should be retrieved successfully

  # Scenario: Get destination using subscriber only strategy
  #   Given I use tenant "1776453780"
  #   When I get subaccount destination "subscriber-dest-test" with "SUBSCRIBER_ONLY" access strategy
  #   Then the destination should be retrieved successfully

  # Scenario: Get destination using provider first strategy
  #   Given I use tenant "1776453780"
  #   When I get subaccount destination "subscriber-dest-test" with "PROVIDER_FIRST" access strategy
  #   Then the destination should be retrieved successfully

  # Scenario: Get destination using provider only strategy
  #   Given I use tenant "1776453780"
  #   When I get subaccount destination "subscriber-dest-test" with "PROVIDER_ONLY" access strategy
  #   Then the destination should not be found

  Scenario: Create and list instance destinations
    Given I have multiple instance destinations:
      | name             | type | url                      |
      | test-list-inst-1 | HTTP | https://api1.example.com |
      | test-list-inst-2 | HTTP | https://api2.example.com |
      | test-list-inst-3 | HTTP | https://api3.example.com |
    When I create all instance destinations
    Then all destination creations should be successful
    When I list instance destinations
    Then the list should contain at least 3 destinations
    And the destination "test-list-inst-1" should be in the list
    And the destination "test-list-inst-2" should be in the list
    And the destination "test-list-inst-3" should be in the list
    And I clean up all instance destinations

  # Scenario: Create and list subaccount destinations (provider access)
  #   Given I have multiple subaccount destinations:
  #     | name            | type | url                      |
  #     | test-list-sub-1 | HTTP | https://sub1.example.com |
  #     | test-list-sub-2 | HTTP | https://sub2.example.com |
  #   And I use tenant "1776453780"
  #   When I create all subaccount destinations
  #   Then all destination creations should be successful
  #   When I list subaccount destinations with "PROVIDER_FIRST" access strategy
  #   Then the list should contain at least 2 destinations
  #   And the destination "test-list-sub-1" should be in the list
  #   And the destination "test-list-sub-2" should be in the list
  #   When I list subaccount destinations with "PROVIDER_ONLY" access strategy
  #   Then the list should contain at least 2 destinations
  #   And the destination "test-list-sub-1" should be in the list
  #   And the destination "test-list-sub-2" should be in the list
  #   And I clean up all subaccount destinations

  Scenario: List destinations with name filter
    Given I have multiple instance destinations:
      | name               | type | url                         |
      | filter-test-dest-1 | HTTP | https://filter1.example.com |
      | filter-test-dest-2 | HTTP | https://filter2.example.com |
      | other-destination  | HTTP | https://other.example.com   |
    When I create all instance destinations
    Then all destination creations should be successful
    When I list instance destinations filtered by names "filter-test-dest-1,filter-test-dest-2"
    Then the list should contain exactly 2 destinations
    And the destination "filter-test-dest-1" should be in the list
    And the destination "filter-test-dest-2" should be in the list
    And the destination "other-destination" should not be in the list
    And I clean up all instance destinations

  # Scenario: List destinations using subscriber first strategy
  #   Given I use tenant "1776453780"
  #   When I list subaccount destinations with "SUBSCRIBER_FIRST" access strategy
  #   Then the destination "subscriber-dest-test" should be in the list

  # Scenario: List destinations using subscriber only strategy
  #   Given I use tenant "1776453780"
  #   When I list subaccount destinations with "SUBSCRIBER_ONLY" access strategy
  #   Then the destination "subscriber-dest-test" should be in the list

  # Scenario: List destinations using provider first strategy
  #   Given I use tenant "1776453780"
  #   When I list subaccount destinations with "PROVIDER_FIRST" access strategy
  #   Then the destination list should be retrieved successfully

  # Scenario: List destinations using provider only strategy
  #   Given I use tenant "1776453780"
  #   When I list subaccount destinations with "PROVIDER_ONLY" access strategy
  #   Then the destination "subscriber-dest-test" should not be in the list

  Scenario: List destinations with network failure
    Given the destination service is configured with an unreachable endpoint
    When I attempt to list instance destinations
    Then the list operation should fail with a network error

  Scenario: Create destination with missing required fields
    Given I have a destination with empty name
    When I attempt to create the destination at subaccount level
    Then the operation should fail with a validation error

  Scenario: Create destination with invalid authentication credentials
    Given I have a destination named "test-invalid-auth" of type "HTTP"
    And the destination has URL "https://invalid-auth.example.com"
    And the destination has authentication "BasicAuthentication"
    And the destination service returns authentication failure
    When I attempt to create the destination at subaccount level
    Then the operation should fail with an authentication error

  Scenario: Concurrent destination operations
    Given I have multiple destinations to create simultaneously
    When I perform concurrent destination creation operations
    Then all concurrent destination creations should be successful
    And the expected number of destinations should be created
    And I clean up all concurrent test destinations

  Scenario: Destination with custom properties
    Given I have a destination named "test-custom-props" of type "HTTP"
    And the destination has URL "https://custom.example.com"
    And the destination has property "CustomHeader1" with value "HeaderValue1"
    And the destination has property "CustomHeader2" with value "HeaderValue2"
    When I create the destination at subaccount level
    Then the destination creation should be successful
    When I get subaccount destination "test-custom-props" with "PROVIDER_ONLY" access strategy
    Then the destination should have property "CustomHeader1" with value "HeaderValue1"
    And the destination should have property "CustomHeader2" with value "HeaderValue2"
    And I clean up the subaccount destination "test-custom-props"

  # Scenario: Consume destination with v2 API - with both fragment and tenant
  #   Given I have a destination named "test-v2-full-options" of type "HTTP"
  #   And the destination has URL "https://multi-tenant-api.example.com"
  #   And the destination has authentication "NoAuthentication"
  #   And I have a fragment named "test-v2-full-fragment"
  #   And the fragment has property "CustomProperty" with value "FragmentValue"
  #   And I use tenant "1776453780"
  #   When I create the destination at instance level
  #   And I create the fragment at instance level
  #   Then the destination creation should be successful
  #   And the fragment creation should be successful
  #   When I consume the destination "test-v2-full-options" with fragment "test-v2-full-fragment" and tenant context
  #   Then the destination should be consumed successfully
  #   And I clean up the instance destination "test-v2-full-options"
  #   And I clean up the instance fragment "test-v2-full-fragment"

  Scenario: Manage labels for subaccount destination
    Given I have a destination named "test-dest-labels" of type "HTTP"
    And the destination has URL "https://labels.example.com"
    And the destination has authentication "NoAuthentication"
    When I create the destination at subaccount level
    Then the destination creation should be successful
    When I update labels on the destination "test-dest-labels" at subaccount level: key "env" values "prod"
    Then the destination label operation should be successful
    When I get labels for the destination "test-dest-labels" at subaccount level
    Then the destination should have label key "env" with value "prod"
    When I patch labels on the destination "test-dest-labels" at subaccount level with action "ADD": key "team" values "platform"
    Then the destination label operation should be successful
    When I get labels for the destination "test-dest-labels" at subaccount level
    Then the destination should have label key "team" with value "platform"
    And I clean up the subaccount destination "test-dest-labels"

  Scenario: List subaccount destinations filtered by label
    Given I have a destination named "test-dest-list-by-label" of type "HTTP"
    And the destination has URL "https://label-list.example.com"
    And the destination has authentication "NoAuthentication"
    When I create the destination at subaccount level
    Then the destination creation should be successful
    When I update labels on the destination "test-dest-list-by-label" at subaccount level: key "list-filter-env" values "prod"
    Then the destination label operation should be successful
    When I list subaccount destinations with "PROVIDER_ONLY" access strategy and label filter key "list-filter-env" values "prod"
    Then the destination list should be retrieved successfully
    And the destination "test-dest-list-by-label" should be in the list
    And I clean up the subaccount destination "test-dest-list-by-label"

  # ==================== SUBSCRIBER WRITE SCENARIOS ====================

  # Scenario: Create destination at subaccount level for subscriber
  #   Given I use tenant "1776453780"
  #   And I have a destination named "test-dest-sub-write" of type "HTTP"
  #   And the destination has URL "https://subscriber-write.example.com"
  #   And the destination has authentication "NoAuthentication"
  #   When I create the destination at subaccount level for subscriber
  #   Then the destination creation should be successful
  #   When I get subaccount destination "test-dest-sub-write" with "SUBSCRIBER_ONLY" access strategy
  #   Then the destination should be retrieved successfully
  #   And the destination URL should be "https://subscriber-write.example.com"

  # Scenario: Update destination at subaccount level for subscriber
  #   Given I use tenant "1776453780"
  #   And I have a destination named "test-dest-sub-update" of type "HTTP"
  #   And the destination has URL "https://subscriber-original.example.com"
  #   And the destination has authentication "NoAuthentication"
  #   When I create the destination at subaccount level for subscriber
  #   Then the destination creation should be successful
  #   When I update the destination URL to "https://subscriber-updated.example.com"
  #   And I update the destination at subaccount level for subscriber
  #   Then the destination update should be successful
  #   When I get subaccount destination "test-dest-sub-update" with "SUBSCRIBER_ONLY" access strategy
  #   Then the destination URL should be "https://subscriber-updated.example.com"

  # Scenario: Delete destination at subaccount level for subscriber
  #   Given I use tenant "1776453780"
  #   And I have a destination named "test-dest-sub-delete" of type "HTTP"
  #   And the destination has URL "https://subscriber-delete.example.com"
  #   And the destination has authentication "NoAuthentication"
  #   When I create the destination at subaccount level for subscriber
  #   Then the destination creation should be successful
  #   When I delete the subaccount destination "test-dest-sub-delete" for subscriber
  #   Then the destination deletion should be successful
  #   When I get subaccount destination "test-dest-sub-delete" with "SUBSCRIBER_ONLY" access strategy
  #   Then the destination should not be found

  # Scenario: Subscriber destination not visible in provider-only context
  #   Given I use tenant "1776453780"
  #   And I have a destination named "test-dest-sub-isolation" of type "HTTP"
  #   And the destination has URL "https://subscriber-isolation.example.com"
  #   And the destination has authentication "NoAuthentication"
  #   When I create the destination at subaccount level for subscriber
  #   Then the destination creation should be successful
  #   When I get subaccount destination "test-dest-sub-isolation" with "PROVIDER_ONLY" access strategy
  #   Then the destination should not be found
