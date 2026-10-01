"""python-odata entity classes for consentConfigurationExternalServices."""

from __future__ import annotations

from typing import Any

from odata.property import DatetimeProperty, StringProperty, UUIDProperty


def _make_entities(Service: Any) -> tuple:
    """Create and return all entity classes bound to the given ODataService instance."""

    class ThirdParty(Service.Entity):
        """OData entity representing a third-party reference record."""

        __odata_collection__ = "thirdParties"
        tenant = StringProperty("tenant")
        third_party_id = UUIDProperty("thirdPartyId", primary_key=True)
        third_party_name = StringProperty("thirdPartyName")
        formatted_description = StringProperty("formattedDescription")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class Jurisdiction(Service.Entity):
        """OData entity representing a jurisdiction reference record."""

        __odata_collection__ = "jurisdictions"
        tenant = StringProperty("tenant")
        jurisdiction_id = UUIDProperty("jurisdictionId", primary_key=True)
        jurisdiction_code = StringProperty("jurisdictionCode")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class JurisdictionText(Service.Entity):
        """OData entity representing a localised description for a jurisdiction."""

        __odata_collection__ = "jurisdictionTexts"
        jurisdiction_text_id = UUIDProperty("jurisdictionTextId", primary_key=True)
        jurisdiction_code = StringProperty("jurisdictionCode")
        jurisdiction_id = UUIDProperty("jurisdictionId")
        language_code = StringProperty("languageCode")
        description = StringProperty("description")

    class Language(Service.Entity):
        """OData entity representing a language reference record."""

        __odata_collection__ = "languages"
        language_code = StringProperty("languageCode", primary_key=True)
        description = StringProperty("description")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class LanguageDescription(Service.Entity):
        """OData entity representing an additional description for a language."""

        __odata_collection__ = "languageDescriptions"
        language_desc_id = UUIDProperty("languageDescId", primary_key=True)
        language_code = StringProperty("languageCode")
        description_language_code = StringProperty("descriptionLanguageCode")
        description = StringProperty("description")

    class SourceInfo(Service.Entity):
        """OData entity representing a data source reference record."""

        __odata_collection__ = "sourceInfos"
        tenant = StringProperty("tenant")
        source_id = UUIDProperty("sourceId", primary_key=True)
        source_name = StringProperty("sourceName")
        description = StringProperty("description")
        data_url = StringProperty("dataURL")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class Controller(Service.Entity):
        """OData entity representing a data controller reference record."""

        __odata_collection__ = "controllers"
        tenant = StringProperty("tenant")
        controller_id = UUIDProperty("controllerId", primary_key=True)
        controller_name = StringProperty("controllerName")
        source_id = UUIDProperty("sourceId")
        source_name = StringProperty("sourceName")
        description = StringProperty("description")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class DataSubjectType(Service.Entity):
        """OData entity representing a data subject type reference record."""

        __odata_collection__ = "dataSubjectTypes"
        tenant = StringProperty("tenant")
        data_subject_type_id = UUIDProperty("dataSubjectTypeId", primary_key=True)
        data_subject_type_name = StringProperty("dataSubjectTypeName")
        master_data_source_id = UUIDProperty("masterDataSourceId")
        master_data_source_name = StringProperty("masterDataSourceName")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class Application(Service.Entity):
        """OData entity representing an application reference record."""

        __odata_collection__ = "applications"
        tenant = StringProperty("tenant")
        application_id = UUIDProperty("applicationId", primary_key=True)
        application_name = StringProperty("applicationName")
        source_id = UUIDProperty("sourceId")
        source_name = StringProperty("sourceName")
        description = StringProperty("description")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class MasterDataSource(Service.Entity):
        """OData entity representing a master data source reference record."""

        __odata_collection__ = "masterDataSources"
        tenant = StringProperty("tenant")
        master_data_source_id = UUIDProperty("masterDataSourceId", primary_key=True)
        master_data_source_name = StringProperty("masterDataSourceName")
        description = StringProperty("description")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    class OutboundChannelType(Service.Entity):
        """OData entity representing an outbound communication channel type."""

        __odata_collection__ = "outboundChannelTypes"
        tenant = StringProperty("tenant")
        outbound_channel_type_id = UUIDProperty(
            "outboundChannelTypeId", primary_key=True
        )
        outbound_channel_type_name = StringProperty("outboundChannelTypeName")
        description = StringProperty("description")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    return (
        ThirdParty,
        Jurisdiction,
        JurisdictionText,
        Language,
        LanguageDescription,
        SourceInfo,
        Controller,
        DataSubjectType,
        Application,
        MasterDataSource,
        OutboundChannelType,
    )
