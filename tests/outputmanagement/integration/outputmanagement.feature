# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company and Cloud SDK contributors
# SPDX-License-Identifier: Apache-2.0

Feature: Output Management Integration
  As a developer using the SDK
  I want to send output requests and email notifications
  So that I can trigger document generation and delivery through Output Management

  Background:
    Given an Output Management client

  # ==================== Basic Email Notification ====================

  Scenario: Send a simple email notification
    Given an email configuration with template key "TEST_NOTIFICATION"
    And a business document of type "com.sap.test.PurchaseOrder" with ID "PO-12345"
    And an output request for "com.sap.test.PurchaseOrder" with ID "PO-12345"
    When I submit the output request
    Then the request should be successful
    And the response should contain an output request ID
    And the response should not contain an error

  Scenario: Send email using simplified API
    When I send an email notification
    Then the request should be successful
    And the response should contain an output request ID
    And the output request ID should match pattern "UUID"

  # ==================== Email with Attachment ====================

  Scenario: Send email with form-generated PDF attachment
    Given an output request with form attachment
    When I submit the output request
    Then the request should be successful
    And the response should contain an output request ID
    And the response should not contain an error

  # ==================== Multiple Recipients ====================

  Scenario: Send email to multiple recipients
    Given an email configuration with template key "MULTI_RECIPIENT_TEST"
    And a business document of type "com.sap.test.Invoice" with ID "INV-001"
    And an output request for "com.sap.test.Invoice" with ID "INV-001"
    When I submit the output request
    Then the request should be successful
    And the response should contain an output request ID

  # ==================== Different Document Types ====================

  Scenario: Send output request for Purchase Order
    Given a business document of type "com.sap.procurement.PurchaseOrder" with ID "PO-98765"
    And an output request for "com.sap.procurement.PurchaseOrder" with ID "PO-98765"
    When I submit the output request
    Then the request should be successful
    And the response should contain an output request ID

  Scenario: Send output request for Invoice
    Given a business document of type "com.sap.finance.Invoice" with ID "INV-54321"
    And an output request for "com.sap.finance.Invoice" with ID "INV-54321"
    When I submit the output request
    Then the request should be successful
    And the response should contain an output request ID
