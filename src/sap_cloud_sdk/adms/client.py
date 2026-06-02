"""ADMS client module — sync and async entry points for the SAP Cloud SDK ADMS module.

Contains:
- Private API classes: _DocumentApi, _DocumentRelationApi, _ConfigurationApi, _JobApi
  and their async counterparts.
- Public client classes: AdmsClient, AsyncAdmsClient.
- Factory functions: create_client, create_async_client.

Usage::

    from sap_cloud_sdk.adms import create_client, create_async_client

    # Sync (service-to-service)
    client = create_client()
    relations = client.relations.get_all(
        filter="HostBusinessObjectNodeID eq 'PO-4500012345'",
        expand=["Document"],
    )

    # Async (FastAPI / LangGraph)
    async with create_async_client() as client:
        relations = await client.relations.get_all(
            filter="HostBusinessObjectNodeID eq 'PO-4500012345'",
            expand=["Document"],
        )
"""

from __future__ import annotations

import httpx

from sap_cloud_sdk.adms._auth import IasTokenFetcher
from sap_cloud_sdk.adms._http import AdmsHttp, AsyncAdmsHttp
from sap_cloud_sdk.adms._models import (
    AllowedDomain,
    BusinessObjectNodeType,
    CreateAllowedDomainInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentTypeInput,
    CreateDocumentRelationInput,
    DeleteUserDataJobParameters,
    Document,
    DocumentRelation,
    DocumentType,
    DocumentTypeBusinessObjectTypeMap,
    DraftActivateInput,
    DraftInput,
    JobOutput,
    JobType,
    ScanStatus,
    UpdateDocumentInput,
    ZipDownloadJobParameters,
)
from sap_cloud_sdk.adms.config import (
    AdmsConfig,
    _ADMIN_SERVICE_PATH,
    _CONFIG_SERVICE_PATH,
    _SERVICE_PATH,
    load_from_env_or_mount,
)
from sap_cloud_sdk.adms.exceptions import (
    ClientCreationError,
    ConfigError,
    ScanNotCleanError,
)
from sap_cloud_sdk.core.auth import TokenCache
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


# ---------------------------------------------------------------------------
# Sync API classes
# ---------------------------------------------------------------------------


