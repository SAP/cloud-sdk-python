"""python-odata entity classes for consentTemplateExternalServices."""

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

    class ConsentTemplate(Service.Entity):
        """OData entity representing a consent template record."""

        __odata_collection__ = "consentTemplates"
        tenant = StringProperty("tenant")
        template_id = UUIDProperty("templateId", primary_key=True)
        template_name = StringProperty("templateName")
        purpose_id = UUIDProperty("purposeId")
        controller_id = UUIDProperty("controllerId")
        application_id = UUIDProperty("applicationId")
        jurisdiction_code = StringProperty("jurisdictionCode")
        consent_model_code = StringProperty("consentModelCode")
        application_template_id = StringProperty("applicationTemplateId")
        validity_period = StringProperty("validityPeriod")
        expiring_period = StringProperty("expiringPeriod")
        lifecycle_status_code = StringProperty("lifecycleStatusCode")
        purpose_name = StringProperty("purposeName")
        controller_name = StringProperty("controllerName")
        application_name = StringProperty("applicationName")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class ConsentTemplateText(Service.Entity):
        """OData entity representing a localised text for a consent template."""

        __odata_collection__ = "consentTemplateTexts"
        tenant = StringProperty("tenant")
        template_id = UUIDProperty("templateId", primary_key=True)
        type_code = StringProperty("typeCode", primary_key=True)
        language_code = StringProperty("languageCode", primary_key=True)
        text = StringProperty("text")
        changed_at = DatetimeProperty("changedAt")

    class TemplateThirdPartyPersData(Service.Entity):
        """OData entity linking a consent template to a third party's personal data handling."""

        __odata_collection__ = "templateThirdPartyPersDatas"
        tenant = StringProperty("tenant")
        template_id = UUIDProperty("templateId", primary_key=True)
        third_party_id = UUIDProperty("thirdPartyId", primary_key=True)
        third_party_function_code = StringProperty("thirdPartyFunctionCode")
        sensitive_data_flag = BooleanProperty("sensitiveDataFlag")
        created_at = DatetimeProperty("createdAt")
        changed_at = DatetimeProperty("changedAt")

    return (
        ConsentTemplate,
        ConsentTemplateText,
        TemplateThirdPartyPersData,
    )
