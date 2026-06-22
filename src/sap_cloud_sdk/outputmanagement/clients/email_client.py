"""Email client for simplified email sending via SAP Ariba Output Service."""

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from ..models.output_request import OutputRequest
from ..models.output_request_data import OutputRequestData
from ..models.output_management_info import OutputManagementInfo
from ..models.email_configuration import EmailConfiguration
from ..models.output_response import OutputResponse, ErrorResponse
from ..models.attachment_config import AttachmentConfig
from ..models.pre_generated_attachment import PreGeneratedAttachment
from ..config.destination_credential_config import DestinationCredentialConfig
from ..constants import Channel
from ..utils.request_validator import RequestValidator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EmailClient:
    """
    Simplified client for sending emails through SAP Ariba Output Service.

    This client handles all the complexity internally - users only need to provide
    minimal information: template key, recipients, business document, and destination.
    """

    def create_output_request(
        self,
        notification_template_key: str,
        to: List[str],
        business_document: Dict[str, Any],
        cc: Optional[List[str]] = None,
        template_language: Optional[str] = "en",
        attachment_urls: Optional[List[str]] = None
    ) -> OutputRequest:
        """
        Create an OutputRequest object from the provided parameters.

        This method handles all the complexity of building the CloudEvents structure,
        extracting document metadata, and configuring email settings.

        Args:
            notification_template_key: ANS template identifier
            to: List of recipient email addresses
            business_document: The business document as a dictionary
            cc: Optional list of CC email addresses
            template_language: ISO language code for email template
            attachment_urls: Optional list of DMS URLs for pre-generated attachments

        Returns:
            OutputRequest: Fully constructed output request ready to send
        """
        # Extract document type from business document
        # Assuming the first key in business_document is the document type
        doc_type_key = next(iter(business_document.keys()))

        # Generate business document ID and type
        doc_id = doc_type_key
        business_document_type = f"com.sap.{doc_type_key.lower()}"

        # Build attachment config if URLs are provided
        attachment_config = None
        if attachment_urls:
            # Convert URLs to PreGeneratedAttachment objects
            pre_gen_attachments = [
                PreGeneratedAttachment(url=url, source="DMS")
                for url in attachment_urls
            ]

            attachment_config = AttachmentConfig(
                preGeneratedAttachments=pre_gen_attachments
            )

        # Build email configuration
        # Use default language if not provided
        lang = template_language or "en"
        email_config = EmailConfiguration(
            emailNotificationTemplateKey=notification_template_key,
            emailTemplateLanguage=lang,
            to=to,
            cc=cc,
            attachment=attachment_config
        )

        # Build output management info
        output_mgmt = OutputManagementInfo(
            businessDocumentType=business_document_type,
            businessDocumentId=doc_id,
            isPriority=False,
            channels=[Channel.INTERNAL_EMAIL],
            emailConfiguration=email_config
        )

        # Build request data (OutputManagement + BusinessDocument)
        data = OutputRequestData(
            OutputManagement=output_mgmt,
            BusinessDocument=business_document
        )

        # Build output request (CloudEvents structure)
        # Source format must be /region/application/tenant per CloudEvents spec
        output_request = OutputRequest(
            source=f"/region/sap/{doc_type_key}",
            type=f"{business_document_type}.notification.created.v1",
            data=data
        )

        return output_request

    def send_email(
        self,
        notification_template_key: str,
        to: List[str],
        business_document: Dict[str, Any],
        destination_name: str,
        cc: Optional[List[str]] = None,
        template_language: Optional[str] = "en",
        access_strategy: Optional[str] = None,
        instance: Optional[str] = None,
        attachment_urls: Optional[List[str]] = None
    ) -> OutputResponse:
        """
        Send an email using the SAP Ariba Output Service.

        This method builds the complete OutputRequest structure internally.
        All CloudEvents metadata and document types are auto-generated.

        Args:
            notification_template_key: ANS template identifier (e.g., "PO_APPROVAL_NOTIFICATION")
            to: List of recipient email addresses
            business_document: The business document as a dictionary
            destination_name: Name of the destination for authentication and endpoint
            cc: Optional list of CC email addresses
            template_language: ISO language code for email template (default: "en")
            access_strategy: Destination access strategy - "PROVIDER_ONLY" or "SUBSCRIBER_ONLY" (defaults to "PROVIDER_ONLY" if not specified)
            instance: Destination service instance name (defaults to "default" if not provided)
            attachment_urls: Optional list of DMS URLs for pre-generated attachments (default: None)

        Returns:
            OutputResponse: Response from the output service

        Raises:
            ValueError: If required parameters are invalid
            Exception: If the email sending fails

        Example - Simple Email:
            ```python
            from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient

            client = EmailClient()

            response = client.send_email(
                notification_template_key="PO_APPROVAL_NOTIFICATION",
                to=["finance@company.com"],
                BusinessDocument={
                    "PurchaseOrder": {
                        "orderId": "PO-12345",
                        "vendor": "ACME Corp",
                        "total": 1500.00
                    }
                },
                destination_name="ARIBA_OUTPUT_SERVICE"
            )

            if response.error:
                print(f"Failed: {response.error}")
            else:
                print(f"Success: {response.output_request_id}")
            ```

        Example - Email with DMS Attachments:
            ```python
            response = client.send_email(
                notification_template_key="PO_APPROVAL_NOTIFICATION",
                to=["finance@company.com"],
                BusinessDocument={"PurchaseOrder": {"orderId": "PO-12345"}},
                destination_name="ARIBA_OUTPUT_SERVICE",
                attachment_urls=[
                    "https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
                    "https://dms.example.com/browser/root?objectId=67890&cmisselector=content"
                ]
            )
            ```
        """
        # Validate input parameters using RequestValidator
        # Ensure template_language is never None for validation
        lang = template_language or "en"
        validation_error = RequestValidator.validate_email_parameters(
            notification_template_key=notification_template_key,
            to=to,
            business_document=business_document,
            template_language=lang,
            cc=cc
        )
        if validation_error:
            return OutputResponse(
                outputRequestId=None,
                error=ErrorResponse(
                    message=validation_error,
                    code="INVALID_REQUEST"
                )
            )

        # Validate destination_name
        if not destination_name or not destination_name.strip():
            return OutputResponse(
                outputRequestId=None,
                error=ErrorResponse(
                    message="destination_name cannot be null or empty",
                    code="INVALID_REQUEST"
                )
            )

        try:
            # Import here to avoid circular import (client.py -> email_client.py -> client_provider.py -> client.py)
            from ..client_provider import OutputManagementServiceClientProviderBuilder

            # Resolve instance name for logging
            inst = instance or "default"
            logger.info(f"Sending email via destination '{destination_name}' using instance '{inst}'")

            # Create the output request using the extracted method
            output_request = self.create_output_request(
                notification_template_key=notification_template_key,
                to=to,
                business_document=business_document,
                cc=cc,
                template_language=template_language,
                attachment_urls=attachment_urls
            )

            if attachment_urls:
                logger.debug(f"Created output request for template '{notification_template_key}' with {len(attachment_urls)} DMS attachment(s)")
            else:
                logger.debug(f"Created output request for template '{notification_template_key}'")

            # Validate the output request using RequestValidator
            validation_error = RequestValidator.validate(output_request)
            if validation_error:
                logger.error(f"Output request validation failed: {validation_error}")
                return OutputResponse(
                    outputRequestId=None,
                    error=ErrorResponse(
                        message=validation_error,
                        code="INVALID_REQUEST"
                    )
                )

            # Create destination config with access strategy and instance
            logger.debug(f"Creating destination config with access_strategy='{access_strategy}', instance='{inst}'")
            destination_config = DestinationCredentialConfig(
                destination_name=destination_name,
                access_strategy=access_strategy,
                instance=instance
            )

            # Build the client provider using the existing builder
            provider_builder = OutputManagementServiceClientProviderBuilder()
            provider_builder.with_destination_credentials(destination_config)

            # Build the provider and get the client
            provider = provider_builder.build()
            oms_client = provider.get_client()

            # Get the output requests client and send the request
            output_requests_client = oms_client.get_output_requests_client()
            return output_requests_client.send_output_request(output_request)

        except Exception as e:
            raise Exception(f"Failed to send email via destination '{destination_name}': {str(e)}") from e

    async def send_email_with_mcp(
        self,
        tool_name: str,
        notification_template_key: str,
        to_emails: List[str],
        business_document: Dict[str, Any],
        cc_email: Optional[str] = None,
        attachment_urls: Optional[List[str]] = None,
        mcp_tool: Any = None,
        sender_provider_subaccount_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an output request and invoke MCP tool with traceparent and sender_provider_subaccount_id.

        This method first generates an output request using the provided parameters, then invokes
        the specified MCP tool with the output request as the body, along with traceparent for
        distributed tracing and sender_provider_subaccount_id for multi-tenancy support.

        Args:
            tool_name: Name of the MCP tool to invoke
            notification_template_key: Template key for the notification
            to_emails: List of recipient email addresses
            business_document: Business document data
            cc_email: Optional CC email address
            attachment_url: Optional attachment URL
            mcp_tool: The MCP tool instance to invoke
            sender_provider_subaccount_id: Optional sender provider subaccount ID (defaults to env var)

        Returns:
            Result from the MCP tool invocation

        Raises:
            Exception: If the MCP tool invocation fails

        Example:
            ```python
            import asyncio
            from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient

            async def send_with_mcp():
                client = EmailClient()

                result = await client.send_email_with_output_request_and_mcp_async(
                    tool_name="send_output_request",
                    notification_template_key="PO_APPROVAL_NOTIFICATION",
                    to_emails=["finance@company.com"],
                    BusinessDocument={
                        "PurchaseOrder": {
                            "orderId": "PO-12345",
                            "vendor": "ACME Corp",
                            "total": 1500.00
                        }
                    },
                    mcp_tool=my_mcp_tool,
                    sender_provider_subaccount_id="my-subaccount-id"
                )
                return result

            result = asyncio.run(send_with_mcp())
            ```
        """
        import logging
        import os

        logger = logging.getLogger(__name__)

        try:
            logger.info("Creating output request for MCP tool '%s'", tool_name)

            # Create the output request
            output_request = self.create_output_request(
                notification_template_key=notification_template_key,
                to=to_emails,
                business_document=business_document,
                cc=[cc_email] if cc_email else None,
                template_language="en",
                attachment_urls=attachment_urls
            )

            logger.info("Output request created successfully")

            # Convert output request to dict for MCP payload
            payload = output_request.model_dump(by_alias=True, exclude_none=True)

            # Get sender_provider_subaccount_id from parameter or environment variable
            subaccount_id = sender_provider_subaccount_id or os.getenv("APPFND_CONHOS_SUBACCOUNTID")

            if not subaccount_id:
                logger.warning("sender_provider_subaccount_id not provided and APPFND_CONHOS_SUBACCOUNTID env var not set")

            logger.info("Invoking MCP tool '%s' with body, traceparent, and sender_provider_subaccount_id", tool_name)

            # Generate traceparent for distributed tracing
            import uuid
            trace_id = uuid.uuid4().hex  # 32 hex chars
            parent_id = uuid.uuid4().hex[:16]  # 16 hex chars
            traceparent = f"00-{trace_id}-{parent_id}-01"

            # Prepare the invocation payload
            invocation_payload = {
                "body": payload,
                "traceparent": traceparent,
                "sender_provider_subaccount_id": subaccount_id
            }

            # Log the payload before invoking
            logger.info("MCP tool '%s' invocation payload: %s", tool_name, invocation_payload)

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
