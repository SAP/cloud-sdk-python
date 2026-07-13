# SAP Cloud SDK for Python - Output Management Service User Guide

## Overview

The Output Management Service provides a simplified way to send emails through SAP Ariba Output Service. This guide covers the unified `OutputManagementClient` which offers four main methods for sending notification emails with optional attachments using ANS (Ariba Notification Service) templates.

## Installation

```bash
# Using uv (recommended)
uv add sap-cloud-sdk

# Using pip
pip install sap-cloud-sdk
```

See further information about installation in the [main documentation](/README.md#installation).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Client Methods](#client-methods)
4. [Basic Email Sending](#basic-email-sending)
5. [Email with DMS Attachments](#email-with-dms-attachments)
6. [Advanced Usage](#advanced-usage)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [API Reference](#api-reference)

## Prerequisites

### Required Setup

1. **SAP BTP Destination**: Configure a destination in SAP BTP Destination Service pointing to your Output Management service
2. **ANS Template**: Create notification templates in Ariba Notification Service (ANS)
3. **Python Environment**: Python 3.11 or higher
4. **SAP Cloud SDK**: Install the SAP Cloud SDK for Python

```bash
pip install sap-cloud-sdk
```

### Destination Configuration

Your destination should be configured with:
- **Name**: e.g., `ARIBA_OUTPUT_SERVICE`
- **Type**: HTTP
- **URL**: Your Output Management service endpoint
- **Authentication**: OAuth2 with mTLS (client certificate)
- **Properties**: Include OAuth token service URL and certificate configuration

## Quick Start

Here's the simplest way to send an email:

```python
from sap_cloud_sdk.outputmanagement import create_client

# Create client using the factory function
client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

# Send email directly
response = client.send_email(
    notification_template_key="PO_APPROVAL_NOTIFICATION",
    to=["finance@company.com"],
    business_document={
        "PurchaseOrder": {
            "orderId": "PO-12345",
            "vendor": "ACME Corp",
            "total": 1500.00
        }
    }
)

# Check the result
if response.error:
    print(f"Failed to send email: {response.error.message}")
else:
    print(f"Email sent successfully! Request ID: {response.outputRequestId}")
```

## Client Methods

The `OutputManagementClient` provides four main methods:

### 1. `send_email()` - Direct Email Sending
Send an email directly with a single method call. This is the most convenient method for simple use cases.

**Basic Example:**
```python
response = client.send_email(
    notification_template_key="TEMPLATE_KEY",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    cc=["manager@example.com"],  # Optional
    template_language="en"  # Optional, default: "en"
)
```

**Example with Attachments:**
```python
response = client.send_email(
    notification_template_key="INVOICE_NOTIFICATION",
    to=["customer@example.com"],
    business_document={
        "Invoice": {
            "invoiceNumber": "INV-2024-001",
            "amount": 5000.00
        }
    },
    cc=["accounting@company.com"],
    template_language="en",
    attachment_urls=[
        "https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
        "https://dms.example.com/browser/root?objectId=67890&cmisselector=content"
    ]
)
```

### 2. `create_output_request()` - Create Request Object
Create an `OutputRequest` object without sending it. Useful when you need to inspect or modify the request before sending.

```python
output_request = client.create_output_request(
    notification_template_key="TEMPLATE_KEY",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    cc=["manager@example.com"],  # Optional
    template_language="en",  # Optional
    attachment_urls=["https://dms.example.com/..."]  # Optional
)

# Inspect or modify the request
print(f"Request type: {output_request.type}")

# Send it later
response = client.send_output_request(output_request)
```

### 3. `send_output_request()` - Send Pre-configured Request
Send a pre-configured `OutputRequest` object.

```python
output_request = client.create_output_request(...)
response = client.send_output_request(output_request)
```

### 4. `send_email_with_mcp()` - MCP Integration (Async)
Send emails via MCP (Model Context Protocol) server integration. This is an async method for advanced integration scenarios.

**Basic Example:**
```python
response = await client.send_email_with_mcp(
    tool_name="sendEmail",
    notification_template_key="TEMPLATE_KEY",
    to_emails=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    mcp_tool=mcp_tool_instance
)
```

**Example with Attachments:**
```python
response = await client.send_email_with_mcp(
    tool_name="sendEmail",
    notification_template_key="CONTRACT_NOTIFICATION",
    to_emails=["legal@company.com"],
    business_document={
        "Contract": {
            "contractId": "CNT-2024-100",
            "partyName": "Partner Corp"
        }
    },
    cc_email="manager@company.com",
    attachment_urls=[
        "https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
        "https://dms.example.com/browser/root?objectId=67890&cmisselector=content"
    ],
    mcp_tool=mcp_tool_instance
)
```

## Basic Email Sending

### Simple Notification Email

Send a notification email using an ANS template:

```python
from sap_cloud_sdk.outputmanagement import create_client

# Create client
client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

# Send email
response = client.send_email(
    notification_template_key="ORDER_CONFIRMATION",
    to=["customer@example.com"],
    business_document={
        "Order": {
            "orderId": "ORD-789",
            "customerName": "John Doe",
            "orderDate": "2024-01-15",
            "totalAmount": 2500.00
        }
    }
)

if response.error:
    print(f"Error: {response.error.message}")
else:
    print(f"Success! Request ID: {response.outputRequestId}")
```

### Email with Multiple Recipients

Send to multiple recipients with CC:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="INVOICE_NOTIFICATION",
    to=["customer@example.com", "billing@example.com"],
    cc=["manager@example.com", "audit@example.com"],
    business_document={
        "Invoice": {
            "invoiceNumber": "INV-2024-001",
            "amount": 5000.00,
            "dueDate": "2024-02-15"
        }
    }
)
```

### Email with Custom Language

Specify the template language:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="WELCOME_EMAIL",
    to=["user@example.com"],
    business_document={
        "User": {
            "userId": "U12345",
            "name": "Jane Smith"
        }
    },
    template_language="de"  # German template
)
```

## Email with DMS Attachments

### Single DMS Attachment

Attach a pre-generated document from DMS (Document Management Service):

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="CONTRACT_NOTIFICATION",
    to=["legal@company.com"],
    business_document={
        "Contract": {
            "contractId": "CNT-2024-100",
            "partyName": "Partner Corp"
        }
    },
    attachment_urls=[
        "https://dms.example.com/browser/root?objectId=12345&cmisselector=content"
    ]
)
```

### Multiple DMS Attachments

Attach multiple documents from DMS:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="REPORT_PACKAGE",
    to=["management@company.com"],
    business_document={
        "Report": {
            "reportId": "RPT-Q1-2024",
            "quarter": "Q1",
            "year": 2024
        }
    },
    attachment_urls=[
        "https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
        "https://dms.example.com/browser/root?objectId=67890&cmisselector=content",
        "https://dms.example.com/browser/root?objectId=11111&cmisselector=content"
    ]
)
```

## Advanced Usage

### Using the Factory Function

The recommended way to create a client is using the `create_client()` factory function. This function supports configuration via environment variables or explicit parameters:

```python
from sap_cloud_sdk.outputmanagement import create_client

# Option 1: Using environment variables
# Set CLOUD_SDK_OMS_DESTINATION_NAME, CLOUD_SDK_OMS_ACCESS_STRATEGY, CLOUD_SDK_OMS_INSTANCE
client = create_client()

# Option 2: With explicit parameters
client = create_client(
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="PROVIDER_ONLY",
    instance="default"
)
```

### Using Different Access Strategies

Control how the destination is accessed:

```python
from sap_cloud_sdk.outputmanagement import create_client

# Provider-only access (default)
client = create_client(
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="PROVIDER_ONLY"
)

# Subscriber-only access
client = create_client(
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="SUBSCRIBER_ONLY"
)
```

### Using Custom Destination Instance

Specify a custom destination service instance:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(
    destination_name="ARIBA_OUTPUT_SERVICE",
    instance="my-custom-instance"
)
```

### Two-Step Approach: Create Then Send

For more control, create the output request object separately:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

# Step 1: Create the output request
output_request = client.create_output_request(
    notification_template_key="CUSTOM_NOTIFICATION",
    to=["recipient@example.com"],
    business_document={
        "CustomDocument": {
            "id": "DOC-456",
            "type": "Important"
        }
    },
    cc=["supervisor@example.com"],
    template_language="en",
    attachment_urls=["https://dms.example.com/browser/root?objectId=999&cmisselector=content"]
)

# Step 2: Inspect or modify the request if needed
print(f"Request source: {output_request.source}")
print(f"Request type: {output_request.type}")

# Step 3: Send the request
response = client.send_output_request(output_request)
```

## Error Handling

### Basic Error Handling

Always check for errors in the response:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}}
)

