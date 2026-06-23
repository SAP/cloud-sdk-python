"""Pre-generated attachment model for email attachments from external sources like DMS."""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class PreGeneratedAttachment(BaseModel):
    """
    Pre-generated attachment configuration for email attachments from external sources.

    This class represents an attachment that already exists in an external system (like DMS)
    and should be attached to the email by reference via URL.

    Attributes:
        url: The URL to access the pre-generated attachment (required)
        source: The source system of the attachment, currently only "DMS" is supported (required)

    Example:
        ```python
        from sap_cloud_sdk.outputmanagement.models.pre_generated_attachment import PreGeneratedAttachment

        attachment = PreGeneratedAttachment(
            url="https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
            source="DMS"
        )
        ```
    """

    url: str = Field(
        ..., min_length=1, description="The URL to access the pre-generated attachment"
    )

    source: Literal["DMS"] = Field(
        ...,
        description="The source system of the attachment (currently only 'DMS' is supported)",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL is not empty and is a valid URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")

        v = v.strip()

        # Basic URL validation - must start with http:// or https://
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")

        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate that source is 'DMS'."""
        if v != "DMS":
            raise ValueError("Currently only 'DMS' is supported as attachment source")
        return v

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        str_strip_whitespace = True
