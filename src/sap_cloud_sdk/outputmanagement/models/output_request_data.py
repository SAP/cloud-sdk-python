"""Output Request Data model."""

from typing import Any, Dict
from pydantic import BaseModel, Field

from .output_management_info import OutputManagementInfo


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
        from sap_cloud_sdk.outputmanagement.models.output_request_data import OutputRequestData
        from sap_cloud_sdk.outputmanagement.models.output_management_info import OutputManagementInfo
        from sap_cloud_sdk.outputmanagement.constants import Channel
        
        output_mgmt = OutputManagementInfo(
            business_document_type="com.sap.procurement.PurchaseOrder",
            business_document_id="PO-123",
            channels=[Channel.INTERNAL_EMAIL],
            email_configuration=email_config
        )
        
        business_doc = {
            "PurchaseOrder": {
                "orderId": "PO-123",
                "vendor": "ABC Corp",
                "total": 1500.00
            }
        }
        
        data = OutputRequestData(
            output_management=output_mgmt,
            business_document=business_doc
        )
        ```
    """

    output_management: OutputManagementInfo = Field(
        ...,
        alias="OutputManagement",
        description="Information required by Output Management to orchestrate the output"
    )
    
    business_document: Dict[str, Any] = Field(
        ...,
        alias="BusinessDocument",
        description="The business document as a JSON object"
    )

    class Config:
        """Pydantic configuration."""
        populate_by_name = True