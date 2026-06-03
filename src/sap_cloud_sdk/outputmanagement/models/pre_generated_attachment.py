"""Pre-generated attachment model for email configuration."""

from typing import Optional
from pydantic import BaseModel, Field


class PreGeneratedAttachment(BaseModel):
    """
    Represents a pre-generated attachment to be included in an email.

    Each attachment has a URL pointing to the pre-generated document and an optional
    file format descriptor.

    Attributes:
        url: URL of the pre-generated attachment document (required)
        file_format: File format of the attachment (e.g., 'PDF', 'DOCX') (optional)

    Example:
        ```python
        from sap_cloud_sdk.outputmanagement.models.pre_generated_attachment import PreGeneratedAttachment

        attachment = PreGeneratedAttachment(
            url="https://storage.example.com/documents/po-12345.pdf",
            file_format="PDF"
        )
        ```
    """

    url: str = Field(
        ...,
        min_length=1,
        description="URL of the pre-generated attachment document"
    )

    file_format: Optional[str] = Field(
        None,
        alias="fileFormat",
        description="File format of the attachment (e.g., 'PDF', 'DOCX')"
    )

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        str_strip_whitespace = True