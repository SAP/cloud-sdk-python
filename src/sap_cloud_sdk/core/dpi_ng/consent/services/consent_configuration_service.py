"""Service client for consentConfigurationExternalServices."""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

from ..client import _ODataClient
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentConfigurationExternalServices"


class ConsentConfigurationService:
    """Client for consentConfigurationExternalServices - CRUD on reference/configuration data."""

    def __init__(
        self,
        client: _ODataClient,
        *,
        _telemetry_source: Module | None = None,
    ) -> None:
        """Bind entity classes from the consentConfigurationExternalServices endpoint."""
        logger.info("Invoked ConsentConfigurationService.__init__")
        self._client = client
        self._telemetry_source = _telemetry_source
        (
            self.ThirdParty,
            self.Jurisdiction,
            self.JurisdictionText,
            self.Language,
            self.LanguageDescription,
            self.SourceInfo,
            self.Controller,
            self.DataSubjectType,
            self.Application,
            self.MasterDataSource,
            self.OutboundChannelType,
        ) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentConfigurationService.__init__")

    # ------ thirdParties ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_THIRD_PARTIES)
    def list_third_parties(self, **query: Any) -> list[Any]:
        """Return all third-party records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of ThirdParty objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_third_parties")
        result = _apply_query(self._client.query(_SVC, self.ThirdParty), query).all()
        logger.info("Exiting ConsentConfigurationService.list_third_parties")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_THIRD_PARTY)
    def get_third_party(self, third_party_id: str) -> Any:
        """Return a single ThirdParty entity by its UUID.

        Args:
            third_party_id: UUID of the ThirdParty to retrieve.

        Returns:
            The matching ThirdParty object.

        Raises:
            NotFoundError: If no ThirdParty with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_third_party")
        result = self._client.query(_SVC, self.ThirdParty).get(third_party_id)
        logger.info("Exiting ConsentConfigurationService.get_third_party")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_THIRD_PARTY)
    def create_third_party(self, body: dict[str, Any]) -> Any:
        """Create a new ThirdParty entity and return it.

        Args:
            body: Dictionary of field names and values for the new ThirdParty.

        Returns:
            The newly created ThirdParty object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_third_party")
        entity = self.ThirdParty()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_third_party")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_THIRD_PARTY)
    def update_third_party(self, third_party_id: str, body: dict[str, Any]) -> Any:
        """Fetch a ThirdParty by ID, apply field updates, and PATCH it to the service.

        Args:
            third_party_id: UUID of the ThirdParty to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated ThirdParty object.

        Raises:
            NotFoundError: If no ThirdParty with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_third_party")
        entity = self._client.query(_SVC, self.ThirdParty).get(third_party_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_third_party")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_THIRD_PARTY)
    def delete_third_party(self, third_party_id: str) -> None:
        """Delete a ThirdParty entity by its UUID.

        Args:
            third_party_id: UUID of the ThirdParty to delete.

        Raises:
            NotFoundError: If no ThirdParty with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_third_party")
        entity = self._client.query(_SVC, self.ThirdParty).get(third_party_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_third_party")

    # ------ jurisdictions ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_JURISDICTIONS)
    def list_jurisdictions(self, **query: Any) -> list[Any]:
        """Return all jurisdiction records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of Jurisdiction objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_jurisdictions")
        result = _apply_query(self._client.query(_SVC, self.Jurisdiction), query).all()
        logger.info("Exiting ConsentConfigurationService.list_jurisdictions")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_JURISDICTION)
    def get_jurisdiction(self, jurisdiction_id: str) -> Any:
        """Return a single Jurisdiction entity by its UUID.

        Args:
            jurisdiction_id: UUID of the Jurisdiction to retrieve.

        Returns:
            The matching Jurisdiction object.

        Raises:
            NotFoundError: If no Jurisdiction with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_jurisdiction")
        result = self._client.query(_SVC, self.Jurisdiction).get(jurisdiction_id)
        logger.info("Exiting ConsentConfigurationService.get_jurisdiction")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_JURISDICTION)
    def create_jurisdiction(self, body: dict[str, Any]) -> Any:
        """Create a new Jurisdiction entity and return it.

        Args:
            body: Dictionary of field names and values for the new Jurisdiction.

        Returns:
            The newly created Jurisdiction object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_jurisdiction")
        entity = self.Jurisdiction()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_jurisdiction")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_JURISDICTION)
    def update_jurisdiction(self, jurisdiction_id: str, body: dict[str, Any]) -> Any:
        """Fetch a Jurisdiction by ID, apply field updates, and PATCH it to the service.

        Args:
            jurisdiction_id: UUID of the Jurisdiction to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated Jurisdiction object.

        Raises:
            NotFoundError: If no Jurisdiction with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_jurisdiction")
        entity = self._client.query(_SVC, self.Jurisdiction).get(jurisdiction_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_jurisdiction")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_JURISDICTION)
    def delete_jurisdiction(self, jurisdiction_id: str) -> None:
        """Delete a Jurisdiction entity by its UUID.

        Args:
            jurisdiction_id: UUID of the Jurisdiction to delete.

        Raises:
            NotFoundError: If no Jurisdiction with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_jurisdiction")
        entity = self._client.query(_SVC, self.Jurisdiction).get(jurisdiction_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_jurisdiction")

    # ------ jurisdictionTexts ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_JURISDICTION_TEXTS)
    def list_jurisdiction_texts(self, **query: Any) -> list[Any]:
        """Return all jurisdiction text records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of JurisdictionText objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_jurisdiction_texts")
        result = _apply_query(
            self._client.query(_SVC, self.JurisdictionText), query
        ).all()
        logger.info("Exiting ConsentConfigurationService.list_jurisdiction_texts")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_JURISDICTION_TEXT)
    def create_jurisdiction_text(self, body: dict[str, Any]) -> Any:
        """Create a new JurisdictionText entity and return it.

        Args:
            body: Dictionary of field names and values for the new JurisdictionText.
                Must include ``jurisdictionId`` and ``languageCode`` as the composite key.

        Returns:
            The newly created JurisdictionText object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_jurisdiction_text")
        entity = self.JurisdictionText()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_jurisdiction_text")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_JURISDICTION_TEXT)
    def update_jurisdiction_text(
        self, jurisdiction_id: str, language_code: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a JurisdictionText by composite key, apply field updates, and PATCH it to the service.

        Args:
            jurisdiction_id: UUID of the parent Jurisdiction.
            language_code: BCP-47 language code identifying the text entry.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated JurisdictionText object.

        Raises:
            NotFoundError: If no JurisdictionText for the given composite key exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_jurisdiction_text")
        entity = self._client.query(_SVC, self.JurisdictionText).get(
            jurisdictionId=jurisdiction_id, languageCode=language_code
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_jurisdiction_text")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_JURISDICTION_TEXT)
    def delete_jurisdiction_text(
        self, jurisdiction_id: str, language_code: str
    ) -> None:
        """Delete a JurisdictionText entity by its composite key.

        Args:
            jurisdiction_id: UUID of the parent Jurisdiction.
            language_code: BCP-47 language code identifying the text entry to delete.

        Raises:
            NotFoundError: If no JurisdictionText for the given composite key exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_jurisdiction_text")
        entity = self._client.query(_SVC, self.JurisdictionText).get(
            jurisdictionId=jurisdiction_id, languageCode=language_code
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_jurisdiction_text")

    # ------ languages ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_LANGUAGES)
    def list_languages(self, **query: Any) -> list[Any]:
        """Return all language reference records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of Language objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_languages")
        result = _apply_query(self._client.query(_SVC, self.Language), query).all()
        logger.info("Exiting ConsentConfigurationService.list_languages")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_LANGUAGE)
    def get_language(self, language_code: str) -> Any:
        """Return a single Language entity by its BCP-47 code.

        Args:
            language_code: BCP-47 language code of the Language to retrieve.

        Returns:
            The matching Language object.

        Raises:
            NotFoundError: If no Language with the given code exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_language")
        result = self._client.query(_SVC, self.Language).get(language_code)
        logger.info("Exiting ConsentConfigurationService.get_language")
        return result

    # ------ languageDescriptions ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_LANGUAGE_DESCRIPTIONS)
    def list_language_descriptions(self, **query: Any) -> list[Any]:
        """Return all language description records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of LanguageDescription objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_language_descriptions")
        result = _apply_query(
            self._client.query(_SVC, self.LanguageDescription), query
        ).all()
        logger.info("Exiting ConsentConfigurationService.list_language_descriptions")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_LANGUAGE_DESCRIPTION)
    def create_language_description(self, body: dict[str, Any]) -> Any:
        """Create a new LanguageDescription entity and return it.

        Args:
            body: Dictionary of field names and values for the new LanguageDescription.
                Must include ``languageCode`` as the primary key.

        Returns:
            The newly created LanguageDescription object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_language_description")
        entity = self.LanguageDescription()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_language_description")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_LANGUAGE_DESCRIPTION)
    def update_language_description(
        self, language_code: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a LanguageDescription by language code, apply field updates, and PATCH it to the service.

        Args:
            language_code: BCP-47 language code of the LanguageDescription to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated LanguageDescription object.

        Raises:
            NotFoundError: If no LanguageDescription with the given code exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_language_description")
        entity = self._client.query(_SVC, self.LanguageDescription).get(language_code)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_language_description")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_LANGUAGE_DESCRIPTION)
    def delete_language_description(self, language_code: str) -> None:
        """Delete a LanguageDescription entity by its language code.

        Args:
            language_code: BCP-47 language code of the LanguageDescription to delete.

        Raises:
            NotFoundError: If no LanguageDescription with the given code exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_language_description")
        entity = self._client.query(_SVC, self.LanguageDescription).get(language_code)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_language_description")

    # ------ sourceInfos ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_SOURCE_INFOS)
    def list_source_infos(self, **query: Any) -> list[Any]:
        """Return all source info records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of SourceInfo objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_source_infos")
        result = _apply_query(self._client.query(_SVC, self.SourceInfo), query).all()
        logger.info("Exiting ConsentConfigurationService.list_source_infos")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_SOURCE_INFO)
    def get_source_info(self, source_id: str) -> Any:
        """Return a single SourceInfo entity by its UUID.

        Args:
            source_id: UUID of the SourceInfo to retrieve.

        Returns:
            The matching SourceInfo object.

        Raises:
            NotFoundError: If no SourceInfo with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_source_info")
        result = self._client.query(_SVC, self.SourceInfo).get(source_id)
        logger.info("Exiting ConsentConfigurationService.get_source_info")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_SOURCE_INFO)
    def create_source_info(self, body: dict[str, Any]) -> Any:
        """Create a new SourceInfo entity and return it.

        Args:
            body: Dictionary of field names and values for the new SourceInfo.

        Returns:
            The newly created SourceInfo object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_source_info")
        entity = self.SourceInfo()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_source_info")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_SOURCE_INFO)
    def update_source_info(self, source_id: str, body: dict[str, Any]) -> Any:
        """Fetch a SourceInfo by ID, apply field updates, and PATCH it to the service.

        Args:
            source_id: UUID of the SourceInfo to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated SourceInfo object.

        Raises:
            NotFoundError: If no SourceInfo with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_source_info")
        entity = self._client.query(_SVC, self.SourceInfo).get(source_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_source_info")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_SOURCE_INFO)
    def delete_source_info(self, source_id: str) -> None:
        """Delete a SourceInfo entity by its UUID.

        Args:
            source_id: UUID of the SourceInfo to delete.

        Raises:
            NotFoundError: If no SourceInfo with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_source_info")
        entity = self._client.query(_SVC, self.SourceInfo).get(source_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_source_info")

    # ------ controllers ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_CONTROLLERS)
    def list_controllers(self, **query: Any) -> list[Any]:
        """Return all controller records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of Controller objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_controllers")
        result = _apply_query(self._client.query(_SVC, self.Controller), query).all()
        logger.info("Exiting ConsentConfigurationService.list_controllers")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_CONTROLLER)
    def get_controller(self, controller_id: str) -> Any:
        """Return a single Controller entity by its UUID.

        Args:
            controller_id: UUID of the Controller to retrieve.

        Returns:
            The matching Controller object.

        Raises:
            NotFoundError: If no Controller with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_controller")
        result = self._client.query(_SVC, self.Controller).get(controller_id)
        logger.info("Exiting ConsentConfigurationService.get_controller")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_CONTROLLER)
    def create_controller(self, body: dict[str, Any]) -> Any:
        """Create a new Controller entity and return it.

        Args:
            body: Dictionary of field names and values for the new Controller.

        Returns:
            The newly created Controller object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_controller")
        entity = self.Controller()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_controller")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_CONTROLLER)
    def update_controller(self, controller_id: str, body: dict[str, Any]) -> Any:
        """Fetch a Controller by ID, apply field updates, and PATCH it to the service.

        Args:
            controller_id: UUID of the Controller to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated Controller object.

        Raises:
            NotFoundError: If no Controller with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_controller")
        entity = self._client.query(_SVC, self.Controller).get(controller_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_controller")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_CONTROLLER)
    def delete_controller(self, controller_id: str) -> None:
        """Delete a Controller entity by its UUID.

        Args:
            controller_id: UUID of the Controller to delete.

        Raises:
            NotFoundError: If no Controller with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_controller")
        entity = self._client.query(_SVC, self.Controller).get(controller_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_controller")

    # ------ dataSubjectTypes ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_DATA_SUBJECT_TYPES)
    def list_data_subject_types(self, **query: Any) -> list[Any]:
        """Return all data subject type records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of DataSubjectType objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_data_subject_types")
        result = _apply_query(
            self._client.query(_SVC, self.DataSubjectType), query
        ).all()
        logger.info("Exiting ConsentConfigurationService.list_data_subject_types")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_DATA_SUBJECT_TYPE)
    def get_data_subject_type(self, data_subject_type_id: str) -> Any:
        """Return a single DataSubjectType entity by its UUID.

        Args:
            data_subject_type_id: UUID of the DataSubjectType to retrieve.

        Returns:
            The matching DataSubjectType object.

        Raises:
            NotFoundError: If no DataSubjectType with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_data_subject_type")
        result = self._client.query(_SVC, self.DataSubjectType).get(
            data_subject_type_id
        )
        logger.info("Exiting ConsentConfigurationService.get_data_subject_type")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_DATA_SUBJECT_TYPE)
    def create_data_subject_type(self, body: dict[str, Any]) -> Any:
        """Create a new DataSubjectType entity and return it.

        Args:
            body: Dictionary of field names and values for the new DataSubjectType.

        Returns:
            The newly created DataSubjectType object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_data_subject_type")
        entity = self.DataSubjectType()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_data_subject_type")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_DATA_SUBJECT_TYPE)
    def update_data_subject_type(
        self, data_subject_type_id: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a DataSubjectType by ID, apply field updates, and PATCH it to the service.

        Args:
            data_subject_type_id: UUID of the DataSubjectType to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated DataSubjectType object.

        Raises:
            NotFoundError: If no DataSubjectType with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_data_subject_type")
        entity = self._client.query(_SVC, self.DataSubjectType).get(
            data_subject_type_id
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_data_subject_type")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_DATA_SUBJECT_TYPE)
    def delete_data_subject_type(self, data_subject_type_id: str) -> None:
        """Delete a DataSubjectType entity by its UUID.

        Args:
            data_subject_type_id: UUID of the DataSubjectType to delete.

        Raises:
            NotFoundError: If no DataSubjectType with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_data_subject_type")
        entity = self._client.query(_SVC, self.DataSubjectType).get(
            data_subject_type_id
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_data_subject_type")

    # ------ applications ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_APPLICATIONS)
    def list_applications(self, **query: Any) -> list[Any]:
        """Return all application records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of Application objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_applications")
        result = _apply_query(self._client.query(_SVC, self.Application), query).all()
        logger.info("Exiting ConsentConfigurationService.list_applications")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_APPLICATION)
    def get_application(self, application_id: str) -> Any:
        """Return a single Application entity by its UUID.

        Args:
            application_id: UUID of the Application to retrieve.

        Returns:
            The matching Application object.

        Raises:
            NotFoundError: If no Application with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_application")
        result = self._client.query(_SVC, self.Application).get(application_id)
        logger.info("Exiting ConsentConfigurationService.get_application")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_APPLICATION)
    def create_application(self, body: dict[str, Any]) -> Any:
        """Create a new Application entity and return it.

        Args:
            body: Dictionary of field names and values for the new Application.

        Returns:
            The newly created Application object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_application")
        entity = self.Application()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_application")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_APPLICATION)
    def update_application(self, application_id: str, body: dict[str, Any]) -> Any:
        """Fetch an Application by ID, apply field updates, and PATCH it to the service.

        Args:
            application_id: UUID of the Application to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated Application object.

        Raises:
            NotFoundError: If no Application with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_application")
        entity = self._client.query(_SVC, self.Application).get(application_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_application")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_APPLICATION)
    def delete_application(self, application_id: str) -> None:
        """Delete an Application entity by its UUID.

        Args:
            application_id: UUID of the Application to delete.

        Raises:
            NotFoundError: If no Application with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_application")
        entity = self._client.query(_SVC, self.Application).get(application_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_application")

    # ------ masterDataSources ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_MASTER_DATA_SOURCES)
    def list_master_data_sources(self, **query: Any) -> list[Any]:
        """Return all master data source records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of MasterDataSource objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_master_data_sources")
        result = _apply_query(
            self._client.query(_SVC, self.MasterDataSource), query
        ).all()
        logger.info("Exiting ConsentConfigurationService.list_master_data_sources")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_MASTER_DATA_SOURCE)
    def get_master_data_source(self, master_data_source_id: str) -> Any:
        """Return a single MasterDataSource entity by its UUID.

        Args:
            master_data_source_id: UUID of the MasterDataSource to retrieve.

        Returns:
            The matching MasterDataSource object.

        Raises:
            NotFoundError: If no MasterDataSource with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_master_data_source")
        result = self._client.query(_SVC, self.MasterDataSource).get(
            master_data_source_id
        )
        logger.info("Exiting ConsentConfigurationService.get_master_data_source")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_MASTER_DATA_SOURCE)
    def create_master_data_source(self, body: dict[str, Any]) -> Any:
        """Create a new MasterDataSource entity and return it.

        Args:
            body: Dictionary of field names and values for the new MasterDataSource.

        Returns:
            The newly created MasterDataSource object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_master_data_source")
        entity = self.MasterDataSource()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_master_data_source")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_MASTER_DATA_SOURCE)
    def update_master_data_source(
        self, master_data_source_id: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a MasterDataSource by ID, apply field updates, and PATCH it to the service.

        Args:
            master_data_source_id: UUID of the MasterDataSource to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated MasterDataSource object.

        Raises:
            NotFoundError: If no MasterDataSource with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_master_data_source")
        entity = self._client.query(_SVC, self.MasterDataSource).get(
            master_data_source_id
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_master_data_source")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_MASTER_DATA_SOURCE)
    def delete_master_data_source(self, master_data_source_id: str) -> None:
        """Delete a MasterDataSource entity by its UUID.

        Args:
            master_data_source_id: UUID of the MasterDataSource to delete.

        Raises:
            NotFoundError: If no MasterDataSource with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_master_data_source")
        entity = self._client.query(_SVC, self.MasterDataSource).get(
            master_data_source_id
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_master_data_source")

    # ------ outboundChannelTypes ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_OUTBOUND_CHANNEL_TYPES)
    def list_outbound_channel_types(self, **query: Any) -> list[Any]:
        """Return all outbound channel type records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of OutboundChannelType objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.list_outbound_channel_types")
        result = _apply_query(
            self._client.query(_SVC, self.OutboundChannelType), query
        ).all()
        logger.info("Exiting ConsentConfigurationService.list_outbound_channel_types")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_OUTBOUND_CHANNEL_TYPE)
    def get_outbound_channel_type(self, outbound_channel_type_id: str) -> Any:
        """Return a single OutboundChannelType entity by its UUID.

        Args:
            outbound_channel_type_id: UUID of the OutboundChannelType to retrieve.

        Returns:
            The matching OutboundChannelType object.

        Raises:
            NotFoundError: If no OutboundChannelType with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.get_outbound_channel_type")
        result = self._client.query(_SVC, self.OutboundChannelType).get(
            outbound_channel_type_id
        )
        logger.info("Exiting ConsentConfigurationService.get_outbound_channel_type")
        return result

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_OUTBOUND_CHANNEL_TYPE
    )
    def create_outbound_channel_type(self, body: dict[str, Any]) -> Any:
        """Create a new OutboundChannelType entity and return it.

        Args:
            body: Dictionary of field names and values for the new OutboundChannelType.

        Returns:
            The newly created OutboundChannelType object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.create_outbound_channel_type")
        entity = self.OutboundChannelType()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.create_outbound_channel_type")
        return entity

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_OUTBOUND_CHANNEL_TYPE
    )
    def update_outbound_channel_type(
        self, outbound_channel_type_id: str, body: dict[str, Any]
    ) -> Any:
        """Fetch an OutboundChannelType by ID, apply field updates, and PATCH it to the service.

        Args:
            outbound_channel_type_id: UUID of the OutboundChannelType to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated OutboundChannelType object.

        Raises:
            NotFoundError: If no OutboundChannelType with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.update_outbound_channel_type")
        entity = self._client.query(_SVC, self.OutboundChannelType).get(
            outbound_channel_type_id
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentConfigurationService.update_outbound_channel_type")
        return entity

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_OUTBOUND_CHANNEL_TYPE
    )
    def delete_outbound_channel_type(self, outbound_channel_type_id: str) -> None:
        """Delete an OutboundChannelType entity by its UUID.

        Args:
            outbound_channel_type_id: UUID of the OutboundChannelType to delete.

        Raises:
            NotFoundError: If no OutboundChannelType with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentConfigurationService.delete_outbound_channel_type")
        entity = self._client.query(_SVC, self.OutboundChannelType).get(
            outbound_channel_type_id
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentConfigurationService.delete_outbound_channel_type")
