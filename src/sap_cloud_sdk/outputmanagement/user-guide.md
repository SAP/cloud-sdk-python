# SAP Cloud SDK for Python - Output Management Email Service User Guide

## Overview

The Output Management Email Service provides a simplified way to send emails through SAP Ariba Output Service. This guide focuses on the email sending functionality, which allows you to send notification emails with optional attachments using ANS (Ariba Notification Service) templates.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Basic Email Sending](#basic-email-sending)
4. [Email with DMS Attachments](#email-with-dms-attachments)
5. [Advanced Configuration](#advanced-configuration)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [API Reference](#api-reference)

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
from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient

# Initialize the email client
client = EmailClient()

# Send a simple notification email
response = client.send_email(
    notification_template_key="PO_APPROVAL_NOTIFICATION",
    to=["finance@company.com"],
    business_document={
        "PurchaseOrder": {
            "orderId": "PO-12345",
            "vendor": "ACME Corp",
            "total": 1500.00
        }
    },
    destination_name="ARIBA_OUTPUT_SERVICE"
)

# Check the result
if response.error:
    print(f"Failed to send email: {response.error.message}")
else:
    print(f"Email sent successfully! Request ID: {response.output_request_id}")
```

## Basic Email Sending

### Simple Notification Email

Send a notification email using an ANS template:

```python
from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient

client = EmailClient()

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
    },
    destination_name="ARIBA_OUTPUT_SERVICE"
)
```

### Email with Multiple Recipients

Send to multiple recipients with CC:

```python
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
    },
    destination_name="ARIBA_OUTPUT_SERVICE"
)
```

### Email with Custom Language

Specify the template language:

```python
response = client.send_email(
    notification_template_key="WELCOME_EMAIL",
    to=["user@example.com"],
    business_document={
        "User": {
            "userId": "U12345",
            "name": "Jane Smith"
        }
    },
    destination_name="ARIBA_OUTPUT_SERVICE",
    template_language="de"  # German template
)
```

## Email with DMS Attachments

### Single DMS Attachment

Attach a pre-generated document from DMS (Document Management Service):

```python
response = client.send_email(
    notification_template_key="CONTRACT_NOTIFICATION",
    to=["legal@company.com"],
    business_document={
        "Contract": {
            "contractId": "CNT-2024-100",
            "partyName": "Partner Corp"
        }
    },
    destination_name="ARIBA_OUTPUT_SERVICE",
    attachment_urls=[
        "https://dms.example.com/browser/root?objectId=12345&cmisselector=content"
    ]
)
```

### Multiple DMS Attachments

Attach multiple documents from DMS:

```python
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
    destination_name="ARIBA_OUTPUT_SERVICE",
    attachment_urls=[
        "https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
        "https://dms.example.com/browser/root?objectId=67890&cmisselector=content",
        "https://dms.example.com/browser/root?objectId=11111&cmisselector=content"
    ]
)
```

## Advanced Configuration

### Using Different Access Strategies

Control how the destination is accessed:

```python
# Provider-only access (default)
response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="PROVIDER_ONLY"
)

# Subscriber-only access
response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="SUBSCRIBER_ONLY"
)
```

### Using Custom Destination Instance

Specify a custom destination service instance:

```python
response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    destination_name="ARIBA_OUTPUT_SERVICE",
    instance="my-custom-instance"
)
```

### Creating Output Request Separately

For more control, create the output request object separately:

```python
from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient

client = EmailClient()

# Create the output request
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

# Inspect or modify the request if needed
print(f"Request source: {output_request.source}")
print(f"Request type: {output_request.type}")

# Send using the client provider
from sap_cloud_sdk.outputmanagement.client_provider import OutputManagementServiceClientProviderBuilder
from sap_cloud_sdk.outputmanagement.config.destination_credential_config import DestinationCredentialConfig

config = DestinationCredentialConfig(
    destination_name="ARIBA_OUTPUT_SERVICE",
    access_strategy="PROVIDER_ONLY"
)

provider = OutputManagementServiceClientProviderBuilder() \
    .with_destination_credentials(config) \
    .build()

oms_client = provider.get_client()
output_client = oms_client.get_output_requests_client()
response = output_client.send_output_request(output_request)
```

## Error Handling

### Basic Error Handling

Always check for errors in the response:

```python
response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    destination_name="ARIBA_OUTPUT_SERVICE"
)

if response.error:
    print(f"Error Code: {response.error.code}")
    print(f"Error Message: {response.error.message}")
    if response.error.details:
        print(f"Error Details: {response.error.details}")
else:
    print(f"Success! Request ID: {response.output_request_id}")
```

### Handling Validation Errors

Validation errors occur before the request is sent:

```python
try:
    response = client.send_email(
        notification_template_key="",  # Invalid: empty template key
        to=[],  # Invalid: no recipients
        business_document={},  # Invalid: empty document
        destination_name="ARIBA_OUTPUT_SERVICE"
    )
    
    if response.error:
        if response.error.code == "INVALID_REQUEST":
            print(f"Validation failed: {response.error.message}")
        else:
            print(f"Request failed: {response.error.message}")
            
