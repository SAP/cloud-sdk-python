"""Attachment configuration model for email documents."""

from typing import Optional, List
from pydantic import BaseModel, Field

from .form_configuration import FormConfiguration
from .pre_generated_attachment import PreGeneratedAttachment


class AttachmentConfig(BaseModel):
    """
    Attachment configuration for email documents.
    
    This class supports two types of attachments:
    1. Generated attachments: PDF documents generated from form templates
    2. Pre-generated attachments: Existing documents from external systems (e.g., DMS)
    
    Attributes:
        form_configuration: Form configuration for PDF generation (optional)
        pre_generated_attachments: List of pre-generated attachments from external sources (optional)
        
    Example - Generated Attachment:
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
        
    Example - Pre-generated Attachment from DMS:
        ```python
        from sap_cloud_sdk.outputmanagement.models.attachment_config import AttachmentConfig
        from sap_cloud_sdk.outputmanagement.models.pre_generated_attachment import PreGeneratedAttachment
        
        pre_gen_attachment = PreGeneratedAttachment(
            url="https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
            source="DMS"
        )
        
        attachment = AttachmentConfig(
            pre_generated_attachments=[pre_gen_attachment]
        )
        ```
        
    Example - Both Types:
        ```python
        attachment = AttachmentConfig(
            form_configuration=form_config,
            pre_generated_attachments=[pre_gen_attachment]
        )
        ```
    """

    form_configuration: Optional[FormConfiguration] = Field(
        None,
        alias="formConfiguration",
        description="Form configuration for PDF generation"
    )
    
    pre_generated_attachments: Optional[List[PreGeneratedAttachment]] = Field(
        None,
        alias="preGeneratedAttachments",
        description="List of pre-generated attachments from external sources like DMS"
    )

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        str_strip_whitespace = True
