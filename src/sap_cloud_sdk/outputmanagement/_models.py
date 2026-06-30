"""Data models for SAP Output Management Service."""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import uuid

from .constants import Channel


# ============================================================================
# Form Configuration
# ============================================================================


class FormConfiguration(BaseModel):
    """Form channel configuration.

    Attributes:
        form_id: Form identifier
        form_data: Optional form data
        callback_url: Optional callback URL for form submission
    """

    form_id: str = Field(..., min_length=1, description="Form identifier")
    form_data: Optional[Dict[str, Any]] = Field(None, description="Form data")
    callback_url: Optional[str] = Field(
        None, description="Callback URL for form submission"
    )

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True


# ============================================================================
# Pre-generated Attachment
# ============================================================================


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
        from sap_cloud_sdk.outputmanagement._models import PreGeneratedAttachment

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


# ============================================================================
# Attachment Configuration
# ============================================================================


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
        from sap_cloud_sdk.outputmanagement._models import AttachmentConfig, FormConfiguration
        from sap_cloud_sdk.outputmanagement.constants import FileFormat

        form_config = FormConfiguration(
            form_name="PurchaseOrderForm",
            form_template_name="PurchaseOrderFormTemplate",
            form_language="en",
            file_format=FileFormat.PDF
        )

        attachment = AttachmentConfig(formConfiguration=form_config)
        ```

    Example - Pre-generated Attachment from DMS:
        ```python
        from sap_cloud_sdk.outputmanagement._models import AttachmentConfig, PreGeneratedAttachment

        pre_gen_attachment = PreGeneratedAttachment(
            url="https://dms.example.com/browser/root?objectId=12345&cmisselector=content",
            source="DMS"
        )

        attachment = AttachmentConfig(
            preGeneratedAttachments=[pre_gen_attachment]
        )
        ```

    Example - Both Types:
        ```python
        attachment = AttachmentConfig(
            formConfiguration=form_config,
            preGeneratedAttachments=[pre_gen_attachment]
        )
        ```
    """

    form_configuration: Optional[FormConfiguration] = Field(
        None,
        alias="formConfiguration",
        description="Form configuration for PDF generation",
    )

    pre_generated_attachments: Optional[List[PreGeneratedAttachment]] = Field(
        None,
        alias="preGeneratedAttachments",
        description="List of pre-generated attachments from external sources like DMS",
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        str_strip_whitespace = True


# ============================================================================
# Email Configuration
# ============================================================================


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
        from sap_cloud_sdk.outputmanagement._models import EmailConfiguration

        config = EmailConfiguration(
            emailNotificationTemplateKey="PO_APPROVAL_NOTIFICATION",
            emailTemplateLanguage="en",
            to=["finance@company.com", "warehouse@company.com"],
            cc=["manager@company.com"]
        )
        ```

    Example - With Document Attachment:
        ```python
        from sap_cloud_sdk.outputmanagement._models import (
            EmailConfiguration,
            AttachmentConfig,
            FormConfiguration
        )
        from sap_cloud_sdk.outputmanagement.constants import FileFormat

        form_config = FormConfiguration(
            form_name="PurchaseOrderForm",
            form_template_name="PurchaseOrderFormTemplate",
            form_language="en",
            file_format=FileFormat.PDF
        )

        attachment = AttachmentConfig(formConfiguration=form_config)

        config = EmailConfiguration(
            emailNotificationTemplateKey="PO_APPROVED_WITH_DOC",
            emailTemplateLanguage="en",
            to=["audit@company.com"],
            attachment=attachment
        )
        ```
    """

    email_notification_template_key: str = Field(
        ...,
        alias="emailNotificationTemplateKey",
        min_length=1,
        description="ANS template identifier for email body and subject",
    )

    email_template_language: str = Field(
        ...,
        alias="emailTemplateLanguage",
        min_length=1,
        description="ISO language code for the email template (e.g., 'en', 'de', 'fr')",
    )

    to: List[str] = Field(
        ..., min_length=1, description="List of recipient email addresses"
    )

    cc: Optional[List[str]] = Field(
        None, description="List of CC recipient email addresses"
    )

    bcc: Optional[List[str]] = Field(
        None, description="List of BCC recipient email addresses"
    )

    attachment: Optional[AttachmentConfig] = Field(
        None,
        description="Optional attachment configuration for PDF generation and pre-generated attachments",
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


# ============================================================================
# Direct Share Configuration
# ============================================================================


class DirectShareConfiguration(BaseModel):
    """Direct share channel configuration.

    Attributes:
        user_ids: List of user IDs to share with
        group_ids: Optional list of group IDs to share with
        message: Optional message to include
        expiration_days: Optional number of days until expiration
    """

    user_ids: List[str] = Field(..., min_length=1, description="User IDs to share with")
    group_ids: Optional[List[str]] = Field(None, description="Group IDs to share with")
    message: Optional[str] = Field(None, description="Message to include")
    expiration_days: Optional[int] = Field(
        None, ge=1, description="Days until expiration"
    )

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True


# ============================================================================
# Output Management Info
# ============================================================================


class OutputManagementInfo(BaseModel):
    """
    Contains information required by Output Management to decide on how to orchestrate the output.

    This class encapsulates the configuration and metadata needed for output processing,
    including business document identification, delivery channels, and channel-specific configurations.

    Attributes:
        business_document_type: Type of the business document (required)
        business_document_id: ID of the business document (required)
        is_priority: Indicates if this is a priority request (optional, default: False)
        user_id: User ID who triggered the output request (optional)
        channels: List of channels for output delivery (required)
        direct_share_configuration: Configuration for direct share channel (optional)
        email_configuration: Configuration for internal email channel (optional)
        cig_data_center: CIG Data Center information (optional)

    Example:
        ```python
        from sap_cloud_sdk.outputmanagement._models import (
            OutputManagementInfo,
            EmailConfiguration
        )
        from sap_cloud_sdk.outputmanagement.constants import Channel

        email_config = EmailConfiguration(
            emailNotificationTemplateKey="PO_NOTIFICATION",
            emailTemplateLanguage="en",
            to=["recipient@example.com"]
        )

        output_mgmt = OutputManagementInfo(
            businessDocumentType="com.sap.procurement.PurchaseOrder",
            businessDocumentId="PO-123",
            isPriority=False,
            user_id="user@sap.com",
            channels=[Channel.INTERNAL_EMAIL],
            emailConfiguration=email_config
        )
        ```
    """

    business_document_type: str = Field(
        ...,
        alias="businessDocumentType",
        min_length=1,
        description="Type of the business document (e.g., 'com.sap.procurement.PurchaseOrder')",
    )

    business_document_id: str = Field(
        ...,
        alias="businessDocumentId",
        min_length=1,
        description="ID of the business document (e.g., 'PO00551100')",
    )

    is_priority: bool = Field(
        False, alias="isPriority", description="Indicates if this is a priority request"
    )

    user_id: Optional[str] = Field(
        None,
        alias="userId",
        description="User ID who triggered the output request (e.g., 'user@sap.com')",
    )

    channels: List[Channel] = Field(
        ..., min_length=1, description="List of channels for output delivery"
    )

    direct_share_configuration: Optional[DirectShareConfiguration] = Field(
        None,
        alias="directShareConfiguration",
        description="Configuration for direct share channel",
    )

    email_configuration: Optional[EmailConfiguration] = Field(
        None,
        alias="emailConfiguration",
        description="Configuration for internal email channel",
    )

    cig_data_center: Optional[str] = Field(
        None, alias="cigDataCenter", description="CIG Data Center information"
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        str_strip_whitespace = True
        use_enum_values = True


# ============================================================================
# Output Request Data
# ============================================================================


class OutputRequestData(BaseModel):
    """
    Container for the data payload of an Output Management request.

    This class serves as the envelope for the actual request data, containing two essential components:
    - OutputManagement: Metadata and configuration for output orchestration
    - BusinessDocument: The actual business document data to be processed

    The business document is stored as a dictionary to provide maximum flexibility
    in handling different document structures and types.

    JSON Structure:
        ```json
        {
          "OutputManagement": {
            "businessDocumentType": "com.sap.procurement.PurchaseOrder",
            "businessDocumentId": "PO-123",
            ...
          },
          "BusinessDocument": {
            "PurchaseOrder": {
              "orderId": "PO-123",
              "vendor": "ABC Corp",
              ...
            }
          }
        }
        ```

    Attributes:
        output_management: Information required by Output Management for orchestration (required)
        business_document: The business document as a dictionary/JSON object (required)

    Example:
        ```python
        from sap_cloud_sdk.outputmanagement._models import (
            OutputRequestData,
            OutputManagementInfo
        )
        from sap_cloud_sdk.outputmanagement.constants import Channel

        output_mgmt = OutputManagementInfo(
            businessDocumentType="com.sap.procurement.PurchaseOrder",
            businessDocumentId="PO-123",
            channels=[Channel.INTERNAL_EMAIL],
            emailConfiguration=email_config
        )

        business_doc = {
            "PurchaseOrder": {
                "orderId": "PO-123",
                "vendor": "ABC Corp",
                "total": 1500.00
            }
        }

        data = OutputRequestData(
            OutputManagement=output_mgmt,
            BusinessDocument=business_doc
        )
        ```
    """

    output_management: OutputManagementInfo = Field(
        ...,
        alias="OutputManagement",
        description="Information required by Output Management to orchestrate the output",
    )

    business_document: Dict[str, Any] = Field(
        ...,
        alias="BusinessDocument",
        description="The business document as a JSON object",
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


# ============================================================================
# Output Request
# ============================================================================


class OutputRequest(BaseModel):
    """
    Represents an Output Management request following the CloudEvents 1.0 specification.

    This is the main request object that encapsulates all information required to trigger
    document generation and delivery through the Output Management service. It follows the
    CloudEvents specification for event-driven architectures.

    Attributes:
        spec_version: CloudEvents specification version (default: "1.0")
        id: Unique ID for this event (auto-generated UUID if not provided)
        source: Identifies where this event originated from (required)
        time: Timestamp when the output request was triggered (auto-generated if not provided)
        type: Describes the type of event (required)
        data_content_type: Content type of event's data (default: "application/json")
        data: Contains OutputManagement and BusinessDocument (required)
        xsapsisgwdestapp: SAP system gateway destination application identifier (optional)
        xsapsisgwdestappid: SAP system gateway destination application ID (optional)
        xsapsisgwbackendid: SAP system gateway backend ID (optional)

    Example:
        ```python
        from sap_cloud_sdk.outputmanagement._models import (
            OutputRequest,
            OutputRequestData,
            OutputManagementInfo,
            EmailConfiguration
        )
        from sap_cloud_sdk.outputmanagement.constants import Channel

        # Create email configuration
        email_config = EmailConfiguration(
            emailNotificationTemplateKey="PO_NOTIFICATION",
            emailTemplateLanguage="en",
            to=["recipient@example.com"]
        )

        # Create output management info
        output_mgmt = OutputManagementInfo(
            businessDocumentType="com.sap.procurement.PurchaseOrder",
            businessDocumentId="PO-123",
            channels=[Channel.INTERNAL_EMAIL],
            emailConfiguration=email_config
        )

        # Create business document
        business_doc = {
            "PurchaseOrder": {
                "orderId": "PO-123",
                "vendor": "ABC Corp"
            }
        }

        # Create request data
        data = OutputRequestData(
            OutputManagement=output_mgmt,
            BusinessDocument=business_doc
        )

        # Create output request
        request = OutputRequest(
            source="/eu12/sap.procurement/tenant-123",
            type="com.sap.procurement.purchaseorder.created",
            data=data
        )
        ```
    """

    spec_version: str = Field(
        default="1.0",
        alias="specversion",
        description="CloudEvents specification version (should be '1.0')",
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this event (UUID). Producers must ensure source + id is unique.",
    )

    source: str = Field(
        ...,
        min_length=1,
        description="Identifies where this event originated from (e.g., '/eu12/sap.nexus.px/8d4bb3fa')",
    )

    time: str = Field(
        default_factory=lambda: (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        ),
        description="Timestamp when the output request was triggered (ISO 8601 format)",
    )

    type: str = Field(
        ...,
        min_length=1,
        description="Type of event (e.g., 'sap.nexus.px.purchaseorder.PurchaseOrder.Created.v1')",
    )

    data_content_type: str = Field(
        default="application/json",
        alias="datacontenttype",
        description="Content type of the event's data (must be 'application/json')",
    )

    data: OutputRequestData = Field(
        ..., description="Contains OutputManagement and BusinessDocument nodes"
    )

    xsapsisgwdestapp: Optional[str] = Field(
        None, description="SAP system gateway destination application identifier"
    )

    xsapsisgwdestappid: Optional[str] = Field(
        None, description="SAP system gateway destination application ID"
    )

    xsapsisgwbackendid: Optional[str] = Field(
        None, description="SAP system gateway backend ID"
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        str_strip_whitespace = True


class OutputRequestBuilder:
    """
    Builder for constructing OutputRequest objects.

    This builder provides a fluent API for creating OutputRequest instances with proper validation.
    """

    def __init__(self):
        """Initialize builder with default values."""
        self._spec_version: str = "1.0"
        self._id: Optional[str] = None
        self._source: Optional[str] = None
        self._time: Optional[str] = None
        self._type: Optional[str] = None
        self._data_content_type: str = "application/json"
        self._data: Optional[OutputRequestData] = None
        self._xsapsisgwdestapp: Optional[str] = None
        self._xsapsisgwdestappid: Optional[str] = None
        self._xsapsisgwbackendid: Optional[str] = None

    def spec_version(self, spec_version: str) -> "OutputRequestBuilder":
        """Set CloudEvents specification version."""
        self._spec_version = spec_version
        return self

    def id(self, id: str) -> "OutputRequestBuilder":
        """Set event ID."""
        self._id = id
        return self

    def source(self, source: str) -> "OutputRequestBuilder":
        """Set event source."""
        self._source = source
        return self

    def time(self, time: str) -> "OutputRequestBuilder":
        """Set event timestamp."""
        self._time = time
        return self

    def type(self, type: str) -> "OutputRequestBuilder":
        """Set event type."""
        self._type = type
        return self

    def data_content_type(self, data_content_type: str) -> "OutputRequestBuilder":
        """Set data content type."""
        self._data_content_type = data_content_type
        return self

    def data(self, data: OutputRequestData) -> "OutputRequestBuilder":
        """Set request data."""
        self._data = data
        return self

    def xsapsisgwdestapp(self, xsapsisgwdestapp: str) -> "OutputRequestBuilder":
        """Set SAP system gateway destination app."""
        self._xsapsisgwdestapp = xsapsisgwdestapp
        return self

    def xsapsisgwdestappid(self, xsapsisgwdestappid: str) -> "OutputRequestBuilder":
        """Set SAP system gateway destination app ID."""
        self._xsapsisgwdestappid = xsapsisgwdestappid
        return self

    def xsapsisgwbackendid(self, xsapsisgwbackendid: str) -> "OutputRequestBuilder":
        """Set SAP system gateway backend ID."""
        self._xsapsisgwbackendid = xsapsisgwbackendid
        return self

    def build(self) -> OutputRequest:
        """
        Build OutputRequest instance.

        Returns:
            OutputRequest instance

        Raises:
            ValueError: If required fields are missing
        """
        if not self._source:
            raise ValueError("source is required")
        if not self._type:
            raise ValueError("type is required")
        if not self._data:
            raise ValueError("data is required")

        return OutputRequest(
            specversion=self._spec_version,
            id=self._id or str(uuid.uuid4()),
            source=self._source,
            time=self._time
            or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            type=self._type,
            datacontenttype=self._data_content_type,
            data=self._data,
            xsapsisgwdestapp=self._xsapsisgwdestapp,
            xsapsisgwdestappid=self._xsapsisgwdestappid,
            xsapsisgwbackendid=self._xsapsisgwbackendid,
        )


# ============================================================================
# Output Response
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response model."""

    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )

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
        description="The unique identifier for the output request",
    )
    error: Optional[ErrorResponse] = Field(
        None, description="Error encountered during processing"
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
