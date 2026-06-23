"""Sync + async API for the ADMS Document entity set."""

from __future__ import annotations

from sap_cloud_sdk.adms._http import (
    AdmsHttp,
    AsyncAdmsHttp,
    build_relation_key_path,
    quote_odata_string_key,
)
from sap_cloud_sdk.adms._models import (
    Document,
    ScanStatus,
    UpdateDocumentInput,
)
from sap_cloud_sdk.adms._query_options import DocumentQueryOptions
from sap_cloud_sdk.adms.config import _SERVICE_PATH
from sap_cloud_sdk.adms.exceptions import ScanNotCleanError
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class _DocumentApi:
    """Operations on the ``Document`` entity set.

    Access via :attr:`AdmsClient.documents`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET_ALL)
    def get_all(
        self,
        options: DocumentQueryOptions | None = None,
    ) -> list[Document]:
        """List all Documents accessible to the caller.

        ADM does not expose ``Document`` as a top-level queryable collection;
        Documents are only reachable as children of ``DocumentRelation``.
        This method transparently queries ``DocumentRelation?$expand=Document``
        and returns the unique set of Documents found across all relations,
        preserving first-seen order.

        ``$filter``, ``$top``, ``$skip``, and ``$orderby`` in *options* are
        applied to the underlying ``DocumentRelation`` query (not to the
        Document entity itself).  ``$select`` and ``$expand`` are forwarded
        as-is; if you need to expand additional navigation properties on
        DocumentRelation alongside ``Document``, include them in
        ``options.expand``.

        Args:
            options: :class:`DocumentQueryOptions` with OData parameters.
                If ``None``, all relations are fetched and their documents
                returned deduplicated.

        Returns:
            Unique :class:`~sap_cloud_sdk.adms._models.Document` instances,
            ordered by first occurrence across relations.
        """
        # Build RelationQueryOptions that always includes Document in $expand.
        rel_params: dict[str, str | int] = {}
        if options:
            rel_params = options.to_query_params()
        existing_expand = str(rel_params.get("$expand", ""))
        if existing_expand:
            if "Document" not in existing_expand.split(","):
                rel_params["$expand"] = existing_expand + ",Document"
        else:
            rel_params["$expand"] = "Document"

        resp = self._http.get(
            "DocumentRelation", params=rel_params, service_base=_SERVICE_PATH
        )
        seen: set[str] = set()
        docs: list[Document] = []
        for rel_data in resp.json().get("value", []):
            doc_data = rel_data.get("Document")
            if not doc_data:
                continue
            doc = Document.from_dict(doc_data)
            if doc.document_id and doc.document_id not in seen:
                seen.add(doc.document_id)
                docs.append(doc)
        return docs

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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/Document"
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
        rel_key = build_relation_key_path(document_relation_id, is_active_entity)
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
            f"DocContentVersionID={quote_odata_string_key(doc_content_version_id)})"
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

        ADM's UpdateDocument action returns only the changed fields.  This
        method transparently follows up with a GET to return the full Document.

        Args:
            document_relation_id: UUID of the parent DocumentRelation.
            update_input: Fields to update (only non-None fields are sent).
            is_active_entity: Active vs draft entity flag.

        Returns:
            Full updated :class:`~sap_cloud_sdk.adms._models.Document`.
        """
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/UpdateDocument"
        )
        payload = {"Document": update_input.to_odata_dict()}
        self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        # UpdateDocument returns only changed fields — fetch the full entity.
        full_path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/Document"
        )
        resp = self._http.get(full_path, service_base=_SERVICE_PATH)
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/RestoreDocumentContentVersion"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/DeleteDocumentContentVersion"
        )
        self._http.post(
            path,
            json={"DocContentVersionID": doc_content_version_id},
            service_base=_SERVICE_PATH,
        )


class _AsyncDocumentApi:
    """Async version of :class:`_DocumentApi`.

    Access via :attr:`AsyncAdmsClient.documents`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET_ALL)
    async def get_all(
        self,
        options: DocumentQueryOptions | None = None,
    ) -> list[Document]:
        """Async variant of :meth:`_DocumentApi.get_all` — same semantics."""
        rel_params: dict[str, str | int] = {}
        if options:
            rel_params = options.to_query_params()
        existing_expand = str(rel_params.get("$expand", ""))
        if existing_expand:
            if "Document" not in existing_expand.split(","):
                rel_params["$expand"] = existing_expand + ",Document"
        else:
            rel_params["$expand"] = "Document"

        resp = await self._http.get(
            "DocumentRelation", params=rel_params, service_base=_SERVICE_PATH
        )
        seen: set[str] = set()
        docs: list[Document] = []
        for rel_data in resp.json().get("value", []):
            doc_data = rel_data.get("Document")
            if not doc_data:
                continue
            doc = Document.from_dict(doc_data)
            if doc.document_id and doc.document_id not in seen:
                seen.add(doc.document_id)
                docs.append(doc)
        return docs

    @record_metrics(Module.ADMS, Operation.ADMS_DOCUMENTS_GET)
    async def get(
        self,
        document_relation_id: str,
        *,
        is_active_entity: bool = True,
    ) -> Document:
        """Async variant of :meth:`_DocumentApi.get` — same semantics."""
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/Document"
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
        rel_key = build_relation_key_path(document_relation_id, is_active_entity)
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
            f"DocContentVersionID={quote_odata_string_key(doc_content_version_id)})"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/UpdateDocument"
        )
        payload = {"Document": update.to_odata_dict()}
        await self._http.post(path, json=payload, service_base=_SERVICE_PATH)
        full_path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/Document"
        )
        resp = await self._http.get(full_path, service_base=_SERVICE_PATH)
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/DeleteDocumentContentVersion"
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
        path = (
            build_relation_key_path(document_relation_id, is_active_entity)
            + "/RestoreDocumentContentVersion"
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