if response.error:
    print(f"Error Code: {response.error.code}")
    print(f"Error Message: {response.error.message}")
else:
    print(f"Success! Request ID: {response.outputRequestId}")
```

### Handling Validation Errors

Validation errors occur before the request is sent:

```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="",  # Invalid: empty template key
    to=[],  # Invalid: no recipients
    business_document={}  # Invalid: empty document
)

if response.error:
    if response.error.code == "INVALID_REQUEST":
        print(f"Validation failed: {response.error.message}")
    else:
        print(f"Request failed: {response.error.message}")
```

### Handling Network and Authentication Errors

Handle network and authentication errors:

```python
from sap_cloud_sdk.outputmanagement import create_client

try:
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    response = client.send_email(
        notification_template_key="NOTIFICATION",
        to=["user@example.com"],
        business_document={"Document": {"id": "123"}}
    )

    if response.error:
        error_code = response.error.code

        if error_code == "AUTHENTICATION_FAILED":
            print("Authentication failed. Check your destination configuration.")
        elif error_code == "NETWORK_ERROR":
            print("Network error. Check connectivity to the service.")
        elif error_code == "SERVICE_UNAVAILABLE":
            print("Service temporarily unavailable. Please retry.")
        else:
            print(f"Error: {response.error.message}")

except Exception as e:
    print(f"Fatal error: {str(e)}")
