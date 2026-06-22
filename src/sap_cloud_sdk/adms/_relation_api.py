"""Sync + async API for the ADMS DocumentRelation entity set."""

from __future__ import annotations

from sap_cloud_sdk.adms._keys import build_relation_key_path
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
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
from sap_cloud_sdk.core.odata._query import StructuredQuery
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class _DocumentRelationApi:
    """Operations on the ``DocumentRelation`` entity set and its bound actions.

    Access via :attr:`AdmsClient.relations`.
    """

    def __init__(self, http: ODataHttpTransport) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET_ALL)
    def get_all(
        self,
        options: StructuredQuery | None = None,
    ) -> list[DocumentRelation]:
        """Query DocumentRelations with OData V4 query options.

        Args:
            options: :class:`~sap_cloud_sdk.core.odata.StructuredQuery` with
                OData parameters. Note: ``$orderby`` is not supported by this
                entity set.

        Returns:
            List of :class:`~sap_cloud_sdk.adms._models.DocumentRelation`.
        """
        params = options.to_params() if options else {}
        resp = self._http.get("DocumentRelation", params=params)
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

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
        return DocumentRelation.from_dict(self._http.get(path, params=params))

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE)
    def create(self, input: CreateDocumentRelationInput) -> DocumentRelation:
        """Atomically create a Document and link it to a business object node.

        Args:
            input: Creation parameters including document metadata and BO info.

        Returns:
            :class:`~sap_cloud_sdk.adms._models.DocumentRelation` with embedded
            :class:`~sap_cloud_sdk.adms._models.Document`.
        """
        return DocumentRelation.from_dict(
            self._http.post(
                "CreateDocumentWithRelation",
                json={"DocumentRelation": input.to_odata_dict()},
            )
        )

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
        return Document.from_dict(
            self._http.post(
                build_relation_key_path(document_relation_id, is_active_entity)
                + "/GenerateDocumentUploadURLs",
                json={
                    "DocumentIsMultipart": is_multipart,
                    "DocumentNoOfParts": no_of_parts,
                },
            )
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_COMPLETE_MULTIPART_UPLOAD)
    def complete_multipart_upload(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> None:
        """Signal completion of a multipart upload."""
        self._http.post(
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/CompleteMultipartUpload",
            json={},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_LOCK)
    def lock(self, document_relation_id: str, *, is_active_entity: bool = True) -> None:
        """Lock a document and its relation to prevent concurrent modifications."""
        self._http.post(
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/LockDocumentAndRelation",
            json={},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_UNLOCK)
    def unlock(
        self, document_relation_id: str, *, is_active_entity: bool = True
    ) -> None:
        """Unlock a previously locked document and relation."""
        self._http.post(
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/UnlockDocumentAndRelation",
            json={},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE)
    def delete(
        self, document_relation_id: str, *, is_active_entity: bool = True
    ) -> None:
        """Soft-delete a DocumentRelation (and its linked document)."""
        self._http.delete(
            build_relation_key_path(document_relation_id, is_active_entity)
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE_DRAFT)
    def create_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Create draft DocumentRelations for a business object node."""
        resp = self._http.post(
            "CreateBusinessObjNodeDraft",
            json={"BusinessObjectNode": draft_input.to_odata_dict()},
        )
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_VALIDATE_DRAFT)
    def validate_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Validate draft DocumentRelations before activation."""
        resp = self._http.post(
            "ValidateBusinessObjNodeDraft",
            json={"BusinessObjectNode": draft_input.to_odata_dict()},
        )
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_ACTIVATE_DRAFT)
    def activate_draft(
        self, activate_input: DraftActivateInput
    ) -> list[DocumentRelation]:
        """Activate draft DocumentRelations (make them the active entity)."""
        resp = self._http.post(
            "ActivateBusinessObjNodeDraft",
            json={"BusinessObjectNode": activate_input.to_odata_dict()},
        )
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DISCARD_DRAFT)
    def discard_draft(self, draft_input: DraftInput) -> None:
        """Discard draft DocumentRelations without activating."""
        self._http.post(
            "DiscardBusinessObjNodeDraft",
            json={"BusinessObjectNode": draft_input.to_odata_dict()},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE_BO_NODE)
    def delete_business_object_node(
        self, draft_input: DraftInput
    ) -> DeleteBusinessObjectNodeResult:
        """Delete all DocumentRelations for a business object node."""
        return DeleteBusinessObjectNodeResult.from_dict(
            self._http.post(
                "DeleteBusinessObjectNode",
                json={"BusinessObjectNode": draft_input.to_odata_dict()},
            )
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CHANGELOG_GET_ALL)
    def get_change_logs(
        self, options: StructuredQuery | None = None
    ) -> list[ChangeLog]:
        """Fetch the audit change log for all document management operations."""
        params = options.to_params() if options else {}
        resp = self._http.get("ChangeLog", params=params)
        return [ChangeLog.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_BO_CHANGELOG_GET_ALL)
    def get_bo_node_change_logs(
        self, options: StructuredQuery | None = None
    ) -> list[BusinessObjectNodeChangeLog]:
        """Fetch the change log joined with business object node context."""
        params = options.to_params() if options else {}
        resp = self._http.get("BusinessObjectNodeChangeLog", params=params)
        return [
            BusinessObjectNodeChangeLog.from_dict(item)
            for item in resp.get("value", [])
        ]


