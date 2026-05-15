"""Output response model."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field



class ErrorResponse(BaseModel):
    """Error response model."""

    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True

class OutputResponse(BaseModel):
    """Output response wrapper.

    Response object for Output Management service operations.
    Contains the request identifier or error information.
    """

    output_request_id: Optional[str] = Field(
        None,
        alias="outputRequestId",
        description="The unique identifier for the output request"
    )
    error: Optional[ErrorResponse] = Field(None, description="Error encountered during processing")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

class OutputRequestChannelResponse(BaseModel):
    """Output request channel response."""

    channel: str = Field(..., description="Channel name")
    status: str = Field(..., description="Channel status")
    error_message: Optional[str] = Field(
        None,
        alias="errorMessage",
        description="Error message if any"
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

class OutputRequestStatusResponse(BaseModel):
    """Output request status response."""

    request_id: str = Field(..., alias="requestId", description="Request identifier")
    business_document_id: Optional[str] = Field(
        None,
        alias="businessDocumentId",
        description="Business document identifier"
    )
    business_document_type: Optional[str] = Field(
        None,
        alias="businessDocumentType",
        description="Business document type"
    )
    created_at: str = Field(..., alias="createdAt", description="Creation timestamp")
    channels: Optional[List[OutputRequestChannelResponse]] = Field(
        None,
        description="Channel responses"
    )
    error_message: Optional[str] = Field(
        None,
        alias="errorMessage",
        description="Error message"
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


class DocumentResponse(BaseModel):
    """Document response wrapper.

    Contains either the document content or an error response.
    """

    document_content: Optional[bytes] = Field(
        None,
        alias="documentContent",
        description="Binary document content"
    )
    error: Optional[ErrorResponse] = Field(None, description="Error response")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

class JobStatusResponse(BaseModel):
    """Job status response wrapper.

    Contains either the output request status response or an error response.
    """

    output_request_status_response: Optional[OutputRequestStatusResponse] = Field(
        None,
        alias="outputRequestStatusResponse",
        description="Output request status response"
    )
    error: Optional[ErrorResponse] = Field(None, description="Error response")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
