"""Sync + async API for the ADMS DocumentRelation entity set."""

from __future__ import annotations

from sap_cloud_sdk.adms._http import (
    AdmsHttp,
    AsyncAdmsHttp,
    build_relation_key_path,
)
from sap_cloud_sdk.adms._models import (
    BusinessObjectNodeChangeLog,
    ChangeLog,
    CreateDocumentRelationInput,
    DeleteBusinessObjectNodeResult,
    Document,
    DocumentRelation,
    DraftActivateInput,
    DraftInput,
)
from sap_cloud_sdk.adms._query_options import ConfigQueryOptions, RelationQueryOptions
from sap_cloud_sdk.adms.config import _SERVICE_PATH
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class _DocumentRelationApi:
    """Operations on the ``DocumentRelation`` entity set and its bound actions.

    Access via :attr:`AdmsClient.relations`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET_ALL)
    def get_all(
        self,
        options: RelationQueryOptions | None = None,
    ) -> list[DocumentRelation]:
        """Query DocumentRelations with OData V4 query options.

        Args:
            options: :class:`RelationQueryOptions` with the OData parameters
                (``filter``, ``select``, ``expand``, ``top``, ``skip``).
                Note: ``$orderby`` is not supported by this entity set.

        Returns:
            List of :class:`~sap_cloud_sdk.adms._models.DocumentRelation`.
        """
        params = options.to_query_params() if options else {}
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
        params: dict = {}
        if expand:
            params["$expand"] = ",".join(expand)
        path = build_relation_key_path(document_relation_id, is_active_entity)
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/GenerateDocumentUploadURLs"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/CompleteMultipartUpload"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/LockDocumentAndRelation"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/UnlockDocumentAndRelation"
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
        path = build_relation_key_path(document_relation_id, is_active_entity)
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
        """Discard draft DocumentRelations without activating."""
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        self._http.post(
            "DiscardBusinessObjNodeDraft",
            json=payload,
            service_base=_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE_BO_NODE)
    def delete_business_object_node(
        self, draft_input: DraftInput
    ) -> DeleteBusinessObjectNodeResult:
        """Delete all DocumentRelations for a business object node.

        Requires ``system-user`` scope.  This is a destructive operation —
        all relations for the given BO node are permanently deleted.

        Args:
            draft_input: Business object node identifier.

        Returns:
            :class:`DeleteBusinessObjectNodeResult` with the number of
            relations deleted.
        """
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        resp = self._http.post(
            "DeleteBusinessObjectNode",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return DeleteBusinessObjectNodeResult.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CHANGELOG_GET_ALL)
    def get_change_logs(
        self, options: ConfigQueryOptions | None = None
    ) -> list[ChangeLog]:
        """Fetch the audit change log for all document management operations.

        Returns:
            List of :class:`~sap_cloud_sdk.adms._models.ChangeLog` entries.
        """
        params = options.to_query_params() if options else {}
        resp = self._http.get("ChangeLog", params=params, service_base=_SERVICE_PATH)
        return [ChangeLog.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_BO_CHANGELOG_GET_ALL)
    def get_bo_node_change_logs(
        self, options: ConfigQueryOptions | None = None
    ) -> list[BusinessObjectNodeChangeLog]:
        """Fetch the change log joined with business object node context.

        Returns:
            List of :class:`~sap_cloud_sdk.adms._models.BusinessObjectNodeChangeLog`.
        """
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "BusinessObjectNodeChangeLog", params=params, service_base=_SERVICE_PATH
        )
        return [
            BusinessObjectNodeChangeLog.from_dict(item)
            for item in resp.json().get("value", [])
        ]


class _AsyncDocumentRelationApi:
    """Async version of :class:`_DocumentRelationApi`.

    Access via :attr:`AsyncAdmsClient.relations`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET_ALL)
    async def get_all(
        self,
        options: RelationQueryOptions | None = None,
    ) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.get_all` — same semantics."""
        params = options.to_query_params() if options else {}
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
        params: dict = {}
        if expand:
            params["$expand"] = ",".join(expand)
        path = build_relation_key_path(document_relation_id, is_active_entity)
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/GenerateDocumentUploadURLs"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/CompleteMultipartUpload"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/LockDocumentAndRelation"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/UnlockDocumentAndRelation"
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
        path = build_relation_key_path(document_relation_id, is_active_entity)
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

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE_BO_NODE)
    async def delete_business_object_node(
        self, draft_input: DraftInput
    ) -> DeleteBusinessObjectNodeResult:
        """Async variant of :meth:`_DocumentRelationApi.delete_business_object_node` — same semantics."""
        payload = {"BusinessObjectNode": draft_input.to_odata_dict()}
        resp = await self._http.post(
            "DeleteBusinessObjectNode",
            json=payload,
            service_base=_SERVICE_PATH,
        )
        return DeleteBusinessObjectNodeResult.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CHANGELOG_GET_ALL)
    async def get_change_logs(
        self, options: ConfigQueryOptions | None = None
    ) -> list[ChangeLog]:
        """Async variant of :meth:`_DocumentRelationApi.get_change_logs` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "ChangeLog", params=params, service_base=_SERVICE_PATH
        )
        return [ChangeLog.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_BO_CHANGELOG_GET_ALL)
    async def get_bo_node_change_logs(
        self, options: ConfigQueryOptions | None = None
    ) -> list[BusinessObjectNodeChangeLog]:
        """Async variant of :meth:`_DocumentRelationApi.get_bo_node_change_logs` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "BusinessObjectNodeChangeLog", params=params, service_base=_SERVICE_PATH
        )
        return [
            BusinessObjectNodeChangeLog.from_dict(item)
            for item in resp.json().get("value", [])
        ]
