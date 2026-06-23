"""Output Management information model."""

from typing import Optional, List
from pydantic import BaseModel, Field

from ..constants import Channel
from .email_configuration import EmailConfiguration
from .direct_share_configuration import DirectShareConfiguration


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
        from sap_cloud_sdk.outputmanagement.models.output_management_info import OutputManagementInfo
        from sap_cloud_sdk.outputmanagement.models.email_configuration import EmailConfiguration
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
