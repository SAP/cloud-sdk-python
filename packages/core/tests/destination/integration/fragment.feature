Feature: Destination Service Integration - Fragments
  As a developer using the SDK
  I want to manage destination fragments
  So that I can configure external system connections

  Background:
    Given the destination service is available
    And I have valid fragment clients

  Scenario: Create and read fragment
    Given I have a fragment named "test-fragment"
    And the fragment has property "fragmentProp1" with value "value1"
    And the fragment has property "fragmentProp2" with value "value2"
    When I create the fragment at subaccount level
    Then the fragment creation should be successful
    When I get subaccount fragment "test-fragment" with "PROVIDER_ONLY" access strategy
    Then the fragment should be retrieved successfully
    And the fragment should have property "fragmentProp1" with value "value1"
    And I clean up the subaccount fragment "test-fragment"

  Scenario: Update fragment
    Given I have a fragment named "test-fragment-update"
    And the fragment has property "propToUpdate" with value "original"
    When I create the fragment at subaccount level
    Then the fragment creation should be successful
    When I update the fragment property "propToUpdate" to "updated"
    And I update the fragment at subaccount level
    Then the fragment update should be successful
    When I get subaccount fragment "test-fragment-update" with "PROVIDER_ONLY" access strategy
    Then the fragment should have property "propToUpdate" with value "updated"
    And I clean up the subaccount fragment "test-fragment-update"

  Scenario: Delete fragment
    Given I have a fragment named "test-fragment-delete"
    And the fragment has property "deleteProp" with value "deleteValue"
    When I create the fragment at subaccount level
    Then the fragment creation should be successful
    When I delete the subaccount fragment "test-fragment-delete"
    Then the fragment deletion should be successful
    When I get subaccount fragment "test-fragment-delete" with "PROVIDER_ONLY" access strategy
    Then the fragment should not be found

  Scenario: Get non-existent instance fragment
    When I get instance fragment "non-existent-fragment"
    Then the fragment should not be found

  Scenario: Get non-existent subaccount fragment
    When I get subaccount fragment "non-existent-fragment" with "PROVIDER_ONLY" access strategy
    Then the fragment should not be found

  Scenario: Get fragment using subscriber first strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I get subaccount fragment "fragment-dest-test" with "SUBSCRIBER_FIRST" access strategy
    Then the fragment should be retrieved successfully

  Scenario: Get fragment using subscriber only strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I get subaccount fragment "fragment-dest-test" with "SUBSCRIBER_ONLY" access strategy
    Then the fragment should be retrieved successfully

  Scenario: Get fragment using provider first strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I get subaccount fragment "fragment-dest-test" with "PROVIDER_FIRST" access strategy
    Then the fragment should be retrieved successfully

  Scenario: Get fragment using provider only strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I get subaccount fragment "fragment-dest-test" with "PROVIDER_ONLY" access strategy
    Then the fragment should not be found

  Scenario: Create and list instance fragments
    Given I have multiple subaccount fragments:
      | name             | property1 | value1 |
      | test-frag-list-1 | prop1     | val1   |
      | test-frag-list-2 | prop2     | val2   |
    And I use tenant "app-foundation-dev-subscriber"
    When I create all instance fragments
    Then all fragment creations should be successful
    When I list instance fragments
    Then the fragment list should contain at least 2 fragments
    And the fragment "test-frag-list-1" should be in the list
    And the fragment "test-frag-list-2" should be in the list
    And I clean up all subaccount fragments

  Scenario: Create and list subaccount fragments (provider access)
    Given I have multiple subaccount fragments:
      | name             | property1 | value1 |
      | test-frag-list-1 | prop1     | val1   |
      | test-frag-list-2 | prop2     | val2   |
    And I use tenant "app-foundation-dev-subscriber"
    When I create all subaccount fragments
    Then all fragment creations should be successful
    When I list subaccount fragments with "PROVIDER_FIRST" access strategy
    Then the fragment list should contain at least 2 fragments
    And the fragment "test-frag-list-1" should be in the list
    And the fragment "test-frag-list-2" should be in the list
    When I list subaccount fragments with "PROVIDER_ONLY" access strategy
    Then the fragment list should contain at least 2 fragments
    And the fragment "test-frag-list-1" should be in the list
    And the fragment "test-frag-list-2" should be in the list
    And I clean up all subaccount fragments

  Scenario: List fragments using subscriber first strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I list subaccount fragments with "SUBSCRIBER_FIRST" access strategy
    Then the fragment "fragment-dest-test" should be in the list

  Scenario: List fragments using subscriber only strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I list subaccount fragments with "SUBSCRIBER_ONLY" access strategy
    Then the fragment "fragment-dest-test" should be in the list

  Scenario: List fragments using provider first strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I list subaccount fragments with "PROVIDER_FIRST" access strategy
    Then the fragment list should be retrieved successfully

  Scenario: List fragments using provider only strategy
    Given I use tenant "app-foundation-dev-subscriber"
    When I list subaccount fragments with "PROVIDER_ONLY" access strategy
    Then the fragment "fragment-dest-test" should not be in the list