```

## Best Practices

### 1. Reuse the Client

Create the client once and reuse it:

```python
from sap_cloud_sdk.outputmanagement import create_client

# Good: Create once and reuse
client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

for order in orders:
    response = client.send_email(
        notification_template_key="ORDER_CONFIRMATION",
        to=[order.customer_email],
        business_document={"Order": order.to_dict()}
    )

    if response.error:
        print(f"Failed to send email for order {order.id}: {response.error.message}")
    else:
        print(f"Email sent for order {order.id}, Request ID: {response.outputRequestId}")
```

### 2. Validate Input Before Sending

Validate your data before calling the API:

```python
from sap_cloud_sdk.outputmanagement import create_client

def send_order_confirmation(order):
    # Validate input
    if not order.customer_email:
        raise ValueError("Customer email is required")

    if not order.order_id:
        raise ValueError("Order ID is required")

    # Create client and send
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    response = client.send_email(
        notification_template_key="ORDER_CONFIRMATION",
        to=[order.customer_email],
        business_document={
            "Order": {
                "orderId": order.order_id,
                "total": order.total
            }
        }
    )

    return response
```

### 3. Use Meaningful Business Document IDs

Ensure your business documents have identifiable IDs:

```python
# Good: Clear, unique ID
business_document = {
    "Invoice": {
        "invoiceNumber": "INV-2024-001",  # Clear identifier
        "customerId": "CUST-12345",
        "amount": 1000.00
    }
}

# Avoid: Generic or missing IDs
business_document = {
    "Invoice": {
        "id": "123",  # Too generic
        "amount": 1000.00
    }
}
```

### 4. Handle Errors Gracefully

Always handle errors and provide meaningful feedback:

```python
from sap_cloud_sdk.outputmanagement import create_client
import time

def send_notification_with_retry(template_key, recipients, document, max_retries=3):
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    for attempt in range(max_retries):
        try:
            response = client.send_email(
                notification_template_key=template_key,
                to=recipients,
                business_document=document
            )

            if response.error:
                if response.error.code in ["NETWORK_ERROR", "SERVICE_UNAVAILABLE"]:
                    if attempt < max_retries - 1:
                        print(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue

                print(f"Failed to send email: {response.error.message}")
                return None

            return response.outputRequestId

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error occurred, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)
                continue
            raise

    return None
```

### 5. Log Request IDs

Always log the request ID for tracking:

```python
import logging
from sap_cloud_sdk.outputmanagement import create_client

logger = logging.getLogger(__name__)

client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}}
)

if response.error:
    logger.error(f"Email send failed: {response.error.message}")
else:
    logger.info(f"Email sent successfully. Request ID: {response.outputRequestId}")
    # Store request ID for tracking
    # save_request_id(response.outputRequestId)
