"""Output response model."""

from typing import Optional, Dict, Any
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
