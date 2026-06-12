"""Email configuration model for INTERNAL_EMAIL channel."""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .attachment_config import AttachmentConfig


class EmailConfiguration(BaseModel):
    """
    Email configuration for INTERNAL_EMAIL channel.
    
    This class contains all the configuration needed to send emails via the INTERNAL_EMAIL channel,
    which skips Business Policy Framework evaluation and uses the configuration provided in the request.
    
    Usage Modes:
    - Mode 1 (Simple Notification): No attachment - fast email notification only
    - Mode 2 (With Document): With attachment - email with PDF attachment
    
    Attributes:
        email_notification_template_key: ANS template identifier for email body and subject (required)
        email_template_language: ISO language code for the email template (required)
        to: List of recipient email addresses (required, minimum 1)
        cc: List of CC recipient email addresses (optional)
        attachment: Optional attachment configuration for PDF generation (optional)
        
    Example - Simple Notification:
        ```python
        from sap_cloud_sdk.outputmanagement.models.email_configuration import EmailConfiguration
        
        config = EmailConfiguration(
            email_notification_template_key="PO_APPROVAL_NOTIFICATION",
            email_template_language="en",
            to=["finance@company.com", "warehouse@company.com"],
            cc=["manager@company.com"]
        )
        ```
        
    Example - With Document Attachment:
        ```python
        from sap_cloud_sdk.outputmanagement.models.email_configuration import EmailConfiguration
        from sap_cloud_sdk.outputmanagement.models.attachment_config import AttachmentConfig
        from sap_cloud_sdk.outputmanagement.models.form_configuration import FormConfiguration
        from sap_cloud_sdk.outputmanagement.constants import FileFormat
        
        form_config = FormConfiguration(
            form_name="PurchaseOrderForm",
            form_template_name="PurchaseOrderFormTemplate",
            form_language="en",
            file_format=FileFormat.PDF
        )
        
        attachment = AttachmentConfig(form_configuration=form_config)
        
        config = EmailConfiguration(
            email_notification_template_key="PO_APPROVED_WITH_DOC",
            email_template_language="en",
            to=["audit@company.com"],
            attachment=attachment
        )
        ```
    """

    email_notification_template_key: str = Field(
        ...,
        alias="emailNotificationTemplateKey",
        min_length=1,
        description="ANS template identifier for email body and subject"
    )
    
    email_template_language: str = Field(
        ...,
        alias="emailTemplateLanguage",
        min_length=1,
        description="ISO language code for the email template (e.g., 'en', 'de', 'fr')"
    )
    
    to: List[str] = Field(
        ...,
        min_length=1,
        description="List of recipient email addresses"
    )
    
    cc: Optional[List[str]] = Field(
        None,
        description="List of CC recipient email addresses"
    )
    
    bcc: Optional[List[str]] = Field(
        None,
        description="List of BCC recipient email addresses"
    )
    
    attachment: Optional[AttachmentConfig] = Field(
        None,
        description="Optional attachment configuration for PDF generation and pre-generated attachments"
    )

    @field_validator("to", "cc", "bcc")
    @classmethod
    def validate_email_list(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate email addresses."""
        if v is not None:
            for email in v:
                if not email or "@" not in email:
                    raise ValueError(f"Invalid email address: {email}")
        return v

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        str_strip_whitespace = True