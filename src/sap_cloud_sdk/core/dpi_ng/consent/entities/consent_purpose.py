"""python-odata entity classes for consentPurposeExternalServices."""

from __future__ import annotations

from typing import Any

from odata.property import (
    BooleanProperty,
    DatetimeProperty,
    StringProperty,
    UUIDProperty,
)


def _make_entities(Service: Any) -> tuple:
    """Create and return all entity classes bound to the given ODataService instance."""

    class ConsentPurpose(Service.Entity):
        """OData entity representing a consent purpose record."""

        __odata_collection__ = "consentPurposes"
        tenant = StringProperty("tenant")
        purpose_id = UUIDProperty("purposeId", primary_key=True)
        purpose_name = StringProperty("purposeName")
        lifecycle_status_code = StringProperty("lifecycleStatusCode")
        lifecycle_status_domain_description = StringProperty(
            "lifecycleStatusDomainDescription"
        )
        sensitive_data_flag = BooleanProperty("sensitiveDataFlag")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class ConsentPurposeText(Service.Entity):
        """OData entity representing a localised text for a consent purpose."""

        __odata_collection__ = "consentPurposeTexts"
        tenant = StringProperty("tenant")
        purpose_id = UUIDProperty("purposeId", primary_key=True)
        type_code = StringProperty("typeCode", primary_key=True)
        language_code = StringProperty("languageCode", primary_key=True)
        text = StringProperty("text")
        changed_at = DatetimeProperty("changedAt")

    return (
        ConsentPurpose,
        ConsentPurposeText,
    )