```

## API Reference

### create_client()

Factory function to create an Output Management client.

**Parameters:**

- `destination_name` (str, optional): Name of the destination. If not provided, reads from `CLOUD_SDK_OMS_DESTINATION_NAME` environment variable
- `access_strategy` (str, optional): Destination access strategy ("PROVIDER_ONLY" or "SUBSCRIBER_ONLY"). If not provided, reads from `CLOUD_SDK_OMS_ACCESS_STRATEGY` or defaults to "PROVIDER_ONLY"
- `instance` (str, optional): Destination service instance name. If not provided, reads from `CLOUD_SDK_OMS_INSTANCE` or defaults to "default"

**Returns:**

`OutputManagementClient` instance

**Example:**

```python
from sap_cloud_sdk.outputmanagement import create_client

# Using explicit parameters
client = create_client(
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="PROVIDER_ONLY",
    instance="default"
)

# Using environment variables
client = create_client()
```

### OutputManagementClient

#### `send_email()`

Send an email directly using the Output Management service.

**Parameters:**

- `notification_template_key` (str, required): ANS template identifier
- `to` (List[str], required): List of recipient email addresses
- `business_document` (Dict[str, Any], required): Business document as a dictionary
- `cc` (List[str], optional): List of CC email addresses
- `template_language` (str, optional): ISO language code (default: "en")
- `attachment_urls` (List[str], optional): List of DMS URLs for attachments

**Returns:**

`OutputResponse` containing the request ID if successful, or error details

**Example:**

```python
response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    cc=["manager@example.com"],
    template_language="en",
    attachment_urls=["https://dms.example.com/..."]
)
```

#### `create_output_request()`

Create an OutputRequest object without sending it.

**Parameters:**

- `notification_template_key` (str, required): ANS template identifier
- `to` (List[str], required): List of recipient email addresses
- `business_document` (Dict[str, Any], required): Business document as a dictionary
- `cc` (List[str], optional): List of CC email addresses
- `template_language` (str, optional): ISO language code (default: "en")
- `attachment_urls` (List[str], optional): List of DMS URLs for attachments

**Returns:**

`OutputRequest` object ready to be sent

**Example:**

```python
output_request = client.create_output_request(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    cc=["manager@example.com"]
)
```

#### `send_output_request()`

Send a pre-configured output request to the Output Management service.

**Parameters:**

- `output_request` (OutputRequest, required): The output request to submit

**Returns:**

`OutputResponse` containing the request ID if successful, or error details

**Example:**

```python
output_request = client.create_output_request(...)
response = client.send_output_request(output_request)
```

#### `send_email_with_mcp()` (Async)

Send an email via MCP server integration.

**Parameters:**

- `tool_name` (str, required): Name of the MCP tool to invoke
- `notification_template_key` (str, required): ANS template identifier
- `to_emails` (List[str], required): List of recipient email addresses
- `business_document` (Dict[str, Any], required): Business document as a dictionary
- `cc_email` (str, optional): CC email address
- `attachment_urls` (List[str], optional): List of DMS URLs for attachments
- `mcp_tool` (Any, required): MCP tool instance
- `sender_provider_subaccount_id` (str, optional): Sender provider subaccount ID

**Returns:**

Response from the MCP tool

**Example:**

```python
response = await client.send_email_with_mcp(
    tool_name="sendEmail",
    notification_template_key="NOTIFICATION",
    to_emails=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    mcp_tool=mcp_tool_instance
)
```

## Common Use Cases

### Use Case 1: Order Confirmation

```python
from sap_cloud_sdk.outputmanagement import create_client

def send_order_confirmation(order):
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    response = client.send_email(
        notification_template_key="ORDER_CONFIRMATION",
        to=[order.customer_email],
        cc=[order.sales_rep_email],
        business_document={
            "Order": {
                "orderId": order.id,
                "orderDate": order.date.isoformat(),
                "customerName": order.customer_name,
                "totalAmount": float(order.total),
                "items": [
                    {
                        "productName": item.product_name,
                        "quantity": item.quantity,
                        "price": float(item.price)
                    }
                    for item in order.items
                ]
            }
        }
    )

    return response
```

### Use Case 2: Invoice with PDF Attachment

```python
from sap_cloud_sdk.outputmanagement import create_client