class _DocumentApi:
    """Operations on the ``Document`` entity set.

    Access via :attr:`AdmsClient.documents`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET_ALL)
    def get_all(
        self,
        *,
        filter: str | None = None,
        select: list[str] | None = None,
        expand: list[str] | None = None,
        top: int | None = None,
        skip: int | None = None,
        orderby: str | None = None,
    ) -> list[Document]:
        """Query the Document entity set with OData V4 query options.

        Args:
            filter: OData ``$filter`` expression.
            select: Properties to include in the response.
            expand: Navigation properties to inline.
            top: Maximum number of records to return.
            skip: Number of records to skip (paging).
            orderby: OData ``$orderby`` expression.

        Returns:
            List of :class:`~sap_cloud_sdk.adms._models.Document`.
        """
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if select is not None:
            params["$select"] = ",".join(select)
        if expand is not None:
            params["$expand"] = ",".join(expand)
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        if orderby is not None:
            params["$orderby"] = orderby
        resp = self._http.get("Document", params=params, service_base=_SERVICE_PATH)
        return [Document.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET)
    def get(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> Document:
        """Fetch the Document attached to a DocumentRelation.

        Args:
            document_relation_id: UUID of the parent DocumentRelation.
            is_active_entity: ``True`` for the active (non-draft) Document.

        Returns:
            Parsed :class:`~sap_cloud_sdk.adms._models.Document`.

        Raises:
            DocumentNotFoundError: If no relation with this ID exists.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})/Document"
        )
        resp = self._http.get(path, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET_DOWNLOAD_URL)
    def get_download_url(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
        doc_content_version_id: str,
    ) -> str:
        """Return a time-limited presigned download URL for a document.

        Security gate: verifies scan state is ``CLEAN`` before generating the URL.

        Args:
            document_relation_id: UUID of the parent DocumentRelation.
            is_active_entity: Active vs draft entity flag.
            doc_content_version_id: Content version to download (e.g. ``"1.0"``).

        Returns:
            Presigned URL string.

        Raises:
            ScanNotCleanError: If the document is not in ``CLEAN`` scan state.
            DocumentNotFoundError: If the relation/document cannot be found.
        """
        is_active = str(is_active_entity).lower()
        rel_key = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
        )
        expanded = self._http.get(
            f"{rel_key}?$expand=Document",
            service_base=_SERVICE_PATH,
        )
        data = expanded.json()
        doc_data = data.get("Document") or {}
        state_raw = doc_data.get("DocumentState", ScanStatus.PENDING.value)
        try:
            state = ScanStatus(state_raw)
        except ValueError:
            state = ScanStatus.PENDING

        if state != ScanStatus.CLEAN:
            raise ScanNotCleanError(
                f"Cannot download document '{document_relation_id}': "
                f"scan state is '{state.value}'. "
                f"Downloads are only permitted when state is CLEAN."
            )

        fn_key = (
            f"{rel_key}/DownloadDocument("
            f"DocContentVersionID='{doc_content_version_id}')"
        )
        resp = self._http.get(fn_key, service_base=_SERVICE_PATH)
        return resp.json().get("value", "")

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_UPDATE)
    def update(
        self,
        document_relation_id: str,
        update_input: UpdateDocumentInput,
        *,
        is_active_entity: bool = True,
    ) -> Document:
        """Update document metadata via the bound ``UpdateDocument`` action.

        Args:
            document_relation_id: UUID of the parent DocumentRelation.
            update_input: Fields to update (only non-None fields are sent).
            is_active_entity: Active vs draft entity flag.

        Returns:
            Updated :class:`~sap_cloud_sdk.adms._models.Document`.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/UpdateDocument"
        )
        payload = {"Document": update_input.to_odata_dict()}
        resp = self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_RESTORE_CONTENT_VERSION)
    def restore_content_version(
        self,
        document_relation_id: str,
        doc_content_version_id: str,
        *,
        is_active_entity: bool = True,
        comment: str | None = None,
    ) -> Document:
        """Restore a previous content version as the latest.

        Args:
            document_relation_id: UUID of the parent DocumentRelation.
            doc_content_version_id: Version to restore (e.g. ``"1.0"``).
            is_active_entity: Active vs draft entity flag.
            comment: Optional comment recorded on the restored version.

        Returns:
            Updated :class:`~sap_cloud_sdk.adms._models.Document`.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/RestoreDocumentContentVersion"
        )
        payload: dict = {
            "DocumentContentVersion": {
                "DocContentVersionID": doc_content_version_id,
            }
        }
        if comment is not None:
            payload["DocumentContentVersion"]["DocContentVersionComment"] = comment
        resp = self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_DELETE_CONTENT_VERSION)
    def delete_content_version(
        self,
        document_relation_id: str,
        doc_content_version_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Soft-delete a specific content version.

        Args:
            document_relation_id: UUID of the parent DocumentRelation.
            doc_content_version_id: Version to delete.
            is_active_entity: Active vs draft entity flag.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/DeleteDocumentContentVersion"
        )
        self._http.post(
            path,
            json={"DocContentVersionID": doc_content_version_id},
            service_base=_SERVICE_PATH,
        )


