# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Tests for EmailClient MCP integration."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient


class TestEmailClientMCP:
    """Test EmailClient MCP integration methods."""

    @pytest.fixture
    def email_client(self):
        """Create an EmailClient instance for testing."""
        return EmailClient()

    @pytest.fixture
    def sample_business_document(self):
        """Sample business document for testing."""
        return {
            "PurchaseOrder": {
                "orderId": "PO-12345",
                "vendor": "ACME Corp",
                "total": 1500.00,
                "items": [
                    {"product": "Widget A", "quantity": 10, "price": 100.00},
                    {"product": "Widget B", "quantity": 5, "price": 100.00}
                ]
            }
        }

    @pytest.fixture
    def mock_mcp_tool(self):
        """Create a mock MCP tool."""
        tool = Mock()
        tool.ainvoke = AsyncMock(return_value={"status": "success", "requestId": "req-123"})
        return tool

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_basic(self, email_client, sample_business_document, mock_mcp_tool):
        """Test basic MCP email sending."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        assert result["status"] == "success"
        assert result["requestId"] == "req-123"
        mock_mcp_tool.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_with_cc(self, email_client, sample_business_document, mock_mcp_tool):
        """Test MCP email sending with CC."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            cc_email="manager@company.com",
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify CC was included in the payload
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        assert "body" in call_args
        assert call_args["body"]["data"]["outputManagement"]["emailConfiguration"]["cc"] == ["manager@company.com"]

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_with_attachments(self, email_client, sample_business_document, mock_mcp_tool):
        """Test MCP email sending with attachments."""
        attachment_urls = [
            "https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
            "https://dms.example.com/browser/root?objectId=67890&cmisselector=content"
        ]

        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            attachment_urls=attachment_urls,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify attachments were included in the payload
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        assert "body" in call_args
        email_config = call_args["body"]["data"]["outputManagement"]["emailConfiguration"]
        assert "attachment" in email_config
        assert len(email_config["attachment"]["preGeneratedAttachments"]) == 2

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_traceparent_generated(self, email_client, sample_business_document, mock_mcp_tool):
        """Test that traceparent is generated correctly."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify traceparent format (W3C Trace Context)
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        assert "traceparent" in call_args
        traceparent = call_args["traceparent"]
        
        # Format: 00-{trace_id}-{parent_id}-01
        parts = traceparent.split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # version
        assert len(parts[1]) == 32  # trace_id (32 hex chars)
        assert len(parts[2]) == 16  # parent_id (16 hex chars)
        assert parts[3] == "01"  # trace-flags

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_sender_subaccount_from_param(self, email_client, sample_business_document, mock_mcp_tool):
        """Test sender_provider_subaccount_id from parameter."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool,
            sender_provider_subaccount_id="test-subaccount-123"
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify sender_provider_subaccount_id was included
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        assert "sender_provider_subaccount_id" in call_args
        assert call_args["sender_provider_subaccount_id"] == "test-subaccount-123"

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'APPFND_CONHOS_SUBACCOUNTID': 'env-subaccount-456'})
    async def test_send_email_with_mcp_sender_subaccount_from_env(self, email_client, sample_business_document, mock_mcp_tool):
        """Test sender_provider_subaccount_id from environment variable."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify sender_provider_subaccount_id from env was used
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        assert "sender_provider_subaccount_id" in call_args
        assert call_args["sender_provider_subaccount_id"] == "env-subaccount-456"

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_missing_tool_raises_error(self, email_client, sample_business_document):
        """Test that missing MCP tool raises ValueError."""
        with pytest.raises(ValueError, match="mcp_tool parameter is required"):
            await email_client.send_email_with_mcp(
                tool_name="send_output_request",
                notification_template_key="PO_APPROVAL_NOTIFICATION",
                to_emails=["finance@company.com"],
                business_document=sample_business_document,
                mcp_tool=None
            )

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_tool_failure(self, email_client, sample_business_document):
        """Test handling of MCP tool invocation failure."""
        mock_tool = Mock()
        mock_tool.ainvoke = AsyncMock(side_effect=Exception("MCP tool error"))

        with pytest.raises(Exception, match="MCP tool invocation failed"):
            await email_client.send_email_with_mcp(
                tool_name="send_output_request",
                notification_template_key="PO_APPROVAL_NOTIFICATION",
                to_emails=["finance@company.com"],
                business_document=sample_business_document,
                mcp_tool=mock_tool
            )

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_payload_structure(self, email_client, sample_business_document, mock_mcp_tool):
        """Test that the MCP payload has correct structure."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com", "accounting@company.com"],
            business_document=sample_business_document,
            cc_email="manager@company.com",
            mcp_tool=mock_mcp_tool,
            sender_provider_subaccount_id="test-subaccount"
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify complete payload structure
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        
        # Top-level keys
        assert "body" in call_args
        assert "traceparent" in call_args
        assert "sender_provider_subaccount_id" in call_args
        
        # Body structure (CloudEvents format)
        body = call_args["body"]
        assert "source" in body
        assert "type" in body
        assert "data" in body
        
        # Data structure
        data = body["data"]
        assert "outputManagement" in data
        assert "businessDocument" in data
        
        # Output management structure
        output_mgmt = data["outputManagement"]
        assert "businessDocumentType" in output_mgmt
        assert "businessDocumentId" in output_mgmt
        assert "channels" in output_mgmt
        assert "emailConfiguration" in output_mgmt
        
        # Email configuration
        email_config = output_mgmt["emailConfiguration"]
        assert email_config["to"] == ["finance@company.com", "accounting@company.com"]
        assert email_config["cc"] == ["manager@company.com"]
        assert email_config["emailNotificationTemplateKey"] == "PO_APPROVAL_NOTIFICATION"
        assert email_config["emailTemplateLanguage"] == "en"

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_multiple_recipients(self, email_client, sample_business_document, mock_mcp_tool):
        """Test MCP email sending with multiple recipients."""
        recipients = [
            "finance@company.com",
            "accounting@company.com",
            "manager@company.com"
        ]

        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=recipients,
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify all recipients were included
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        email_config = call_args["body"]["data"]["outputManagement"]["emailConfiguration"]
        assert len(email_config["to"]) == 3
        assert set(email_config["to"]) == set(recipients)

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_complex_business_document(self, email_client, mock_mcp_tool):
        """Test MCP email with complex nested business document."""
        complex_doc = {
            "Invoice": {
                "invoiceNumber": "INV-2024-001",
                "customer": {
                    "id": "CUST-123",
                    "name": "ACME Corporation",
                    "address": {
                        "street": "123 Main St",
                        "city": "New York",
                        "country": "USA"
                    }
                },
                "lineItems": [
                    {
                        "itemId": "ITEM-001",
                        "description": "Product A",
                        "quantity": 10,
                        "unitPrice": 100.00,
                        "total": 1000.00
                    },
                    {
                        "itemId": "ITEM-002",
                        "description": "Product B",
                        "quantity": 5,
                        "unitPrice": 200.00,
                        "total": 1000.00
                    }
                ],
                "subtotal": 2000.00,
                "tax": 200.00,
                "total": 2200.00
            }
        }

        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="INVOICE_NOTIFICATION",
            to_emails=["billing@customer.com"],
            business_document=complex_doc,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify business document was preserved
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        business_doc = call_args["body"]["data"]["businessDocument"]
        assert "Invoice" in business_doc
        assert business_doc["Invoice"]["invoiceNumber"] == "INV-2024-001"
        assert len(business_doc["Invoice"]["lineItems"]) == 2

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_unique_trace_ids(self, email_client, sample_business_document, mock_mcp_tool):
        """Test that each invocation generates unique trace IDs."""
        # Call the method twice
        await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        # Verify two calls were made
        assert mock_mcp_tool.ainvoke.call_count == 2
        
        # Get trace IDs from both calls
        call1_args = mock_mcp_tool.ainvoke.call_args_list[0][0][0]
        call2_args = mock_mcp_tool.ainvoke.call_args_list[1][0][0]
        
        traceparent1 = call1_args["traceparent"]
        traceparent2 = call2_args["traceparent"]
        
        # Verify they are different
        assert traceparent1 != traceparent2

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_no_optional_params(self, email_client, sample_business_document, mock_mcp_tool):
        """Test MCP email with only required parameters."""
        result = await email_client.send_email_with_mcp(
            tool_name="send_output_request",
            notification_template_key="PO_APPROVAL_NOTIFICATION",
            to_emails=["finance@company.com"],
            business_document=sample_business_document,
            mcp_tool=mock_mcp_tool
        )

        assert result is not None
        mock_mcp_tool.ainvoke.assert_called_once()
        
        # Verify optional fields are not present or None
        call_args = mock_mcp_tool.ainvoke.call_args[0][0]
        email_config = call_args["body"]["data"]["outputManagement"]["emailConfiguration"]
        
        # CC should not be present when not provided
        assert "cc" not in email_config or email_config.get("cc") is None
        
        # Attachment should not be present when not provided
        assert "attachment" not in email_config or email_config.get("attachment") is None