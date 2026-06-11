"""Attachment configuration model for email documents."""

from typing import Optional
from pydantic import BaseModel, Field

from .form_configuration import FormConfiguration


class AttachmentConfig(BaseModel):
    """
    Attachment configuration for email documents.
    
    This is a helper class used to parse attachment configuration from INTERNAL_EMAIL requests.
    It contains form configuration details that will be used to populate FormConfiguration
    for document generation.
    
    If provided in EmailConfiguration, a PDF document will be generated using these form details
    and attached to the email. If not provided, no document will be generated.
    
    Attributes:
        form_configuration: Form configuration for PDF generation
        
    Example:
        ```python
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
        ```
    """

    form_configuration: FormConfiguration = Field(
        ...,
        alias="formConfiguration",
        description="Form configuration for PDF generation"
    )

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        str_strip_whitespace = True