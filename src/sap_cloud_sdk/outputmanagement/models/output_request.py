"""Output request model following CloudEvents 1.0 specification."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from .output_request_data import OutputRequestData


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
        from sap_cloud_sdk.outputmanagement.models.output_request import OutputRequest
        from sap_cloud_sdk.outputmanagement.models.output_request_data import OutputRequestData
        from sap_cloud_sdk.outputmanagement.models.output_management_info import OutputManagementInfo
        from sap_cloud_sdk.outputmanagement.models.email_configuration import EmailConfiguration
        from sap_cloud_sdk.outputmanagement.constants import Channel
        
        # Create email configuration
        email_config = EmailConfiguration(
            email_notification_template_key="PO_NOTIFICATION",
            email_template_language="en",
            to=["recipient@example.com"]
        )
        
        # Create output management info
        output_mgmt = OutputManagementInfo(
            business_document_type="com.sap.procurement.PurchaseOrder",
            business_document_id="PO-123",
            channels=[Channel.INTERNAL_EMAIL],
            email_configuration=email_config
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
            output_management=output_mgmt,
            business_document=business_doc
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
        description="CloudEvents specification version (should be '1.0')"
    )
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this event (UUID). Producers must ensure source + id is unique."
    )
    
    source: str = Field(
        ...,
        min_length=1,
        description="Identifies where this event originated from (e.g., '/eu12/sap.nexus.px/8d4bb3fa')"
    )
    
    time: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Timestamp when the output request was triggered (ISO 8601 format)"
    )
    
    type: str = Field(
        ...,
        min_length=1,
        description="Type of event (e.g., 'sap.nexus.px.purchaseorder.PurchaseOrder.Created.v1')"
    )
    
    data_content_type: str = Field(
        default="application/json",
        alias="datacontenttype",
        description="Content type of the event's data (must be 'application/json')"
    )
    
    data: OutputRequestData = Field(
        ...,
        description="Contains OutputManagement and BusinessDocument nodes"
    )
    
    xsapsisgwdestapp: Optional[str] = Field(
        None,
        description="SAP system gateway destination application identifier"
    )
    
    xsapsisgwdestappid: Optional[str] = Field(
        None,
        description="SAP system gateway destination application ID"
    )
    
    xsapsisgwbackendid: Optional[str] = Field(
        None,
        description="SAP system gateway backend ID"
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
            spec_version=self._spec_version,
            id=self._id or str(uuid.uuid4()),
            source=self._source,
            time=self._time or datetime.utcnow().isoformat() + "Z",
            type=self._type,
            data_content_type=self._data_content_type,
            data=self._data,
            xsapsisgwdestapp=self._xsapsisgwdestapp,
            xsapsisgwdestappid=self._xsapsisgwdestappid,
            xsapsisgwbackendid=self._xsapsisgwbackendid,
        )