except Exception as e:
    print(f"Unexpected error: {str(e)}")
```

### Handling Network Errors

Handle network and authentication errors:

```python
try:
    response = client.send_email(
        notification_template_key="NOTIFICATION",
        to=["user@example.com"],
        business_document={"Document": {"id": "123"}},
        destination_name="ARIBA_OUTPUT_SERVICE"
    )
    
    if response.error:
        error_code = response.error.code
        
        if error_code == "AUTHENTICATION_FAILED":
            print("Authentication failed. Check your destination configuration.")
        elif error_code == "DESTINATION_NOT_FOUND":
            print("Destination not found. Verify the destination name.")
        elif error_code == "NETWORK_ERROR":
            print("Network error. Check connectivity to the service.")
        else:
            print(f"Error: {response.error.message}")
            
except Exception as e:
    print(f"Fatal error: {str(e)}")
```

## Best Practices

### 1. Reuse the Email Client

Create the client once and reuse it:

```python
# Good: Create once
client = EmailClient()

for order in orders:
    response = client.send_email(
        notification_template_key="ORDER_CONFIRMATION",
        to=[order.customer_email],
        business_document={"Order": order.to_dict()},
        destination_name="ARIBA_OUTPUT_SERVICE"
    )
```

### 2. Validate Input Before Sending

Validate your data before calling the API:

```python
def send_order_confirmation(order):
    # Validate input
    if not order.customer_email:
        raise ValueError("Customer email is required")
    
    if not order.order_id:
        raise ValueError("Order ID is required")
    
    # Send email
    client = EmailClient()
    response = client.send_email(
        notification_template_key="ORDER_CONFIRMATION",
        to=[order.customer_email],
        business_document={
            "Order": {
                "orderId": order.order_id,
                "total": order.total
            }
        },
        destination_name="ARIBA_OUTPUT_SERVICE"
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
def send_notification_with_retry(template_key, recipients, document, max_retries=3):
    client = EmailClient()
    
    for attempt in range(max_retries):
        try:
            response = client.send_email(
                notification_template_key=template_key,
                to=recipients,
                business_document=document,
                destination_name="ARIBA_OUTPUT_SERVICE"
            )
            
            if response.error:
                if response.error.code in ["NETWORK_ERROR", "SERVICE_UNAVAILABLE"]:
                    if attempt < max_retries - 1:
                        print(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                        continue
                
                print(f"Failed to send email: {response.error.message}")
                return None
            
            return response.output_request_id
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error occurred, retrying... (attempt {attempt + 1}/{max_retries})")
                continue
            raise
    
    return None
```

### 5. Log Request IDs

Always log the request ID for tracking:

```python
import logging

logger = logging.getLogger(__name__)

response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    destination_name="ARIBA_OUTPUT_SERVICE"
)

if response.error:
    logger.error(f"Email send failed: {response.error.message}")
else:
    logger.info(f"Email sent successfully. Request ID: {response.output_request_id}")
    # Store request ID for tracking
    save_request_id(response.output_request_id)
```

## API Reference

### EmailClient

#### `send_email()`

Sends an email using the SAP Ariba Output Service.

**Parameters:**

- `notification_template_key` (str, required): ANS template identifier
- `to` (List[str], required): List of recipient email addresses
- `business_document` (Dict[str, Any], required): Business document as a dictionary
- `destination_name` (str, required): Name of the destination for authentication
- `cc` (List[str], optional): List of CC email addresses
- `template_language` (str, optional): ISO language code (default: "en")
- `access_strategy` (str, optional): "PROVIDER_ONLY" or "SUBSCRIBER_ONLY" (default: "PROVIDER_ONLY")
- `instance` (str, optional): Destination service instance name (default: "default")
- `attachment_urls` (List[str], optional): List of DMS URLs for attachments

**Returns:**

`OutputResponse` object with:
- `output_request_id` (str): Request ID if successful
- `error` (ErrorResponse): Error details if failed
  - `message` (str): Error message
  - `code` (str): Error code
  - `details` (Dict): Additional error details

**Example:**

```python
response = client.send_email(
    notification_template_key="NOTIFICATION",
    to=["user@example.com"],
    business_document={"Document": {"id": "123"}},
    destination_name="ARIBA_OUTPUT_SERVICE"
)
```

#### `create_output_request()`

Creates an OutputRequest object without sending it.

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

## Common Use Cases

### Use Case 1: Order Confirmation

```python
def send_order_confirmation(order):
    client = EmailClient()
    
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
        },
        destination_name="ARIBA_OUTPUT_SERVICE"
    )
    
    return response
```

### Use Case 2: Invoice with PDF Attachment

```python
def send_invoice_with_pdf(invoice, pdf_dms_url):
    client = EmailClient()
    
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
        destination_name="ARIBA_OUTPUT_SERVICE",
        attachment_urls=[pdf_dms_url]
    )
    
    return response
```

### Use Case 3: Bulk Notification

```python
def send_bulk_notification(recipients, notification_data):
    client = EmailClient()
    
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
        },
        destination_name="ARIBA_OUTPUT_SERVICE"
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

**Version:** 1.0.0  
**Last Updated:** 2024-01-15