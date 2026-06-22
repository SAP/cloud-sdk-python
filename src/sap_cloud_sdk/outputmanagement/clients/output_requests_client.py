"""Output requests client interface."""

import logging
from abc import ABC, abstractmethod

from ..models.output_request import OutputRequest
from ..models.output_response import (
    OutputResponse,
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
            businessDocumentType="com.sap.procurement.PurchaseOrder",
            businessDocumentId="PO-123"
        )

        response = requests_client.send_output_request(request)
        if response.has_errors():
            print(f"Errors: {response.errors}")
        else:
            request_id = response.output_request_id
            print(f"Request ID: {request_id}")
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