class _DocumentRelationApi:
    """Operations on the ``DocumentRelation`` entity set and its bound actions.

    Access via :attr:`AdmsClient.relations`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET_ALL)
    def get_all(
        self,
        *,
        filter: str | None = None,
        expand: list[str] | None = None,
        select: list[str] | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[DocumentRelation]:
        """Query DocumentRelations with OData V4 query options.

        Args:
            filter: OData ``$filter`` expression.
            expand: Navigation properties to inline (e.g. ``["Document"]``).
            select: Properties to include in the response.
            top: Maximum number of records to return.
            skip: Number of records to skip (paging).

        Returns:
            List of :class:`~sap_cloud_sdk.adms._models.DocumentRelation`.
        """
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if expand is not None:
            params["$expand"] = ",".join(expand)
        if select is not None:
            params["$select"] = ",".join(select)
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = self._http.get(
            "DocumentRelation", params=params, service_base=_SERVICE_PATH
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET)
    def get(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
        expand: list[str] | None = None,
    ) -> DocumentRelation:
        """Fetch a single DocumentRelation by primary key.

        Args:
            document_relation_id: UUID of the relation.
            is_active_entity: Active vs draft entity flag.
            expand: Navigation properties to inline (e.g. ``["Document"]``).

        Returns:
            Parsed :class:`~sap_cloud_sdk.adms._models.DocumentRelation`.

        Raises:
            DocumentNotFoundError: If the relation does not exist.
        """
        is_active = str(is_active_entity).lower()
        params: dict = {}
        if expand:
            params["$expand"] = ",".join(expand)
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
        )
        resp = self._http.get(path, params=params, service_base=_SERVICE_PATH)
        return DocumentRelation.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE)
    def create(self, input: CreateDocumentRelationInput) -> DocumentRelation:
        """Atomically create a Document and link it to a business object node.

        Args:
            input: Creation parameters including document metadata and BO info.

        Returns:
            :class:`~sap_cloud_sdk.adms._models.DocumentRelation` with embedded
            :class:`~sap_cloud_sdk.adms._models.Document`.
        """
        payload = {"DocumentRelation": input.to_odata_dict()}
        resp = self._http.post(
            "CreateDocumentWithRelation",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return DocumentRelation.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GENERATE_UPLOAD_URLS)
    def generate_upload_urls(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
        is_multipart: bool = False,
        no_of_parts: int = 1,
    ) -> Document:
        """Generate presigned upload URL(s) for a document.

        Args:
            document_relation_id: UUID of the DocumentRelation.
            is_active_entity: Active vs draft entity flag.
            is_multipart: ``True`` to use multipart upload.
            no_of_parts: Number of parts (must be ≥1).

        Returns:
            :class:`~sap_cloud_sdk.adms._models.Document` with upload URLs.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/GenerateDocumentUploadURLs"
        )
        payload = {
            "DocumentIsMultipart": is_multipart,
            "DocumentNoOfParts": no_of_parts,
        }
        resp = self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_COMPLETE_MULTIPART_UPLOAD)
    def complete_multipart_upload(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Signal completion of a multipart upload.

        Args:
            document_relation_id: UUID of the DocumentRelation.
            is_active_entity: Active vs draft entity flag.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/CompleteMultipartUpload"
        )
        self._http.post(path, json={}, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_LOCK)
    def lock(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Lock a document and its relation to prevent concurrent modifications."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/LockDocumentAndRelation"
        )
        self._http.post(path, json={}, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_UNLOCK)
    def unlock(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Unlock a previously locked document and relation."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/UnlockDocumentAndRelation"
        )
        self._http.post(path, json={}, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE)
    def delete(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Soft-delete a DocumentRelation (and its linked document).

        Args:
            document_relation_id: UUID of the relation to delete.
            is_active_entity: Active vs draft entity flag.
        """
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
        )
        self._http.delete(path, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE_DRAFT)
    def create_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Create draft DocumentRelations for a business object node.

        Args:
            draft_input: Business object node identifier.

        Returns:
            List of draft :class:`~sap_cloud_sdk.adms._models.DocumentRelation`.
        """
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        resp = self._http.post(
            "CreateBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_VALIDATE_DRAFT)
    def validate_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Validate draft DocumentRelations before activation.

        Args:
            draft_input: Business object node identifier.

        Returns:
            List of validated draft relations.
        """
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        resp = self._http.post(
            "ValidateBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_ACTIVATE_DRAFT)
    def activate_draft(
        self, activate_input: DraftActivateInput
    ) -> list[DocumentRelation]:
        """Activate draft DocumentRelations (make them the active entity).

        Args:
            activate_input: Business object node identifier with optional late
                host node ID.

        Returns:
            List of now-active :class:`~sap_cloud_sdk.adms._models.DocumentRelation`.
        """
        payload = {"BusinessObjectNode": activate_input.to_odata_dict()}
        resp = self._http.post(
            "ActivateBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DISCARD_DRAFT)
    def discard_draft(self, draft_input: DraftInput) -> None:
        """Discard draft DocumentRelations without activating.

        Args:
            draft_input: Business object node identifier.
        """
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        self._http.post(
            "DiscardBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )


class _ConfigurationApi:
    """Configuration-service operations.

    Access via :attr:`AdmsClient.config`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_ALLOWED_DOMAINS)
    def get_all_allowed_domains(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[AllowedDomain]:
        """Return all allowed-domain entries visible to the current tenant."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = self._http.get(
            "AllowedDomain", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [AllowedDomain.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_ALLOWED_DOMAIN)
    def create_allowed_domain(self, payload: CreateAllowedDomainInput) -> AllowedDomain:
        """Register a new hostname/protocol combination in the allow-list."""
        resp = self._http.post(
            "AllowedDomain",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return AllowedDomain.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_ALLOWED_DOMAIN)
    def delete_allowed_domain(self, allowed_domain_id: str) -> None:
        """Remove an entry from the domain allow-list."""
        self._http.delete(
            f"AllowedDomain(AllowedDomainID={allowed_domain_id})",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCUMENT_TYPES)
    def get_all_document_types(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[DocumentType]:
        """Return all document type classifications."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = self._http.get(
            "DocumentType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [DocumentType.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCUMENT_TYPE)
    def create_document_type(self, payload: CreateDocumentTypeInput) -> DocumentType:
        """Create a new document type classification."""
        resp = self._http.post(
            "DocumentType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCUMENT_TYPE)
    def delete_document_type(self, document_type_id: str) -> None:
        """Delete a document type classification."""
        self._http.delete(
            f"DocumentType(DocumentTypeID='{document_type_id}')",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_BUSINESS_OBJECT_TYPES)
    def get_all_business_object_types(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[BusinessObjectNodeType]:
        """Return all registered business object node types."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = self._http.get(
            "BusinessObjectNodeType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [
            BusinessObjectNodeType.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_BUSINESS_OBJECT_TYPE)
    def create_business_object_type(
        self, payload: CreateBusinessObjectNodeTypeInput
    ) -> BusinessObjectNodeType:
        """Register a new business object node type."""
        resp = self._http.post(
            "BusinessObjectNodeType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return BusinessObjectNodeType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_BUSINESS_OBJECT_TYPE)
    def delete_business_object_type(
        self, business_object_node_type_unique_id: str
    ) -> None:
        """Delete a business object node type registration."""
        self._http.delete(
            f"BusinessObjectNodeType(BusinessObjectNodeTypeUniqueID='{business_object_node_type_unique_id}')",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCTYPE_BOTYPE_MAPS)
    def get_type_mappings(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[DocumentTypeBusinessObjectTypeMap]:
        """Return all DocumentType ↔ BusinessObjectNodeType mappings."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = self._http.get(
            "DocumentTypeBusinessObjectTypeMap",
            params=params,
            service_base=_CONFIG_SERVICE_PATH,
        )
        return [
            DocumentTypeBusinessObjectTypeMap.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCTYPE_BOTYPE_MAP)
    def create_type_mapping(
        self, payload: CreateDocumentTypeBoTypeMapInput
    ) -> DocumentTypeBusinessObjectTypeMap:
        """Create a DocumentType ↔ BusinessObjectNodeType mapping."""
        resp = self._http.post(
            "DocumentTypeBusinessObjectTypeMap",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentTypeBusinessObjectTypeMap.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCTYPE_BOTYPE_MAP)
    def delete_type_mapping(self, document_type_bo_type_map_id: str) -> None:
        """Delete a DocumentType ↔ BusinessObjectNodeType mapping."""
        self._http.delete(
            f"DocumentTypeBusinessObjectTypeMap("
            f"DocumentTypeBOTypeMapID={document_type_bo_type_map_id})",
            service_base=_CONFIG_SERVICE_PATH,
        )


class _JobApi:
    """Async job operations for the ADMS module.

    Access via :attr:`AdmsClient.jobs`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_ZIP_DOWNLOAD)
    def start_zip_download(self, params: ZipDownloadJobParameters) -> JobOutput:
        """Start a ``ZIP_DOWNLOAD`` job via DocumentService.

        Args:
            params: ZIP download parameters.

        Returns:
            :class:`~sap_cloud_sdk.adms._models.JobOutput` with the ``job_id``.
        """
        payload = {
            "JobInput": {
                "JobType": JobType.ZIP_DOWNLOAD.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        resp = self._http.post("StartJob", json=payload, service_base=_SERVICE_PATH)
        return JobOutput.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_DELETE_USER_DATA)
    def start_delete_user_data(self, params: DeleteUserDataJobParameters) -> JobOutput:
        """Start a ``DELETE_USER_DATA`` job via AdminService (GDPR erasure).

        Args:
            params: User ID to erase.

        Returns:
            :class:`~sap_cloud_sdk.adms._models.JobOutput` with ``job_id``.
        """
        payload = {
            "JobInput": {
                "JobType": JobType.DELETE_USER_DATA.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        resp = self._http.post(
            "StartJob", json=payload, service_base=_ADMIN_SERVICE_PATH
        )
        return JobOutput.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_GET_STATUS)
    def get_status(
        self,
        job_id: str,
        *,
        use_admin_service: bool = False,
    ) -> JobOutput:
        """Poll the status of a running job.

        Args:
            job_id: The ``job_id`` from :meth:`start_zip_download` or
                :meth:`start_delete_user_data`.
            use_admin_service: Set ``True`` when polling a ``DELETE_USER_DATA`` job.

        Returns:
            Current :class:`~sap_cloud_sdk.adms._models.JobOutput`.
        """
        service = _ADMIN_SERVICE_PATH if use_admin_service else _SERVICE_PATH
        path = f"JobStatus(JobID='{job_id}')"
        resp = self._http.get(path, service_base=service)
        return JobOutput.from_dict(resp.json())


# ---------------------------------------------------------------------------
# Async API classes
# ---------------------------------------------------------------------------


class _AsyncDocumentApi:
    """Async version of :class:`_DocumentApi`.

    Access via :attr:`AsyncAdmsClient.documents`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET_ALL)
    async def get_all(
        self,
        *,
        filter: str | None = None,
        select: list[str] | None = None,
        expand: list[str] | None = None,
        top: int | None = None,
        skip: int | None = None,
        orderby: str | None = None,
    ) -> list[Document]:
        """Async variant of :meth:`_DocumentApi.get_all` — same semantics."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if select is not None:
            params["$select"] = ",".join(select)
        if expand is not None:
            params["$expand"] = ",".join(expand)
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        if orderby is not None:
            params["$orderby"] = orderby
        resp = await self._http.get(
            "Document", params=params, service_base=_SERVICE_PATH
        )
        return [Document.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET)
    async def get(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> Document:
        """Async variant of :meth:`_DocumentApi.get` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})/Document"
        )
        resp = await self._http.get(path, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET_DOWNLOAD_URL)
    async def get_download_url(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
        doc_content_version_id: str,
    ) -> str:
        """Async download URL fetch with scan-state gate."""
        is_active = str(is_active_entity).lower()
        rel_key = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
        )
        expanded = await self._http.get(
            f"{rel_key}?$expand=Document",
            service_base=_SERVICE_PATH,
        )
        data = expanded.json()
        doc_data = data.get("Document") or {}
        state_raw = doc_data.get("DocumentState", ScanStatus.PENDING.value)
        try:
            state = ScanStatus(state_raw)
        except ValueError:
            state = ScanStatus.PENDING

        if state != ScanStatus.CLEAN:
            raise ScanNotCleanError(
                f"Cannot download document '{document_relation_id}': "
                f"scan state is '{state.value}'. "
                f"Downloads are only permitted when state is CLEAN."
            )

        fn_key = (
            f"{rel_key}/DownloadDocument("
            f"DocContentVersionID='{doc_content_version_id}')"
        )
        resp = await self._http.get(fn_key, service_base=_SERVICE_PATH)
        return resp.json().get("value", "")

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_UPDATE)
    async def update(
        self,
        document_relation_id: str,
        update: UpdateDocumentInput,
        *,
        is_active_entity: bool = True,
    ) -> Document:
        """Async variant of :meth:`_DocumentApi.update` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/UpdateDocument"
        )
        payload = {"Document": update.to_odata_dict()}
        resp = await self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_DELETE_CONTENT_VERSION)
    async def delete_content_version(
        self,
        document_relation_id: str,
        doc_content_version_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Async variant of :meth:`_DocumentApi.delete_content_version` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/DeleteDocumentContentVersion"
        )
        await self._http.post(
            path,
            json={"DocContentVersionID": doc_content_version_id},
            service_base=_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_RESTORE_CONTENT_VERSION)
    async def restore_content_version(
        self,
        document_relation_id: str,
        doc_content_version_id: str,
        *,
        is_active_entity: bool = True,
        comment: str | None = None,
    ) -> Document:
        """Async variant of :meth:`_DocumentApi.restore_content_version` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/RestoreDocumentContentVersion"
        )
        payload: dict = {
            "DocumentContentVersion": {
                "DocContentVersionID": doc_content_version_id,
            }
        }
        if comment is not None:
            payload["DocumentContentVersion"]["DocContentVersionComment"] = comment
        resp = await self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())


