"""Email client for simplified email sending via SAP Ariba Output Service."""

from typing import Optional, List, Dict, Any
from ..models.output_request import OutputRequest
from ..models.output_request_data import OutputRequestData
from ..models.output_management_info import OutputManagementInfo
from ..models.email_configuration import EmailConfiguration
from ..models.output_response import OutputResponse, ErrorResponse
from ..config.destination_credential_config import DestinationCredentialConfig
from ..constants import Channel
from ..utils.request_validator import RequestValidator


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
        template_language: str = "en"
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
            
        Returns:
            OutputRequest: Fully constructed output request ready to send
        """
        # Extract document type and ID from business document
        # Assuming the first key in business_document is the document type
        doc_type_key = next(iter(business_document.keys()))
        doc_content = business_document[doc_type_key]
        
        # Try to extract document ID from common field names
        doc_id = None
        for id_field in ['id', 'orderId', 'invoiceNumber', 'documentId', 'number']:
            if id_field in doc_content:
                doc_id = str(doc_content[id_field])
                break
        
        # If no ID found, use template key as fallback
        if not doc_id:
            doc_id = f"{notification_template_key}-{id(business_document)}"
        
        # Generate business document type from the key
        business_document_type = f"com.sap.{doc_type_key.lower()}"
        
        # Build email configuration
        email_config = EmailConfiguration(
            email_notification_template_key=notification_template_key,
            email_template_language=template_language,
            to=to,
            cc=cc
        )
        
        # Build output management info
        output_mgmt = OutputManagementInfo(
            business_document_type=business_document_type,
            business_document_id=doc_id,
            is_priority=False,
            channels=[Channel.INTERNAL_EMAIL],
            email_configuration=email_config
        )
        
        # Build request data (OutputManagement + BusinessDocument)
        data = OutputRequestData(
            output_management=output_mgmt,
            business_document=business_document
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
        template_language: str = "en",
        access_strategy: str = "PROVIDER_ONLY"
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
            access_strategy: Destination access strategy - "PROVIDER_ONLY" or "SUBSCRIBER_ONLY" (default: "PROVIDER_ONLY")
            
        Returns:
            OutputResponse: Response from the output service
            
        Raises:
            ValueError: If required parameters are invalid
            Exception: If the email sending fails
            
        Example:
            ```python
            from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient
            
            client = EmailClient()
            
            # Just provide essentials - that's it!
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
            
            if response.error:
                print(f"Failed: {response.error}")
            else:
                print(f"Success: {response.output_request_id}")
            ```
        """
        # Validate input parameters using RequestValidator
        validation_error = RequestValidator.validate_email_parameters(
            notification_template_key=notification_template_key,
            to=to,
            business_document=business_document,
            template_language=template_language,
            cc=cc
        )
        if validation_error:
            return OutputResponse(
                output_request_id=None,
                error=ErrorResponse(
                    message=validation_error,
                    code="INVALID_REQUEST"
                )
            )
        
        # Validate destination_name
        if not destination_name or not destination_name.strip():
            return OutputResponse(
                output_request_id=None,
                error=ErrorResponse(
                    message="destination_name cannot be null or empty",
                    code="INVALID_REQUEST"
                )
            )
        
        try:
            # Import here to avoid circular import at module initialization
            from ..client_provider import OutputManagementServiceClientProviderBuilder
            
            # Create the output request using the extracted method
            output_request = self.create_output_request(
                notification_template_key=notification_template_key,
                to=to,
                business_document=business_document,
                cc=cc,
                template_language=template_language
            )
            
            # Validate the output request using RequestValidator
            validation_error = RequestValidator.validate(output_request)
            if validation_error:
                return OutputResponse(
                    output_request_id=None,
                    error=ErrorResponse(
                        message=validation_error,
                        code="INVALID_REQUEST"
                    )
                )
            
            # Create destination config with access strategy
            destination_config = DestinationCredentialConfig(
                destination_name=destination_name,
                access_strategy=access_strategy
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