def send_invoice_with_pdf(invoice, pdf_dms_url):
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    response = client.send_email(
        notification_template_key="INVOICE_WITH_PDF",
        to=[invoice.customer_email],
        cc=["accounting@company.com"],
        business_document={
            "Invoice": {
                "invoiceNumber": invoice.number,
                "invoiceDate": invoice.date.isoformat(),
                "dueDate": invoice.due_date.isoformat(),
                "amount": float(invoice.amount),
                "currency": invoice.currency
            }
        },
        attachment_urls=[pdf_dms_url]
    )

    return response
```

### Use Case 3: Bulk Notification

```python
from sap_cloud_sdk.outputmanagement import create_client

def send_bulk_notification(recipients, notification_data):
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    response = client.send_email(
        notification_template_key="BULK_NOTIFICATION",
        to=recipients,
        business_document={
            "Notification": {
                "notificationId": notification_data["id"],
                "title": notification_data["title"],
                "message": notification_data["message"],
                "timestamp": notification_data["timestamp"]
            }
        }
    )

    return response
```

## Troubleshooting

### Issue: "Destination not found"

**Solution:** Verify the destination name and ensure it exists in your BTP subaccount:

```python
# Check destination name matches exactly
destination_name = "ARIBA_OUTPUT_SERVICE"  # Case-sensitive
```

### Issue: "Authentication failed"

**Solution:** Verify your destination has proper OAuth2 configuration with mTLS:
- Check token service URL
- Verify client certificate is uploaded to Destination Service
- Ensure certificate password is correct

### Issue: "Template not found"

**Solution:** Verify the ANS template key exists:

```python
# Use exact template key from ANS
notification_template_key = "PO_APPROVAL_NOTIFICATION"  # Must match ANS
```

### Issue: "Invalid email address"

**Solution:** Ensure email addresses are properly formatted:

```python
# Good
to = ["user@example.com", "admin@example.com"]

# Bad
to = ["invalid-email", "user@"]
```

## Exception Handling

The SDK provides specific exception classes for different error scenarios:

```python
from sap_cloud_sdk.outputmanagement import (
    create_client,
    OutputManagementException,
    AuthenticationException,
    ValidationException,
    NetworkException,
    DestinationNotFoundException,
    DestinationAccessException
)

try:
    client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

    response = client.send_email(
        notification_template_key="NOTIFICATION",
        to=["user@example.com"],
        business_document={"Document": {"id": "123"}}
    )

    if response.error:
        print(f"Error: {response.error.message}")

except ValidationException as e:
    print(f"Validation error: {e.message}")
except AuthenticationException as e:
    print(f"Authentication failed: {e.message}")
except DestinationNotFoundException as e:
    print(f"Destination not found: {e.message}")
except NetworkException as e:
    print(f"Network error: {e.message}")
except OutputManagementException as e:
    print(f"General error: {e.message}")
```

## Environment Variables

The SDK supports the following environment variables for configuration:

- `CLOUD_SDK_OMS_DESTINATION_NAME`: Default destination name
- `CLOUD_SDK_OMS_ACCESS_STRATEGY`: Default access strategy (PROVIDER_ONLY or SUBSCRIBER_ONLY)
- `CLOUD_SDK_OMS_INSTANCE`: Default destination service instance name
- `APPFND_CONHOS_SUBACCOUNTID`: Sender provider subaccount ID for multi-tenancy scenarios

Example:
```bash
export CLOUD_SDK_OMS_DESTINATION_NAME="ARIBA_OUTPUT_SERVICE"
export CLOUD_SDK_OMS_ACCESS_STRATEGY="PROVIDER_ONLY"
export CLOUD_SDK_OMS_INSTANCE="default"
```

Then use the factory function without parameters:
```python
from sap_cloud_sdk.outputmanagement import create_client

client = create_client()  # Uses environment variables
```

## Additional Resources

- [SAP Ariba Output Management Documentation](https://help.sap.com/docs/ariba)
- [SAP BTP Destination Service](https://help.sap.com/docs/connectivity)
- [SAP Cloud SDK for Python](https://github.com/SAP/cloud-sdk-python)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the API reference
3. Consult SAP support channels
4. Report bugs via GitHub issues

---

**Version:** 3.0.0
**Last Updated:** 2026-06-23