class _AsyncDocumentRelationApi:
    """Async version of :class:`_DocumentRelationApi`.

    Access via :attr:`AsyncAdmsClient.relations`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET_ALL)
    async def get_all(
        self,
        *,
        filter: str | None = None,
        expand: list[str] | None = None,
        select: list[str] | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.get_all` — same semantics."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if expand is not None:
            params["$expand"] = ",".join(expand)
        if select is not None:
            params["$select"] = ",".join(select)
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = await self._http.get(
            "DocumentRelation", params=params, service_base=_SERVICE_PATH
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET)
    async def get(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
        expand: list[str] | None = None,
    ) -> DocumentRelation:
        """Async variant of :meth:`_DocumentRelationApi.get` — same semantics."""
        is_active = str(is_active_entity).lower()
        params: dict = {}
        if expand:
            params["$expand"] = ",".join(expand)
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
        )
        resp = await self._http.get(path, params=params, service_base=_SERVICE_PATH)
        return DocumentRelation.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE)
    async def create(self, input: CreateDocumentRelationInput) -> DocumentRelation:
        """Async variant of :meth:`_DocumentRelationApi.create` — same semantics."""
        payload = {"DocumentRelation": input.to_odata_dict()}
        resp = await self._http.post(
            "CreateDocumentWithRelation",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return DocumentRelation.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GENERATE_UPLOAD_URLS)
    async def generate_upload_urls(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
        is_multipart: bool = False,
        no_of_parts: int = 1,
    ) -> Document:
        """Async variant of :meth:`_DocumentRelationApi.generate_upload_urls` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/GenerateDocumentUploadURLs"
        )
        payload = {
            "DocumentIsMultipart": is_multipart,
            "DocumentNoOfParts": no_of_parts,
        }
        resp = await self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        return Document.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_COMPLETE_MULTIPART_UPLOAD)
    async def complete_multipart_upload(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.complete_multipart_upload` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/CompleteMultipartUpload"
        )
        await self._http.post(path, json={}, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_LOCK)
    async def lock(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.lock` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/LockDocumentAndRelation"
        )
        await self._http.post(path, json={}, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_UNLOCK)
    async def unlock(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.unlock` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
            f"/UnlockDocumentAndRelation"
        )
        await self._http.post(path, json={}, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE)
    async def delete(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.delete` — same semantics."""
        is_active = str(is_active_entity).lower()
        path = (
            f"DocumentRelation("
            f"DocumentRelationID={document_relation_id},"
            f"IsActiveEntity={is_active})"
        )
        await self._http.delete(path, service_base=_SERVICE_PATH)

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE_DRAFT)
    async def create_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.create_draft` — same semantics."""
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        resp = await self._http.post(
            "CreateBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_VALIDATE_DRAFT)
    async def validate_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.validate_draft` — same semantics."""
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        resp = await self._http.post(
            "ValidateBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_ACTIVATE_DRAFT)
    async def activate_draft(
        self, activate_input: DraftActivateInput
    ) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.activate_draft` — same semantics."""
        payload = {"BusinessObjectNode": activate_input.to_odata_dict()}
        resp = await self._http.post(
            "ActivateBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return [
            DocumentRelation.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DISCARD_DRAFT)
    async def discard_draft(self, draft_input: DraftInput) -> None:
        """Async variant of :meth:`_DocumentRelationApi.discard_draft` — same semantics."""
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        await self._http.post(
            "DiscardBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )


class _AsyncConfigurationApi:
    """Async version of :class:`_ConfigurationApi`.

    Access via :attr:`AsyncAdmsClient.config`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_ALLOWED_DOMAINS)
    async def get_all_allowed_domains(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[AllowedDomain]:
        """Async variant of :meth:`_ConfigurationApi.get_all_allowed_domains` — same semantics."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = await self._http.get(
            "AllowedDomain", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [AllowedDomain.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_ALLOWED_DOMAIN)
    async def create_allowed_domain(
        self, payload: CreateAllowedDomainInput
    ) -> AllowedDomain:
        """Async variant of :meth:`_ConfigurationApi.create_allowed_domain` — same semantics."""
        resp = await self._http.post(
            "AllowedDomain",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return AllowedDomain.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_ALLOWED_DOMAIN)
    async def delete_allowed_domain(self, allowed_domain_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_allowed_domain` — same semantics."""
        await self._http.delete(
            f"AllowedDomain(AllowedDomainID={allowed_domain_id})",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCUMENT_TYPES)
    async def get_all_document_types(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[DocumentType]:
        """Async variant of :meth:`_ConfigurationApi.get_all_document_types` — same semantics."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = await self._http.get(
            "DocumentType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [DocumentType.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCUMENT_TYPE)
    async def create_document_type(
        self, payload: CreateDocumentTypeInput
    ) -> DocumentType:
        """Async variant of :meth:`_ConfigurationApi.create_document_type` — same semantics."""
        resp = await self._http.post(
            "DocumentType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCUMENT_TYPE)
    async def delete_document_type(self, document_type_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_document_type` — same semantics."""
        await self._http.delete(
            f"DocumentType(DocumentTypeID='{document_type_id}')",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_BUSINESS_OBJECT_TYPES)
    async def get_all_business_object_types(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[BusinessObjectNodeType]:
        """Async variant of :meth:`_ConfigurationApi.get_all_business_object_types` — same semantics."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = await self._http.get(
            "BusinessObjectNodeType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [
            BusinessObjectNodeType.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_BUSINESS_OBJECT_TYPE)
    async def create_business_object_type(
        self, payload: CreateBusinessObjectNodeTypeInput
    ) -> BusinessObjectNodeType:
        """Async variant of :meth:`_ConfigurationApi.create_business_object_type` — same semantics."""
        resp = await self._http.post(
            "BusinessObjectNodeType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return BusinessObjectNodeType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_BUSINESS_OBJECT_TYPE)
    async def delete_business_object_type(
        self, business_object_node_type_unique_id: str
    ) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_business_object_type` — same semantics."""
        await self._http.delete(
            f"BusinessObjectNodeType(BusinessObjectNodeTypeUniqueID='{business_object_node_type_unique_id}')",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCTYPE_BOTYPE_MAPS)
    async def get_type_mappings(
        self,
        *,
        filter: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[DocumentTypeBusinessObjectTypeMap]:
        """Async variant of :meth:`_ConfigurationApi.get_type_mappings` — same semantics."""
        params: dict = {}
        if filter is not None:
            params["$filter"] = filter
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        resp = await self._http.get(
            "DocumentTypeBusinessObjectTypeMap",
            params=params,
            service_base=_CONFIG_SERVICE_PATH,
        )
        return [
            DocumentTypeBusinessObjectTypeMap.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCTYPE_BOTYPE_MAP)
    async def create_type_mapping(
        self, payload: CreateDocumentTypeBoTypeMapInput
    ) -> DocumentTypeBusinessObjectTypeMap:
        """Async variant of :meth:`_ConfigurationApi.create_type_mapping` — same semantics."""
        resp = await self._http.post(
            "DocumentTypeBusinessObjectTypeMap",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentTypeBusinessObjectTypeMap.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCTYPE_BOTYPE_MAP)
    async def delete_type_mapping(self, document_type_bo_type_map_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_type_mapping` — same semantics."""
        await self._http.delete(
            f"DocumentTypeBusinessObjectTypeMap("
            f"DocumentTypeBOTypeMapID={document_type_bo_type_map_id})",
            service_base=_CONFIG_SERVICE_PATH,
        )


class _AsyncJobApi:
    """Async version of :class:`_JobApi`.

    Access via :attr:`AsyncAdmsClient.jobs`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_ZIP_DOWNLOAD)
    async def start_zip_download(self, params: ZipDownloadJobParameters) -> JobOutput:
        """Start a ``ZIP_DOWNLOAD`` job (async)."""
        payload = {
            "JobInput": {
                "JobType": JobType.ZIP_DOWNLOAD.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        resp = await self._http.post(
            "StartJob", json=payload, service_base=_SERVICE_PATH
        )
        return JobOutput.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_DELETE_USER_DATA)
    async def start_delete_user_data(
        self, params: DeleteUserDataJobParameters
    ) -> JobOutput:
        """Start a ``DELETE_USER_DATA`` job via AdminService (async)."""
        payload = {
            "JobInput": {
                "JobType": JobType.DELETE_USER_DATA.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        resp = await self._http.post(
            "StartJob", json=payload, service_base=_ADMIN_SERVICE_PATH
        )
        return JobOutput.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_GET_STATUS)
    async def get_status(self, job_id: str) -> JobOutput:
        """Poll job status (async) — call until :meth:`JobOutput.job_status.is_terminal`."""
        path = f"JobStatus(JobID='{job_id}')"
        resp = await self._http.get(path, service_base=_SERVICE_PATH)
        return JobOutput.from_dict(resp.json())


# ---------------------------------------------------------------------------
# Public client classes
# ---------------------------------------------------------------------------


class AdmsClient:
    """High-level sync client for the SAP Advanced Document Management OData V4 API.

    Exposes four namespaced API objects:
    - :attr:`documents` — document metadata, download URLs, version management
    - :attr:`relations` — document ↔ business-object links, draft lifecycle, upload URLs
    - :attr:`jobs`      — async bulk download (ZIP) and GDPR erasure jobs
    - :attr:`config`    — tenant configuration (allowed domains, document types, BO node types)

    Do **not** instantiate directly — use :func:`create_client`.
    Use :meth:`with_user_jwt` to obtain a user-context client from an existing one.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http
        self.documents = _DocumentApi(http)
        self.relations = _DocumentRelationApi(http)
        self.jobs = _JobApi(http)
        self.config = _ConfigurationApi(http)

    def with_user_jwt(self, user_jwt: str) -> "AdmsClient":
        """Return a new :class:`AdmsClient` with user-context authentication.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT from the inbound request.

        Returns:
            New :class:`AdmsClient` configured for user-context calls.
        """
        return AdmsClient(self._http.with_user_jwt(user_jwt))


class AsyncAdmsClient:
    """Async high-level client for the SAP Advanced Document Management OData V4 API.

    Use as an async context manager to ensure the underlying ``httpx.AsyncClient``
    is closed when done::

        async with create_async_client() as client:
            rel = await client.relations.create(...)

    Do **not** instantiate directly — use :func:`create_async_client`.
    Use :meth:`with_user_jwt` to obtain a user-context client from an existing one.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http
        self.documents = _AsyncDocumentApi(http)
        self.relations = _AsyncDocumentRelationApi(http)
        self.jobs = _AsyncJobApi(http)
        self.config = _AsyncConfigurationApi(http)

    async def __aenter__(self) -> "AsyncAdmsClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    def with_user_jwt(self, user_jwt: str) -> "AsyncAdmsClient":
        """Return a new :class:`AsyncAdmsClient` with user-context authentication.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT.

        Returns:
            New :class:`AsyncAdmsClient` for user-context calls.
        """
        return AsyncAdmsClient(self._http.with_user_jwt(user_jwt))


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_client(
    *,
    instance: str | None = None,
    config: AdmsConfig | None = None,
    user_jwt: str | None = None,
    token_cache: TokenCache | None = None,
) -> AdmsClient:
    """Create an :class:`AdmsClient` from a mounted secret or environment variables.

    Reads the ADM IAS service binding credentials from:
    1. ``/etc/secrets/appfnd/adms/<instance>/`` (Kubernetes / Kyma mount)
    2. ``CLOUD_SDK_CFG_ADMS_<INSTANCE>_*`` environment variables (fallback)

    Args:
        instance: Logical binding instance name.  Defaults to ``"default"``.
        config: Optional explicit :class:`~sap_cloud_sdk.adms.config.AdmsConfig`.
            When provided, ``instance`` is ignored.
        user_jwt: Optional user JWT for AMS per-user permission enforcement.
        token_cache: Optional pluggable token cache.

    Returns:
        Ready-to-use :class:`AdmsClient`.

    Raises:
        ConfigError: If the binding configuration is missing or incomplete.
        ClientCreationError: If client instantiation fails.
    """
    try:
        if instance is not None and instance == "":
            raise ValueError(
                "instance must not be an empty string; omit it to use 'default'"
            )
        binding = config or load_from_env_or_mount(instance)
        token_fetcher = IasTokenFetcher(config=binding, cache=token_cache)
        http = AdmsHttp(config=binding, token_fetcher=token_fetcher, user_jwt=user_jwt)
        return AdmsClient(http)
    except (ConfigError, ValueError):
        raise
    except Exception as exc:
        raise ClientCreationError(
            f"Failed to create ADMS client for instance '{instance or 'default'}': {exc}"
        ) from exc


def create_async_client(
    *,
    instance: str | None = None,
    config: AdmsConfig | None = None,
    user_jwt: str | None = None,
    token_cache: TokenCache | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> AsyncAdmsClient:
    """Create an :class:`AsyncAdmsClient` from a mounted secret or environment variables.

    Args:
        instance: Logical binding instance name.  Defaults to ``"default"``.
        config: Optional explicit :class:`~sap_cloud_sdk.adms.config.AdmsConfig`.
            When provided, ``instance`` is ignored.
        user_jwt: Optional user JWT for OBO token exchange.
        token_cache: Optional pluggable token cache.
        http_client: Optional ``httpx.AsyncClient`` for testing/customization.

    Returns:
        Ready-to-use :class:`AsyncAdmsClient` (use as async context manager).

    Raises:
        ConfigError: If binding configuration is missing or incomplete.
        ClientCreationError: If client instantiation fails.
    """
    try:
        if instance is not None and instance == "":
            raise ValueError(
                "instance must not be an empty string; omit it to use 'default'"
            )
        binding = config or load_from_env_or_mount(instance)
        token_fetcher = IasTokenFetcher(config=binding, cache=token_cache)
        http = AsyncAdmsHttp(
            config=binding,
            token_fetcher=token_fetcher,
            client=http_client,
            user_jwt=user_jwt,
        )
        return AsyncAdmsClient(http)
    except (ConfigError, ValueError):
        raise
    except Exception as exc:
        raise ClientCreationError(
            f"Failed to create async ADMS client for instance '{instance or 'default'}': {exc}"
        ) from exc
