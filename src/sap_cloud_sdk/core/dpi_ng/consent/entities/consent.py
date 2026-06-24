"""python-odata entity classes for consentServices."""

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

    class Consent(Service.Entity):
        """OData entity representing a consent record."""

        __odata_collection__ = "consents"
        tenant = StringProperty("tenant")
        consent_id = UUIDProperty("consentId", primary_key=True)
        template_id = UUIDProperty("templateId")
        purpose_id = UUIDProperty("purposeId")
        controller_id = UUIDProperty("controllerId")
        jurisdiction_code = StringProperty("jurisdictionCode")
        consent_model_code = StringProperty("consentModelCode")
        application_id = UUIDProperty("applicationId")
        application_template_id = StringProperty("applicationTemplateId")
        valid_from = DatetimeProperty("validFrom")
        start_of_expiration = DatetimeProperty("startOfExpiration")
        valid_to = DatetimeProperty("validTo")
        data_subject_type_id = UUIDProperty("dataSubjectTypeId")
        data_subject_id = StringProperty("dataSubjectId")
        data_subject_description = StringProperty("dataSubjectDescription")
        granted_at = DatetimeProperty("grantedAt")
        granted_by = StringProperty("grantedBy")
        withdrawn_at = DatetimeProperty("withdrawnAt")
        withdrawn_by = StringProperty("withdrawnBy")
        submission_site = StringProperty("submissionSite")
        outbound_channel = StringProperty("outboundChannel")
        outbound_channel_type_id = UUIDProperty("outboundChannelTypeId")
        language_code = StringProperty("languageCode")
        third_party_id = UUIDProperty("thirdPartyId")
        third_party_function_code = StringProperty("thirdPartyFunctionCode")
        consent_status_code = StringProperty("consentStatusCode")
        lifecycle_status_code = StringProperty("lifecycleStatusCode")
        purpose_description_text_id = StringProperty("purposeDescriptionTextId")
        purpose_explanatory_text_id = StringProperty("purposeExplanatoryTextId")
        template_description_text_id = StringProperty("templateDescriptionTextId")
        template_explanatory_text_id = StringProperty("templateExplanatoryTextId")
        template_question_text_id = StringProperty("templateQuestionTextId")
        template_consequence_text_id = StringProperty("templateConsequenceTextId")
        template_data_privacy_statement_text_id = StringProperty(
            "templateDataPrivacyStatementTextId"
        )
        purpose_sensitive_data_flag = BooleanProperty("purposeSensitiveDataFlag")
        third_party_sensitive_data_flag = BooleanProperty("thirdPartySensitiveDataFlag")
        template_name = StringProperty("templateName")
        purpose_name = StringProperty("purposeName")
        application_name = StringProperty("applicationName")
        application_description = StringProperty("applicationDescription")
        third_party_name = StringProperty("thirdPartyName")
        controller_name = StringProperty("controllerName")
        controller_description = StringProperty("controllerDescription")
        data_subject_type_name = StringProperty("dataSubjectTypeName")
        outbound_channel_type_name = StringProperty("outboundChannelTypeName")
        purpose_description = StringProperty("purposeDescription")
        template_description = StringProperty("templateDescription")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    return (Consent,)