class _AsyncDocumentRelationApi:
    """Async version of :class:`_DocumentRelationApi`.

    Access via :attr:`AsyncAdmsClient.relations`.
    """

    def __init__(self, http: AsyncODataHttpTransport) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_GET_ALL)
    async def get_all(
        self, options: StructuredQuery | None = None
    ) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.get_all` — same semantics."""
        params = options.to_params() if options else {}
        resp = await self._http.get("DocumentRelation", params=params)
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

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
        return DocumentRelation.from_dict(await self._http.get(path, params=params))

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE)
    async def create(self, input: CreateDocumentRelationInput) -> DocumentRelation:
        """Async variant of :meth:`_DocumentRelationApi.create` — same semantics."""
        return DocumentRelation.from_dict(
            await self._http.post(
                "CreateDocumentWithRelation",
                json={"DocumentRelation": input.to_odata_dict()},
            )
        )

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
        return Document.from_dict(
            await self._http.post(
                build_relation_key_path(document_relation_id, is_active_entity)
                + "/GenerateDocumentUploadURLs",
                json={
                    "DocumentIsMultipart": is_multipart,
                    "DocumentNoOfParts": no_of_parts,
                },
            )
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_COMPLETE_MULTIPART_UPLOAD)
    async def complete_multipart_upload(
        self, document_relation_id: str, *, is_active_entity: bool = True
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.complete_multipart_upload` — same semantics."""
        await self._http.post(
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/CompleteMultipartUpload",
            json={},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_LOCK)
    async def lock(
        self, document_relation_id: str, *, is_active_entity: bool = True
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.lock` — same semantics."""
        await self._http.post(
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/LockDocumentAndRelation",
            json={},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_UNLOCK)
    async def unlock(
        self, document_relation_id: str, *, is_active_entity: bool = True
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.unlock` — same semantics."""
        await self._http.post(
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/UnlockDocumentAndRelation",
            json={},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE)
    async def delete(
        self, document_relation_id: str, *, is_active_entity: bool = True
    ) -> None:
        """Async variant of :meth:`_DocumentRelationApi.delete` — same semantics."""
        await self._http.delete(
            build_relation_key_path(document_relation_id, is_active_entity)
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_CREATE_DRAFT)
    async def create_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.create_draft` — same semantics."""
        resp = await self._http.post(
            "CreateBusinessObjNodeDraft",
            json={"BusinessObjectNode": draft_input.to_odata_dict()},
        )
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_VALIDATE_DRAFT)
    async def validate_draft(self, draft_input: DraftInput) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.validate_draft` — same semantics."""
        resp = await self._http.post(
            "ValidateBusinessObjNodeDraft",
            json={"BusinessObjectNode": draft_input.to_odata_dict()},
        )
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_ACTIVATE_DRAFT)
    async def activate_draft(
        self, activate_input: DraftActivateInput
    ) -> list[DocumentRelation]:
        """Async variant of :meth:`_DocumentRelationApi.activate_draft` — same semantics."""
        resp = await self._http.post(
            "ActivateBusinessObjNodeDraft",
            json={"BusinessObjectNode": activate_input.to_odata_dict()},
        )
        return [DocumentRelation.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DISCARD_DRAFT)
    async def discard_draft(self, draft_input: DraftInput) -> None:
        """Async variant of :meth:`_DocumentRelationApi.discard_draft` — same semantics."""
        await self._http.post(
            "DiscardBusinessObjNodeDraft",
            json={"BusinessObjectNode": draft_input.to_odata_dict()},
        )

    @record_metrics(Module.ADMS, Operation.ADMS_RELATIONS_DELETE_BO_NODE)
    async def delete_business_object_node(
        self, draft_input: DraftInput
    ) -> DeleteBusinessObjectNodeResult:
        """Async variant of :meth:`_DocumentRelationApi.delete_business_object_node` — same semantics."""
        return DeleteBusinessObjectNodeResult.from_dict(
            await self._http.post(
                "DeleteBusinessObjectNode",
                json={"BusinessObjectNode": draft_input.to_odata_dict()},
            )
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CHANGELOG_GET_ALL)
    async def get_change_logs(
        self, options: StructuredQuery | None = None
    ) -> list[ChangeLog]:
        """Async variant of :meth:`_DocumentRelationApi.get_change_logs` — same semantics."""
        params = options.to_params() if options else {}
        resp = await self._http.get("ChangeLog", params=params)
        return [ChangeLog.from_dict(item) for item in resp.get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_BO_CHANGELOG_GET_ALL)
    async def get_bo_node_change_logs(
        self, options: StructuredQuery | None = None
    ) -> list[BusinessObjectNodeChangeLog]:
        """Async variant of :meth:`_DocumentRelationApi.get_bo_node_change_logs` — same semantics."""
        params = options.to_params() if options else {}
        resp = await self._http.get("BusinessObjectNodeChangeLog", params=params)
        return [
            BusinessObjectNodeChangeLog.from_dict(item)
            for item in resp.get("value", [])
        ]
