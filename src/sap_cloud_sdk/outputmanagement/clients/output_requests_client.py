"""Output requests client interface."""

import logging
from abc import ABC, abstractmethod

from ..models.output_request import OutputRequest
from ..models.output_response import (
    OutputResponse,
    JobStatusResponse,
    DocumentResponse,
)

logger = logging.getLogger(__name__)


class OutputRequestsClient(ABC):
    """
    Interface for managing output requests in the Output Management service.
    
    This interface defines operations for:
    - Submitting output requests for document generation and delivery
    - Checking the status of submitted requests
    - Retrieving generated documents
    
    Usage Example:
        from sap_cloud_sdk.outputmanagement import OutputManagementServiceClient
        
        client = OutputManagementServiceClient.from_destination("DEST")
        requests_client = client.get_output_requests_client()
        
        # Submit request
        request = OutputRequest(
            source="https://...",
            type="com.sap.procurement.po.created",
            business_document_type="com.sap.procurement.PurchaseOrder",
            business_document_id="PO-123"
        )
        
        response = requests_client.send_output_request(request)
        if response.has_errors():
            print(f"Errors: {response.errors}")
        else:
            request_id = response.output_request_id
            print(f"Request ID: {request_id}")
            
            # Check status
            status = requests_client.get_output_request_status(request_id)
            if not status.errors:
                print(f"Status: {status.created_at}")
            
            # Get document
            document_response = requests_client.get_document("DIRECT_SHARE", request_id)
            if not document_response.errors:
                document = document_response.document_content
                print(f"Document size: {len(document)}")
    """

    @abstractmethod
    def send_output_request(self, output_request: OutputRequest) -> OutputResponse:
        """
        Submits an output request to the Output Management service.
        
        This method sends a complete output request to trigger document generation and delivery.
        The request is processed asynchronously, and this method returns immediately with an
        OutputResponse containing the request ID or error information.
        
        Response Handling:
        - HTTP 202 (Accepted) - Request successfully submitted, returns OutputResponse with request ID
        - HTTP 4xx - Client error, returns OutputResponse with error details
        - HTTP 5xx - Server error, returns OutputResponse with error details
        - Validation Error - Returns OutputResponse with validation error message
        
        Note: This method does not raise exceptions. Check the response's has_errors() method
        or errors list to determine if the operation was successful.
        
        Args:
            output_request: The output request to submit
            
        Returns:
            OutputResponse containing the request ID if successful, or error details if failed
        """
        pass

    @abstractmethod
    def get_output_request_status(self, request_id: str) -> JobStatusResponse:
        """
        Retrieves the status of a previously submitted output request.
        
        Use this method to check the processing status of an output request after submission.
        The response contains detailed information about the request processing state.
        
        Common Status Values:
        - PENDING - Request is queued for processing
        - PROCESSING - Document generation in progress
        - COMPLETED - Document successfully generated and delivered
        - FAILED - Processing failed (check error details)
        
        Note: This method does not raise exceptions. Check the response's errors field
        to determine if the operation failed.
        
        Args:
            request_id: The ID of the request to check
            
        Returns:
            JobStatusResponse containing request details if successful, or error details if failed
        """
        pass

    @abstractmethod
    def get_document(self, channel: str, output_request_id: str) -> DocumentResponse:
        """
        Retrieves a generated document from the Output Management service.
        
        This method downloads the binary content of a document that was generated
        as part of an output request. The document must be available (request status = COMPLETED)
        before it can be retrieved.
        
        Supported Channels:
        - DIRECT_SHARE - Documents stored for direct download
        - EMAIL - Attachments from email deliveries (if accessible)
        - PRINT - Print-ready documents
        
        Note: This method does not raise exceptions. Check the response's errors field
        to determine if the operation failed.
        
        Args:
            channel: The delivery channel (e.g., "DIRECT_SHARE")
            output_request_id: The output request ID
            
        Returns:
            DocumentResponse containing the document content if successful, or error details if failed
        """
        pass