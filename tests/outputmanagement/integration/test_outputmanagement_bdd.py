# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company and Cloud SDK contributors
# SPDX-License-Identifier: Apache-2.0
"""BDD step definitions for Output Management integration tests."""

import logging
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sap_cloud_sdk.outputmanagement import (
    AttachmentConfig,
    Channel,
    EmailConfiguration,
    FormConfiguration,
    OutputManagementInfo,
    OutputRequest,
    OutputRequestData,
)

logger = logging.getLogger(__name__)

# Load all scenarios from the feature file
scenarios(str(Path(__file__).parent / "outputmanagement.feature"))


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def context():
    """Shared context for BDD scenarios."""
    return {}


# ============================================================================
# Background Steps
# ============================================================================


@given("an Output Management client")
def output_management_client_available(output_management_client, context):
    """Store the Output Management client in context."""
    context["client"] = output_management_client
    logger.info("Output Management client initialized")


# ============================================================================
# Given Steps - Setup
# ============================================================================


@given(parsers.parse('an email configuration with template key "{template_key}"'))
def create_email_configuration(context, template_key):
    """Create an email configuration."""
    context["email_config"] = EmailConfiguration(
        emailNotificationTemplateKey=template_key,
        emailTemplateLanguage="en",
        to=["test@example.com"],
    )
    logger.info(f"Created email configuration with template key: {template_key}")


@given(parsers.parse('a business document of type "{doc_type}" with ID "{doc_id}"'))
def create_business_document(context, doc_type, doc_id):
    """Create a business document."""
    context["business_document"] = {
        "TestDocument": {
            "id": doc_id,
            "type": doc_type,
            "content": "Test content for integration testing",
        }
    }
    logger.info(f"Created business document: type={doc_type}, id={doc_id}")


@given(parsers.parse('an output request for "{doc_type}" with ID "{doc_id}"'))
def create_output_request(context, doc_type, doc_id):
    """Create an output request."""
    email_config = context.get("email_config")
    business_doc = context.get("business_document")

    if not email_config:
        email_config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["test@example.com"],
        )

    if not business_doc:
        business_doc = {
            "TestDocument": {
                "id": doc_id,
                "type": doc_type,
            }
        }

    output_mgmt_info = OutputManagementInfo(
        businessDocumentType=doc_type,
        businessDocumentId=doc_id,
        channels=[Channel.INTERNAL_EMAIL],
        emailConfiguration=email_config,
    )

    data = OutputRequestData(
        OutputManagement=output_mgmt_info,
        BusinessDocument=business_doc,
    )

    context["output_request"] = OutputRequest(
        source=f"/region/sap/{doc_type}",
        type=f"{doc_type}.Created.v1.notification",
        data=data,
    )
    logger.info(f"Created output request for {doc_type} with ID {doc_id}")


@given("an output request with form attachment")
def create_output_request_with_attachment(context):
    """Create an output request with form attachment."""
    form_config = FormConfiguration(
        form_id="TEST_FORM_ID",
        formName="TestForm",  # Required field
        formTemplateName="TEST_TEMPLATE",  # Required field
        formLanguage="en",  # Required field
        fileFormat="PDF",  # Required field
        form_data={"field1": "value1"},
    )

    attachment = AttachmentConfig(formConfiguration=form_config)

    email_config = EmailConfiguration(
        emailNotificationTemplateKey="TEST_TEMPLATE",
        emailTemplateLanguage="en",
        to=["test@example.com"],
        attachment=attachment,
    )

    output_mgmt_info = OutputManagementInfo(
        businessDocumentType="com.sap.test.Document",
        businessDocumentId="TEST-001",
        channels=[Channel.INTERNAL_EMAIL],
        emailConfiguration=email_config,
    )

    business_doc = {
        "TestDocument": {
            "id": "TEST-001",
            "content": "Test document with attachment",
        }
    }

    data = OutputRequestData(
        OutputManagement=output_mgmt_info,
        BusinessDocument=business_doc,
    )

    context["output_request"] = OutputRequest(
        source="/region/sap/Document",
        type="com.sap.test.Document.Created.v1.notification",
        data=data,
    )
    logger.info("Created output request with form attachment")


# ============================================================================
# When Steps - Actions
# ============================================================================


@when("I submit the output request")
def submit_output_request(context):
    """Submit the output request."""
    client = context["client"]
    output_request = context["output_request"]

    try:
        response = client.send_output_request(output_request)
        context["response"] = response
        context["error"] = None
        logger.info(
            f"Output request submitted successfully: {response.output_request_id}"
        )
    except Exception as e:
        context["error"] = e
        context["response"] = None
        logger.error(f"Failed to submit output request: {e}")


@when("I send an email notification")
def send_email_notification(context):
    """Send an email notification using the simplified API."""
    client = context["client"]

    try:
        response = client.send_email(
            notification_template_key="TEST_TEMPLATE",
            to=["test@example.com"],
            business_document={
                "TestDocument": {
                    "id": "TEST-001",
                    "content": "Test notification",
                }
            },
        )
        context["response"] = response
        context["error"] = None
        logger.info(
            f"Email notification sent successfully: {response.output_request_id}"
        )
    except Exception as e:
        context["error"] = e
        context["response"] = None
        logger.error(f"Failed to send email notification: {e}")


# ============================================================================
# Then Steps - Assertions
# ============================================================================


@then("the request should be successful")
def request_successful(context):
    """Verify the request was successful."""
    error = context.get("error")
    response = context.get("response")

    assert error is None, f"Request failed with error: {error}"
    assert response is not None, "No response received"
    logger.info("Request completed successfully")


@then("the response should contain an output request ID")
def response_contains_request_id(context):
    """Verify the response contains an output request ID."""
    response = context["response"]
    assert response.output_request_id is not None, (
        "Response does not contain an output request ID"
    )
    assert len(response.output_request_id) > 0, "Output request ID is empty"
    logger.info(f"Response contains output request ID: {response.output_request_id}")


@then("the response should not contain an error")
def response_no_error(context):
    """Verify the response does not contain an error."""
    response = context["response"]
    assert response.error is None, f"Response contains error: {response.error}"
    logger.info("Response does not contain errors")


@then(parsers.parse('the output request ID should match pattern "{pattern}"'))
def verify_request_id_pattern(context, pattern):
    """Verify the output request ID matches a pattern."""
    response = context["response"]
    request_id = response.output_request_id

    # Pattern matching for Output Management service response format
    if pattern == "UUID":
        # Real service returns: _region_sap_TestDocument~<uuid>
        # Check it contains a UUID-like part (has dashes and ~)
        assert "~" in request_id or "-" in request_id, (
            f"Request ID does not contain UUID-like format: {request_id}"
        )
        assert len(request_id) > 0, "Request ID is empty"

    logger.info(f"Output request ID matches pattern {pattern}: {request_id}")


@then("the request should fail with validation error")
def request_fails_with_validation_error(context):
    """Verify the request failed with a validation error."""
    error = context.get("error")
    assert error is not None, "Expected validation error but request succeeded"
    logger.info(f"Request failed as expected with validation error: {error}")
