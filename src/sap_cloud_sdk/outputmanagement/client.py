"""Unified Output Management client."""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

from ._models import (
    OutputRequest,
    OutputRequestData,
    OutputManagementInfo,
    EmailConfiguration,
    OutputResponse,
    ErrorResponse,
    AttachmentConfig,
    PreGeneratedAttachment,
)
from .constants import Channel
from .utils import RequestValidator

logger = logging.getLogger(__name__)


class OutputManagementClient:
    """
    Unified client for Output Management operations.

    This client provides four main methods:
    1. send_email() - Send emails directly via Output Management API
    2. send_email_with_mcp() - Send emails via MCP server integration
    3. create_output_request() - Create an output request object
    4. send_output_request() - Send a pre-configured output request

    Usage:
        from sap_cloud_sdk.outputmanagement import create_client

        client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")

        # Send email
        response = client.send_email(
            notification_template_key="PO_NOTIFICATION",
            to=["user@example.com"],
            business_document={"PurchaseOrder": {"id": "PO-123"}}
        )
    """

    def __init__(self, service_client):
        """
        Initialize the Output Management client.

        Args:
            service_client: The underlying service client implementation
        """
        self._service_client = service_client

    @record_metrics(Module.OUTPUT_MANAGEMENT, Operation.OUTPUT_MANAGEMENT_SEND_EMAIL)
    def send_email(
        self,
        notification_template_key: str,
        to: List[str],
        business_document: Dict[str, Any],
        cc: Optional[List[str]] = None,
        template_language: Optional[str] = "en",
        attachment_urls: Optional[List[str]] = None,
    ) -> OutputResponse:
        """
        Send an email using the Output Management service.

        Args:
            notification_template_key: ANS template identifier
            to: List of recipient email addresses
            business_document: Business document as a dictionary
            cc: List of CC email addresses (optional)
            template_language: ISO language code (default: "en")
            attachment_urls: List of DMS URLs for attachments (optional)

        Returns:
            OutputResponse containing the request ID if successful, or error details

        Example:
            >>> from sap_cloud_sdk.outputmanagement import create_client
            >>> client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")
            >>> response = client.send_email(
            ...     notification_template_key="PO_NOTIFICATION",
            ...     to=["user@example.com"],
            ...     business_document={"PurchaseOrder": {"id": "PO-123"}}
            ... )
        """
        # Validate input parameters
        lang = template_language or "en"
        validation_error = RequestValidator.validate_email_parameters(
            notification_template_key=notification_template_key,
            to=to,
            business_document=business_document,
            template_language=lang,
            cc=cc,
        )
        if validation_error:
            return OutputResponse(
                outputRequestId=None,
                error=ErrorResponse(message=validation_error, code="INVALID_REQUEST"),
            )

        # Create the output request
        output_request = self.create_output_request(
            notification_template_key=notification_template_key,
            to=to,
            business_document=business_document,
            cc=cc,
            template_language=template_language,
            attachment_urls=attachment_urls,
        )

        # Send the output request
        return self.send_output_request(output_request)

    @record_metrics(
        Module.OUTPUT_MANAGEMENT, Operation.OUTPUT_MANAGEMENT_SEND_EMAIL_WITH_MCP
    )
    async def send_email_with_mcp(
        self,
        tool_name: str,
        notification_template_key: str,
        to_emails: List[str],
        business_document: Dict[str, Any],
        cc_email: Optional[str] = None,
        attachment_urls: Optional[List[str]] = None,
        mcp_tool: Any = None,
        sender_provider_subaccount_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an output request and invoke MCP tool with traceparent and sender_provider_subaccount_id.

        Args:
            tool_name: Name of the MCP tool to invoke
            notification_template_key: ANS template identifier
            to_emails: List of recipient email addresses
            business_document: Business document as a dictionary
            cc_email: CC email address (optional)
            attachment_urls: List of DMS URLs for attachments (optional)
            mcp_tool: MCP tool instance (required)
            sender_provider_subaccount_id: Sender provider subaccount ID (optional)

        Returns:
            Response from the MCP tool

        Example:
            >>> from sap_cloud_sdk.outputmanagement import create_client
            >>> client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")
            >>> response = await client.send_email_with_mcp(
            ...     tool_name="sendEmail",
            ...     notification_template_key="PO_NOTIFICATION",
            ...     to_emails=["user@example.com"],
            ...     business_document={"PurchaseOrder": {"id": "PO-123"}},
            ...     mcp_tool=mcp_tool_instance
            ... )
        """
        try:
            logger.info("Creating output request for MCP tool '%s'", tool_name)

            # Create the output request
            output_request = self.create_output_request(
                notification_template_key=notification_template_key,
                to=to_emails,
                business_document=business_document,
                cc=[cc_email] if cc_email else None,
                template_language="en",
                attachment_urls=attachment_urls,
            )

            logger.info("Output request created successfully")

            # Convert output request to dict for MCP payload
            payload = output_request.model_dump(by_alias=True, exclude_none=True)

            # Get sender_provider_subaccount_id from parameter or environment variable
            subaccount_id = sender_provider_subaccount_id or os.getenv(
                "APPFND_CONHOS_SUBACCOUNTID"
            )

            if not subaccount_id:
                logger.warning(
                    "sender_provider_subaccount_id not provided and APPFND_CONHOS_SUBACCOUNTID env var not set"
                )

            logger.info(
                "Invoking MCP tool '%s' with body, traceparent, and sender_provider_subaccount_id",
                tool_name,
            )

            # Generate traceparent for distributed tracing
            trace_id = uuid.uuid4().hex
            parent_id = uuid.uuid4().hex[:16]
            traceparent = f"00-{trace_id}-{parent_id}-01"

            # Prepare the invocation payload
            invocation_payload = {
                "body": payload,
                "traceparent": traceparent,
                "sender_provider_subaccount_id": subaccount_id,
            }

            logger.info(
                "MCP tool '%s' invocation payload: %s", tool_name, invocation_payload
            )

            # Validate that mcp_tool is provided
            if mcp_tool is None:
                raise ValueError("mcp_tool parameter is required")

            # Use ainvoke for async invocation
            result = await mcp_tool.ainvoke(invocation_payload)
            logger.info("MCP tool '%s' executed successfully", tool_name)
            logger.info("Result from MCP tool '%s': %s", tool_name, result)
            return result

        except Exception as e:
            logger.error("Failed to invoke MCP tool '%s': %s", tool_name, str(e))
            raise Exception(f"MCP tool invocation failed: {str(e)}") from e

    def create_output_request(
        self,
        notification_template_key: str,
        to: List[str],
        business_document: Dict[str, Any],
        cc: Optional[List[str]] = None,
        template_language: Optional[str] = "en",
        attachment_urls: Optional[List[str]] = None,
    ) -> OutputRequest:
        """
        Create an OutputRequest object from the provided parameters.

        Args:
            notification_template_key: ANS template identifier
            to: List of recipient email addresses
            business_document: Business document as a dictionary
            cc: List of CC email addresses (optional)
            template_language: ISO language code (default: "en")
            attachment_urls: List of DMS URLs for attachments (optional)

        Returns:
            OutputRequest object ready to be sent

        Example:
            >>> from sap_cloud_sdk.outputmanagement import create_client
            >>> client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")
            >>> output_request = client.create_output_request(
            ...     notification_template_key="PO_NOTIFICATION",
            ...     to=["user@example.com"],
            ...     business_document={"PurchaseOrder": {"id": "PO-123"}}
            ... )
            >>> # Inspect or modify the request if needed
            >>> response = client.send_output_request(output_request)
        """
        # Extract document type from business document
        doc_type_key = next(iter(business_document.keys()))

        # Generate business document ID and type
        doc_id = doc_type_key
        business_document_type = f"com.sap.{doc_type_key.lower()}"

        # Build attachment config if URLs are provided
        attachment_config = None
        if attachment_urls:
            pre_gen_attachments = [
                PreGeneratedAttachment(url=url, source="DMS") for url in attachment_urls
            ]
            attachment_config = AttachmentConfig(
                preGeneratedAttachments=pre_gen_attachments
            )

        # Build email configuration
        lang = template_language or "en"
        email_config = EmailConfiguration(
            emailNotificationTemplateKey=notification_template_key,
            emailTemplateLanguage=lang,
            to=to,
            cc=cc,
            attachment=attachment_config,
        )

        # Build output management info
        output_mgmt = OutputManagementInfo(
            businessDocumentType=business_document_type,
            businessDocumentId=doc_id,
            isPriority=False,
            channels=[Channel.INTERNAL_EMAIL],
            emailConfiguration=email_config,
        )

        # Build request data
        data = OutputRequestData(
            OutputManagement=output_mgmt, BusinessDocument=business_document
        )

        # Build output request (CloudEvents structure)
        output_request = OutputRequest(
            source=f"/region/sap/{doc_type_key}",
            type=f"{business_document_type}.notification.created.v1",
            data=data,
        )

        return output_request

    @record_metrics(
        Module.OUTPUT_MANAGEMENT, Operation.OUTPUT_MANAGEMENT_SEND_OUTPUT_REQUEST
    )
    def send_output_request(self, output_request: OutputRequest) -> OutputResponse:
        """
        Send a pre-configured output request to the Output Management service.

        Args:
            output_request: The output request to submit

        Returns:
            OutputResponse containing the request ID if successful, or error details

        Example:
            >>> from sap_cloud_sdk.outputmanagement import create_client
            >>> client = create_client(destination_name="ARIBA_OUTPUT_SERVICE")
            >>> output_request = client.create_output_request(
            ...     notification_template_key="PO_NOTIFICATION",
            ...     to=["user@example.com"],
            ...     business_document={"PurchaseOrder": {"id": "PO-123"}}
            ... )
            >>> response = client.send_output_request(output_request)
        """
        return self._service_client.send_output_request(output_request)
