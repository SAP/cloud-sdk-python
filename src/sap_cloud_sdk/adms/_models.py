"""Data models for the SAP ADMS (Advanced Document Management Service) module.

This module defines enums and dataclasses for all ADMS entities:
- Enums: ``BaseType``, ``ScanStatus``, ``JobType``, ``JobStatus``
- Document management: ``Document``, ``CreateDocumentInput``, ``UpdateDocumentInput``,
  ``DocumentContentVersion``
- Relations: ``DocumentRelation``, ``CreateDocumentRelationInput``, ``DraftInput``,
  ``DraftActivateInput``
- Configuration: ``AllowedDomain``, ``CreateAllowedDomainInput``, ``DocumentType``,
  ``DocumentTypeText``, ``CreateDocumentTypeInput``, ``BusinessObjectNodeType``,
  ``CreateBusinessObjectNodeTypeInput``, ``DocumentTypeBusinessObjectTypeMap``,
  ``CreateDocumentTypeBoTypeMapInput``
- Jobs: ``ZipDownloadJobParameters``, ``DeleteUserDataJobParameters``, ``JobInput``,
  ``JobOutput``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BaseType(str, Enum):
    """Document base type.

    Attributes:
        DOCUMENT: A file attachment stored in the object store.
        FOLDER: A logical folder grouping documents.
        URL: An external URL reference (no actual file upload).
    """

    DOCUMENT = "D"
    FOLDER = "F"
    URL = "U"


class ScanStatus(str, Enum):
    """Virus scan status for a document or content version.

    After upload, the document is in PENDING state until the scanner reports back.

    Attributes:
        CLEAN: Scan passed — safe to download.
        FAILED: Scan infrastructure failure.  Contact support.
        FILE_EXT_RESTRICTED: Blocked by the tenant's file extension policy.
        PENDING: Upload received; virus scan is in progress.  Retry later.
        QUARANTINED: Virus detected.  Access permanently blocked.
    """

    CLEAN = "CLEAN"
    FAILED = "FAILED"
    FILE_EXT_RESTRICTED = "FILE_EXT_RESTRICTED"
    PENDING = "PENDING"
    QUARANTINED = "QUARANTINED"

    def is_downloadable(self) -> bool:
        """Return ``True`` only when the document is safe to download."""
        return self is ScanStatus.CLEAN


class JobType(str, Enum):
    """Async job types.

    Attributes:
        DELETE_USER_DATA: GDPR user data erasure.
            Only allowed via AdminService.StartJob (system-user auth required).
        ZIP_DOWNLOAD: Package documents into a ZIP archive.
            Only allowed via DocumentService.StartJob.
    """

    DELETE_USER_DATA = "DELETE_USER_DATA"
    ZIP_DOWNLOAD = "ZIP_DOWNLOAD"


class JobStatus(str, Enum):
    """Async job lifecycle states.

    Terminal states: COMPLETED, FAILED, CANCELLED.
    Non-terminal (keep polling): NOT_STARTED, IN_PROGRESS, PAUSED.
    """

    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_STARTED = "NOT_STARTED"
    PAUSED = "PAUSED"

    def is_terminal(self) -> bool:
        """Return ``True`` when the job has reached a final state."""
        return self in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


# ---------------------------------------------------------------------------
# DocumentContentVersion
# ---------------------------------------------------------------------------


@dataclass
class DocumentContentVersion:
    """Represents a single content version of a stored document.

    Each upload of a new file creates a new content version (``1.0``, ``2.0``, …).
    ADM retains all versions; the latest is flagged via
    :attr:`doc_content_version_is_latest`.

    Attributes:
        document_id: Parent document UUID.
        document_is_active_entity: Parent document active/draft flag.
        doc_content_version_id: Version identifier string (e.g. ``"1.0"``).
        doc_content_version_state: Virus scan status for this version.
    """

    document_id: str
    document_is_active_entity: bool
    doc_content_version_id: str
    doc_content_version_state: ScanStatus = ScanStatus.PENDING

    doc_content_version_name: str | None = None
    doc_content_version_comment: str | None = None
    doc_content_version_is_latest: bool | None = None
    doc_content_version_mime_type: str | None = None
    doc_content_version_size_in_byte: int | None = None
    # Internal object-store URI — do not expose to end users.
    doc_content_version_stream_uri: str | None = None
    doc_content_version_content_hash: str | None = None
    doc_content_version_upload_id: str | None = None
    doc_content_version_is_soft_deleted: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> DocumentContentVersion:
        """Parse an OData V4 entity payload into a :class:`DocumentContentVersion`."""
        state_raw = data.get("DocContentVersionState", ScanStatus.PENDING.value)
        try:
            state = ScanStatus(state_raw)
        except ValueError:
            state = ScanStatus.PENDING

        return cls(
            document_id=data.get("DocumentID", ""),
            document_is_active_entity=data.get("IsActiveEntity", True),
            doc_content_version_id=data.get("DocContentVersionID", ""),
            doc_content_version_state=state,
            doc_content_version_name=data.get("DocContentVersionName"),
            doc_content_version_comment=data.get("DocContentVersionComment"),
            doc_content_version_is_latest=data.get("DocContentVersionIsLatest"),
            doc_content_version_mime_type=data.get("DocContentVersionMimeType"),
            doc_content_version_size_in_byte=data.get("DocContentVersionSizeInByte"),
            doc_content_version_stream_uri=data.get("DocContentVersionStreamURI"),
            doc_content_version_content_hash=data.get("DocContentVersionContentHash"),
            doc_content_version_upload_id=data.get("DocContentVersionUploadID"),
            doc_content_version_is_soft_deleted=data.get(
                "DocContentVersionIsSoftDeleted", False
            ),
        )


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """Represents a document entity returned by the ADM OData V4 API.

    A document holds metadata about a stored file, folder, or external URL.
    The actual file bytes live in the object store; use
    :meth:`~sap_cloud_sdk.adms._document.DocumentApi.get_download_url` to obtain
    a time-limited presigned URL for downloading.

    Attributes:
        document_id: Primary key UUID.
        is_active_entity: ``True`` for the active (published) version; ``False`` for drafts.
        document_name: Human-readable file name (max 255 chars).
        document_base_type: ``D`` (file), ``F`` (folder), or ``U`` (URL).
        document_type_id: Tenant-configured document type code (max 10 chars).
        document_state: Current virus scan status.  Only ``CLEAN`` documents
            may be downloaded.
    """

    document_id: str
    is_active_entity: bool
    document_name: str
    document_base_type: BaseType
    document_type_id: str
    document_state: ScanStatus

    document_mime_type: str | None = None
    document_description: str | None = None
    document_size_in_byte: int | None = None
    # Internal object store URI — do NOT expose directly to end users.
    document_content_stream_uri: str | None = None
    # Only populated for BaseType.URL documents.
    document_external_content_url: str | None = None
    document_is_locked: bool = False
    document_is_soft_deleted: bool = False
    has_active_document_entity: bool = False
    has_draft_document_entity: bool = False
    draft_uuid: str | None = None
    # Presigned upload URLs returned by GenerateDocumentUploadURLs.
    document_content_upload_urls: list[str] = field(default_factory=list)
    document_is_multi_referenced: bool | None = None
    document_created_by_user_name: str | None = None
    document_created_at_date_time: str | None = None
    document_changed_by_user_name: str | None = None
    document_changed_at_date_time: str | None = None
    # Human-readable text for the current scan state (e.g. "File Extension Restricted").
    document_state_text: str | None = None
    # SHA-256 or similar hash of the stored content (populated after upload).
    document_content_hash: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Document:
        """Parse an OData V4 entity payload into a :class:`Document`."""
        state_raw = data.get("DocumentState", ScanStatus.PENDING.value)
        try:
            state = ScanStatus(state_raw)
        except ValueError:
            state = ScanStatus.PENDING

        base_type_raw = data.get("DocumentBaseType", BaseType.DOCUMENT.value)
        try:
            base_type = BaseType(base_type_raw)
        except ValueError:
            base_type = BaseType.DOCUMENT

        return cls(
            document_id=data.get("DocumentID", ""),
            is_active_entity=data.get("IsActiveEntity", True),
            document_name=data.get("DocumentName", ""),
            document_base_type=base_type,
            document_type_id=data.get("DocumentTypeID", ""),
            document_state=state,
            document_mime_type=data.get("DocumentMimeType"),
            document_description=data.get("DocumentDescription"),
            document_size_in_byte=data.get("DocumentSizeInByte"),
            document_content_stream_uri=data.get("DocumentContentStreamURI"),
            document_external_content_url=data.get("DocumentExternalContentURL"),
            document_is_locked=data.get("DocumentIsLocked", False),
            document_is_soft_deleted=data.get("DocumentIsSoftDeleted", False),
            has_active_document_entity=data.get("HasActiveDocumentEntity", False),
            has_draft_document_entity=data.get("HasDraftDocumentEntity", False),
            draft_uuid=data.get("DraftUUID"),
            document_content_upload_urls=data.get("DocumentContentUploadURLs") or [],
            document_is_multi_referenced=data.get("DocumentIsMultiReferenced"),
            document_created_by_user_name=data.get("DocumentCreatedByUserName"),
            document_created_at_date_time=data.get("DocumentCreatedAtDateTime"),
            document_changed_by_user_name=data.get("DocumentChangedByUserName"),
            document_changed_at_date_time=data.get("DocumentChangedAtDateTime"),
            document_state_text=data.get("DocumentStateText"),
            document_content_hash=data.get("DocumentContentHash"),
        )


@dataclass
class CreateDocumentInput:
    """Input for creating a new document.

    Used as the ``document`` field of :class:`CreateDocumentRelationInput`.

    Attributes:
        document_name: File name including extension (max 255 chars, required).
        document_base_type: Required.  Use ``D`` for file uploads, ``U`` for URLs.
        document_type_id: Tenant-specific document type code.  Must exist in
            ConfigurationService/DocumentType.
        document_description: Optional free-text description (max 255 chars).
        document_external_content_url: Required only when
            ``document_base_type == BaseType.URL``.
        document_is_multipart: Set ``True`` for multipart uploads.
        document_no_of_parts: Number of parts; required if ``document_is_multipart``.
    """

    document_name: str
    document_base_type: BaseType = BaseType.DOCUMENT
    document_type_id: str | None = None
    document_description: str | None = None
    document_external_content_url: str | None = None
    document_is_multipart: bool = False
    document_no_of_parts: int | None = None

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        out: dict = {
            "DocumentName": self.document_name,
            "DocumentBaseType": self.document_base_type.value,
        }
        if self.document_type_id is not None:
            out["DocumentTypeID"] = self.document_type_id
        if self.document_description is not None:
            out["DocumentDescription"] = self.document_description
        if self.document_external_content_url is not None:
            out["DocumentExternalContentURL"] = self.document_external_content_url
        out["DocumentIsMultipart"] = self.document_is_multipart
        if self.document_no_of_parts is not None:
            out["DocumentNoOfParts"] = self.document_no_of_parts
        return out


@dataclass
class UpdateDocumentInput:
    """Input for updating an existing document.

    All fields are optional — only non-``None`` fields are included in the
    PATCH/action payload.
    """

    document_name: str | None = None
    document_description: str | None = None
    document_type_id: str | None = None
    doc_content_version_comment: str | None = None
    is_content_update: bool | None = None
    document_external_content_url: str | None = None
    document_is_multipart: bool | None = None
    document_no_of_parts: int | None = None

    def to_odata_dict(self) -> dict:
        """Serialise only set fields to the OData payload shape expected by ADM."""
        out: dict = {}
        if self.document_name is not None:
            out["DocumentName"] = self.document_name
        if self.document_description is not None:
            out["DocumentDescription"] = self.document_description
        if self.document_type_id is not None:
            out["DocumentTypeID"] = self.document_type_id
        if self.doc_content_version_comment is not None:
            out["DocContentVersionComment"] = self.doc_content_version_comment
        if self.is_content_update is not None:
            out["IsContentUpdate"] = self.is_content_update
        if self.document_external_content_url is not None:
            out["DocumentExternalContentURL"] = self.document_external_content_url
        if self.document_is_multipart is not None:
            out["DocumentIsMultipart"] = self.document_is_multipart
        if self.document_no_of_parts is not None:
            out["DocumentNoOfParts"] = self.document_no_of_parts
        return out


# ---------------------------------------------------------------------------
# DocumentRelation
# ---------------------------------------------------------------------------


@dataclass
class DraftAdministrativeData:
    """CAP draft administrative metadata returned on draft DocumentRelation records.

    Populated only when the relation is a draft (``IsActiveEntity=false`` and
    ``HasDraftEntity=true``), typically after ``CreateBusinessObjNodeDraft``,
    ``ValidateBusinessObjNodeDraft``, or ``ActivateBusinessObjNodeDraft``.

    Attributes:
        draft_uuid: Internal UUID identifying this draft instance.
        creation_date_time: ISO-8601 timestamp when the draft was created.
        created_by_user: User who created the draft.
        draft_is_created_by_me: Whether the current user created the draft.
        last_change_date_time: ISO-8601 timestamp of the last draft modification.
        last_changed_by_user: User who last modified the draft.
        in_process_by_user: User currently editing the draft (lock owner).
        draft_is_processed_by_me: Whether the current user holds the draft lock.
    """

    draft_uuid: str | None = None
    creation_date_time: str | None = None
    created_by_user: str | None = None
    draft_is_created_by_me: bool | None = None
    last_change_date_time: str | None = None
    last_changed_by_user: str | None = None
    in_process_by_user: str | None = None
    draft_is_processed_by_me: bool | None = None

    @classmethod
    def from_dict(cls, data: dict) -> DraftAdministrativeData:
        return cls(
            draft_uuid=data.get("DraftUUID"),
            creation_date_time=data.get("CreationDateTime"),
            created_by_user=data.get("CreatedByUser"),
            draft_is_created_by_me=data.get("DraftIsCreatedByMe"),
            last_change_date_time=data.get("LastChangeDateTime"),
            last_changed_by_user=data.get("LastChangedByUser"),
            in_process_by_user=data.get("InProcessByUser"),
            draft_is_processed_by_me=data.get("DraftIsProcessedByMe"),
        )


@dataclass
class DocumentRelation:
    """Represents the link between a business object node and a stored document.

    A DocumentRelation is the *link* between a business object node
    (e.g. a Purchase Order line) and a stored document.

    Attributes:
        document_relation_id: Primary key UUID.
        business_object_node_type_unique_id: Identifies the business object type
            (e.g. ``"PurchaseOrder"``).  Max 36 chars.
        host_business_object_node_id: Identifies the specific business object instance
            (e.g. ``"PO-4500012345"``).  Max 50 chars.
        host_business_obj_node_display_id: Human-readable display ID for the BO node.
        document_id: UUID of the linked Document entity.
        document_is_active_entity: Whether the linked Document is the active version.
        is_active_entity: Whether this DocumentRelation record is the active version.
        has_active_entity: Whether an active version of this relation exists.
        has_draft_entity: Whether a draft version of this relation exists.
        document_relation_is_locked: Whether the relation (and its document) is locked.
        document_relation_is_deleted: Whether the relation is soft-deleted.
        document_relation_is_output_relevant: Whether the relation is flagged for output.
        draft_messages: SAP draft validation messages (populated during draft lifecycle).
        draft_administrative_data: CAP draft metadata — only present on draft records
            returned by the draft lifecycle actions (create/validate/activate draft).
        doc_relation_created_by_user_name: User who created the relation.
        doc_relation_created_at_date_time: ISO-8601 creation timestamp.
        doc_relation_changed_by_user_name: User who last modified the relation.
        doc_relation_changed_at_date_time: ISO-8601 last-modified timestamp.
        document: Expanded :class:`Document` — populated when the caller requests
            ``?$expand=Document``.
    """

    document_relation_id: str
    business_object_node_type_unique_id: str
    host_business_object_node_id: str

    host_business_obj_node_display_id: str | None = None
    document_id: str | None = None
    document_is_active_entity: bool | None = None
    is_active_entity: bool | None = None
    has_active_entity: bool = False
    has_draft_entity: bool = False
    document_relation_is_locked: bool = False
    document_relation_is_deleted: bool = False
    document_relation_is_output_relevant: bool = False
    draft_messages: list = field(default_factory=list)
    draft_administrative_data: DraftAdministrativeData | None = None
    document: Document | None = None
    doc_relation_created_by_user_name: str | None = None
    doc_relation_created_at_date_time: str | None = None
    doc_relation_changed_by_user_name: str | None = None
    doc_relation_changed_at_date_time: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> DocumentRelation:
        """Parse an OData V4 entity payload into a :class:`DocumentRelation`."""
        doc_data = data.get("Document") or data.get("document")
        doc = Document.from_dict(doc_data) if doc_data else None

        draft_admin_data = data.get("DraftAdministrativeData")
        draft_admin = (
            DraftAdministrativeData.from_dict(draft_admin_data)
            if draft_admin_data
            else None
        )

        return cls(
            document_relation_id=data.get("DocumentRelationID", ""),
            business_object_node_type_unique_id=data.get(
                "BusinessObjectNodeTypeUniqueID", ""
            ),
            host_business_object_node_id=data.get("HostBusinessObjectNodeID", ""),
            host_business_obj_node_display_id=data.get("HostBusinessObjNodeDisplayID"),
            document_id=data.get("DocumentID"),
            document_is_active_entity=data.get("DocumentIsActiveEntity"),
            is_active_entity=data.get("IsActiveEntity"),
            has_active_entity=data.get("HasActiveEntity", False),
            has_draft_entity=data.get("HasDraftEntity", False),
            document_relation_is_locked=data.get("DocumentRelationIsLocked", False),
            document_relation_is_deleted=data.get("DocumentRelationIsDeleted", False),
            document_relation_is_output_relevant=data.get(
                "DocumentRelationIsOutputRelevant", False
            ),
            draft_messages=data.get("DraftMessages") or [],
            draft_administrative_data=draft_admin,
            document=doc,
            doc_relation_created_by_user_name=data.get("DocRelationCreatedByUserName"),
            doc_relation_created_at_date_time=data.get("DocRelationCreatedAtDateTime"),
            doc_relation_changed_by_user_name=data.get("DocRelationChangedByUserName"),
            doc_relation_changed_at_date_time=data.get("DocRelationChangedAtDateTime"),
        )


@dataclass
class CreateDocumentRelationInput:
    """Input for the ``CreateDocumentWithRelation`` unbound action.

    Attributes:
        business_object_node_type_unique_id: Business object type identifier (required).
        host_business_object_node_id: Business object instance identifier (required).
        document: Document metadata for the new document (required).
        host_business_obj_node_display_id: Optional human-readable BO node ID.
        is_active_entity: ``True`` to create as active; ``False`` for draft.
    """

    business_object_node_type_unique_id: str
    host_business_object_node_id: str
    document: CreateDocumentInput
    host_business_obj_node_display_id: str | None = None
    is_active_entity: bool = True

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        payload: dict = {
            "BusinessObjectNodeTypeUniqueID": self.business_object_node_type_unique_id,
            "HostBusinessObjectNodeID": self.host_business_object_node_id,
            "IsActiveEntity": self.is_active_entity,
            "Document": self.document.to_odata_dict(),
        }
        if self.host_business_obj_node_display_id is not None:
            payload["HostBusinessObjNodeDisplayID"] = (
                self.host_business_obj_node_display_id
            )
        return payload


@dataclass
class DraftInput:
    """Input for draft lifecycle actions.

    Used for CreateBusinessObjNodeDraft, ValidateBusinessObjNodeDraft, and
    DiscardBusinessObjNodeDraft.
    """

    business_object_node_type_unique_id: str
    host_business_object_node_id: str

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "BusinessObjectNodeTypeUniqueID": self.business_object_node_type_unique_id,
            "HostBusinessObjectNodeID": self.host_business_object_node_id,
        }


@dataclass
class DraftActivateInput(DraftInput):
    """Input for ActivateBusinessObjNodeDraft.

    Extends :class:`DraftInput` with an optional late-binding node ID.
    """

    late_host_business_object_node_id: str | None = None

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM (extends parent with the optional ``LateHostBusinessObjectNodeID`` field)."""
        out = super().to_odata_dict()
        if self.late_host_business_object_node_id is not None:
            out["LateHostBusinessObjectNodeID"] = self.late_host_business_object_node_id
        return out


# ---------------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------------


@dataclass
class AllowedDomain:
    """Tenant-level domain allow-list for external URL documents.

    Controls which hostnames are permitted as targets when a document
    with ``BaseType.URL`` is created.

    Attributes:
        allowed_domain_id: Primary key UUID.
        allowed_domain_host_name: Hostname (lower-cased by the server on write).
        allowed_domain_protocol: Protocol, e.g. ``"https"`` (lower-cased).
        allowed_domain_port: Port number the service resolves during URL validation.
            Defaults to the protocol default (443 for https, 80 for http) when
            not explicitly stored.
    """

    allowed_domain_id: str
    allowed_domain_host_name: str
    allowed_domain_protocol: str
    allowed_domain_port: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> AllowedDomain:
        return cls(
            allowed_domain_id=data.get("AllowedDomainID", ""),
            allowed_domain_host_name=data.get("AllowedDomainHostName", ""),
            allowed_domain_protocol=data.get("AllowedDomainProtocol", ""),
            allowed_domain_port=data.get("AllowedDomainPort"),
        )

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        d: dict = {
            "AllowedDomainHostName": self.allowed_domain_host_name,
            "AllowedDomainProtocol": self.allowed_domain_protocol,
        }
        if self.allowed_domain_port is not None:
            d["AllowedDomainPort"] = self.allowed_domain_port
        return d


@dataclass
class CreateAllowedDomainInput:
    """Input for creating an :class:`AllowedDomain` entry.

    Attributes:
        host_name: Hostname to allow (e.g. ``"storage.example.com"``).
        protocol: Protocol to allow (``"https"`` or ``"http"``).
        port: Port to allow.  Must match the port in the document URL (the
            service resolves omitted ports to their protocol default: 443 for
            https, 80 for http).  Leave ``None`` to use the protocol default.
    """

    host_name: str
    protocol: str
    port: int | None = None

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        d: dict = {
            "AllowedDomainHostName": self.host_name,
            "AllowedDomainProtocol": self.protocol,
        }
        if self.port is not None:
            d["AllowedDomainPort"] = self.port
        return d


@dataclass
class UpdateAllowedDomainInput:
    """Input for updating an existing :class:`AllowedDomain` entry (PATCH).

    Only non-``None`` fields are included in the PATCH payload.

    Attributes:
        host_name: New hostname.
        protocol: New protocol (``"https"`` or ``"http"``).
        port: New port.  Pass ``0`` to explicitly clear an existing port.
    """

    host_name: str | None = None
    protocol: str | None = None
    port: int | None = None

    def to_odata_dict(self) -> dict:
        """Serialise only non-None fields to the OData PATCH payload."""
        d: dict = {}
        if self.host_name is not None:
            d["AllowedDomainHostName"] = self.host_name
        if self.protocol is not None:
            d["AllowedDomainProtocol"] = self.protocol
        if self.port is not None:
            d["AllowedDomainPort"] = self.port
        return d


@dataclass
class DocumentTypeText:
    """Localization entry for a :class:`DocumentType` (CAP ``texts`` deep-insert).

    Pass one or more of these in :attr:`CreateDocumentTypeInput.texts` to set
    locale-specific names at create time.

    Attributes:
        locale: BCP-47 locale code, e.g. ``"en"`` or ``"de"``.
        document_type_id: Must match the parent ``DocumentTypeID``.
        document_type_name: Locale-specific label.
    """

    locale: str
    document_type_id: str
    document_type_name: str

    @classmethod
    def from_dict(cls, data: dict) -> DocumentTypeText:
        return cls(
            locale=data.get("locale", ""),
            document_type_id=data.get("DocumentTypeID", ""),
            document_type_name=data.get("DocumentTypeName", ""),
        )

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "locale": self.locale,
            "DocumentTypeID": self.document_type_id,
            "DocumentTypeName": self.document_type_name,
        }


@dataclass
class DocumentType:
    """Tenant-configured document type (classification for documents).

    ADM enforces AMS policies per document type.  Each
    :class:`DocumentRelation` references a document type via its linked Document.

    Attributes:
        document_type_id: Short code, max 10 chars (e.g. ``"INVOICE"``).
        document_type_name: Human-readable label (max 40 chars).
        document_type_description: Optional longer description (max 255 chars).
    """

    document_type_id: str
    document_type_name: str
    document_type_description: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> DocumentType:
        return cls(
            document_type_id=data.get("DocumentTypeID", ""),
            document_type_name=data.get("DocumentTypeName", ""),
            document_type_description=data.get("DocumentTypeDescription"),
        )

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        d: dict = {
            "DocumentTypeID": self.document_type_id,
            "DocumentTypeName": self.document_type_name,
        }
        if self.document_type_description is not None:
            d["DocumentTypeDescription"] = self.document_type_description
        return d


@dataclass
class CreateDocumentTypeInput:
    """Input for creating a :class:`DocumentType`.

    Attributes:
        document_type_id: Short code, max 10 chars (e.g. ``"INVOICE"``).
        document_type_name: Default (fallback) label, max 40 chars.
        document_type_description: Optional longer description, max 255 chars.
        texts: Optional locale-specific labels.  Use this for deep-inserting
            translations at create time (CAP ``texts`` navigation property).
            Example::

                CreateDocumentTypeInput(
                    document_type_id="INVOICE",
                    document_type_name="Invoice",
                    texts=[
                        DocumentTypeText(locale="en", document_type_id="INVOICE", document_type_name="Invoice"),
                        DocumentTypeText(locale="de", document_type_id="INVOICE", document_type_name="Rechnung"),
                    ],
                )
    """

    document_type_id: str
    document_type_name: str
    document_type_description: str | None = None
    texts: list[DocumentTypeText] | None = None

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        d: dict = {
            "DocumentTypeID": self.document_type_id,
            "DocumentTypeName": self.document_type_name,
        }
        if self.document_type_description is not None:
            d["DocumentTypeDescription"] = self.document_type_description
        if self.texts:
            d["texts"] = [t.to_odata_dict() for t in self.texts]
        return d


@dataclass
class UpdateDocumentTypeInput:
    """Input for updating an existing :class:`DocumentType` (PATCH).

    Only non-``None`` fields are included in the PATCH payload.

    Attributes:
        document_type_name: New human-readable label.
        document_type_description: New description.
    """

    document_type_name: str | None = None
    document_type_description: str | None = None

    def to_odata_dict(self) -> dict:
        d: dict = {}
        if self.document_type_name is not None:
            d["DocumentTypeName"] = self.document_type_name
        if self.document_type_description is not None:
            d["DocumentTypeDescription"] = self.document_type_description
        return d


@dataclass
class BusinessObjectNodeType:
    """Tenant-configured business object node type.

    Each :class:`DocumentRelation` is anchored to a
    ``BusinessObjectNodeTypeUniqueID`` (e.g. ``"PurchaseOrder"``).  The node
    type must be registered here before relations can be created.

    Attributes:
        business_object_node_type_unique_id: UUID primary key (max 36 chars).
        business_object_node_type: Short identifier code (max 30 chars),
            e.g. ``"PO"``. Note: the CDS field name is ``BusinessObjectNodeType``
            (not ``BusinessObjectNodeTypeID``).
        business_object_node_type_name: Human-readable label (max 50 chars).
        odm_entity_name: Optional ODM (One Domain Model) entity name.
        application_tenant_id: Tenant identifier this BO type belongs to.
    """

    business_object_node_type_unique_id: str
    business_object_node_type: str
    business_object_node_type_name: str
    odm_entity_name: str | None = None
    application_tenant_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> BusinessObjectNodeType:
        return cls(
            business_object_node_type_unique_id=data.get(
                "BusinessObjectNodeTypeUniqueID", ""
            ),
            business_object_node_type=data.get("BusinessObjectNodeType", ""),
            business_object_node_type_name=data.get("BusinessObjectNodeTypeName", ""),
            odm_entity_name=data.get("ODMEntityName"),
            application_tenant_id=data.get("ApplicationTenantID"),
        )

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "BusinessObjectNodeType": self.business_object_node_type,
            "BusinessObjectNodeTypeName": self.business_object_node_type_name,
        }


@dataclass
class CreateBusinessObjectNodeTypeInput:
    """Input for creating a :class:`BusinessObjectNodeType`.

    Attributes:
        business_object_node_type: Short identifier code (max 30 chars), e.g. ``"PO"``.
        business_object_node_type_name: Human-readable label (max 50 chars).
        application_tenant_id: Tenant this BO type belongs to.
    """

    business_object_node_type: str
    business_object_node_type_name: str
    application_tenant_id: str

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "BusinessObjectNodeType": self.business_object_node_type,
            "BusinessObjectNodeTypeName": self.business_object_node_type_name,
            "ApplicationTenantID": self.application_tenant_id,
        }


@dataclass
class UpdateBusinessObjectNodeTypeInput:
    """Input for updating an existing :class:`BusinessObjectNodeType` (PATCH).

    Only non-``None`` fields are included in the PATCH payload.

    Attributes:
        business_object_node_type: New short identifier code.
        business_object_node_type_name: New human-readable label.
    """

    business_object_node_type: str | None = None
    business_object_node_type_name: str | None = None

    def to_odata_dict(self) -> dict:
        d: dict = {}
        if self.business_object_node_type is not None:
            d["BusinessObjectNodeType"] = self.business_object_node_type
        if self.business_object_node_type_name is not None:
            d["BusinessObjectNodeTypeName"] = self.business_object_node_type_name
        return d


@dataclass
class DocumentTypeBusinessObjectTypeMap:
    """Mapping that controls which document types are allowed for a business object node type.

    Must be created before consumers can attach documents of a given type
    to a business object.

    Attributes:
        document_type_bo_type_map_id: Primary key UUID.
        business_object_node_type_unique_id: FK to :class:`BusinessObjectNodeType`.
        document_type_id: FK to :class:`DocumentType`.
        is_default: If ``True`` this is the default type for the BO node type.
    """

    document_type_bo_type_map_id: str
    business_object_node_type_unique_id: str
    document_type_id: str
    is_default: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> DocumentTypeBusinessObjectTypeMap:
        return cls(
            document_type_bo_type_map_id=data.get("DocumentTypeBOTypeMapID", ""),
            business_object_node_type_unique_id=data.get(
                "BusinessObjectNodeTypeUniqueID", ""
            ),
            document_type_id=data.get("DocumentTypeID", ""),
            is_default=data.get("IsDefault", False),
        )

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "BusinessObjectNodeTypeUniqueID": self.business_object_node_type_unique_id,
            "DocumentTypeID": self.document_type_id,
            "IsDefault": self.is_default,
        }


@dataclass
class CreateDocumentTypeBoTypeMapInput:
    """Input for creating a :class:`DocumentTypeBusinessObjectTypeMap`.

    Attributes:
        business_object_node_type_unique_id: The BO node type UUID to map.
        document_type_id: The document type code to allow.
        is_default: Whether this mapping is the default for the BO node type.
    """

    business_object_node_type_unique_id: str
    document_type_id: str
    is_default: bool = False

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "BusinessObjectNodeTypeUniqueID": self.business_object_node_type_unique_id,
            "DocumentTypeID": self.document_type_id,
            "IsDefault": self.is_default,
        }


# ---------------------------------------------------------------------------
# Job models
# ---------------------------------------------------------------------------


@dataclass
class ZipDownloadJobParameters:
    """Parameters for a ``ZIP_DOWNLOAD`` job (DocumentService only).

    Instructs ADM to package the specified documents into a ZIP archive for
    bulk download.

    Attributes:
        business_object_node_type_unique_id: Business object type identifier.
        host_business_object_node_id: Business object instance identifier.
        is_active_entity: Whether to ZIP active (``True``) or draft documents.
        document_relation_ids: Specific relation IDs to include.
            An empty list means "include all relations for this BO node".
    """

    business_object_node_type_unique_id: str
    host_business_object_node_id: str
    is_active_entity: bool = True
    document_relation_ids: list[str] = field(default_factory=list)

    def to_odata_dict(self) -> dict[str, Any]:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "BusinessObjectNodeTypeUniqueID": self.business_object_node_type_unique_id,
            "HostBusinessObjectNodeID": self.host_business_object_node_id,
            "DocumentRelationIDs": self.document_relation_ids,
            "IsActiveEntity": self.is_active_entity,
        }


@dataclass
class DeleteUserDataJobParameters:
    """Parameters for a ``DELETE_USER_DATA`` job (AdminService only).

    Fulfils GDPR right-of-erasure requests by replacing all references to a
    user across Document and DocumentRelation audit fields.

    Attributes:
        user_id: The user whose data should be erased (required).
        replacement_user_id: Replacement display name; defaults to ``"SYSTEM"``
            if not provided.
    """

    user_id: str
    replacement_user_id: str | None = None

    def to_odata_dict(self) -> dict[str, Any]:
        """Serialise to the OData payload shape expected by ADM."""
        out: dict[str, Any] = {"UserID": self.user_id}
        if self.replacement_user_id is not None:
            out["ReplacementUserID"] = self.replacement_user_id
        return out


@dataclass
class JobInput:
    """Generic job input.

    Prefer the typed helper methods on :class:`~sap_cloud_sdk.adms._job.JobApi`
    (:meth:`start_zip_download`, :meth:`start_delete_user_data`) rather than
    constructing this directly.
    """

    job_type: JobType
    job_parameters: dict[str, Any] = field(default_factory=dict)

    def to_odata_dict(self) -> dict:
        """Serialise to the OData payload shape expected by ADM."""
        return {
            "JobInput": {
                "JobType": self.job_type.value,
                "JobParameters": self.job_parameters,
            }
        }


@dataclass
class JobOutput:
    """ADM job result.

    Returned by :meth:`~sap_cloud_sdk.adms._job.JobApi.start_zip_download`,
    :meth:`~sap_cloud_sdk.adms._job.JobApi.start_delete_user_data`, and
    :meth:`~sap_cloud_sdk.adms._job.JobApi.get_status`.

    Poll :meth:`~sap_cloud_sdk.adms._job.JobApi.get_status` until
    ``job_status.is_terminal()`` returns ``True``.
    """

    job_id: str | None = None
    job_status: JobStatus | None = None
    job_result: dict[str, Any] | None = None
    job_error_details: dict[str, Any] | None = None
    job_progress_percentage: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> JobOutput:
        # OData functions return value under "value" key
        raw = data.get("value", data)
        status_raw = raw.get("JobStatus")
        try:
            status = JobStatus(status_raw) if status_raw else None
        except ValueError:
            status = None

        return cls(
            job_id=raw.get("JobID"),
            job_status=status,
            job_result=raw.get("JobResult"),
            job_error_details=raw.get("JobErrorDetails"),
            job_progress_percentage=raw.get("JobProgressPercentage"),
        )


# ---------------------------------------------------------------------------
# ChangeLog / audit models
# ---------------------------------------------------------------------------


@dataclass
class ChangeLog:
    """A single audit entry tracking a property change in ADM.

    Read-only entity from ``GET /DocumentService/ChangeLog``.

    Attributes:
        change_log_id: Primary key UUID.
        change_log_created_at_date_time: When the change was recorded.
        change_log_created_by_user_name: User who made the change.
        change_log_group_id: Groups related change entries together.
        change_log_root_entity: Root entity where the change originated.
        change_log_root_identifier: Identifier of the root entity.
        changed_property_name: The attribute/property that was changed.
        changed_property_old_value: Previous value.
        changed_property_new_value: New value.
        changed_property_data_type: Data type of the changed property.
        change_log_target_entity: Target entity affected by the change.
        change_log_target_identifier: Identifier of the target entity.
        change_log_path: Path to the changed element.
        change_log_modification_type: "create", "update", or "delete".
        change_log_description: Human-readable description of the change.
        is_active_entity: Whether this is an active (non-draft) entry.
        business_object_node_type_unique_id: BO type context.
        host_business_object_node_id: BO instance context.
        document_type_id: Document type context.
        document_name: Document name context.
    """

    change_log_id: str
    change_log_created_at_date_time: str | None = None
    change_log_created_by_user_name: str | None = None
    change_log_group_id: str | None = None
    change_log_root_entity: str | None = None
    change_log_root_identifier: str | None = None
    changed_property_name: str | None = None
    changed_property_old_value: str | None = None
    changed_property_new_value: str | None = None
    changed_property_data_type: str | None = None
    change_log_target_entity: str | None = None
    change_log_target_identifier: str | None = None
    change_log_path: str | None = None
    change_log_modification_type: str | None = None
    change_log_description: str | None = None
    is_active_entity: bool = True
    business_object_node_type_unique_id: str | None = None
    host_business_object_node_id: str | None = None
    document_type_id: str | None = None
    document_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> ChangeLog:
        return cls(
            change_log_id=data.get("ChangeLogID", ""),
            change_log_created_at_date_time=data.get("ChangeLogCreatedAtDateTime"),
            change_log_created_by_user_name=data.get("ChangeLogCreatedByUserName"),
            change_log_group_id=data.get("ChangeLogGroupID"),
            change_log_root_entity=data.get("ChangeLogRootEntity"),
            change_log_root_identifier=data.get("ChangeLogRootIdentifier"),
            changed_property_name=data.get("ChangedPropertyName"),
            changed_property_old_value=data.get("ChangedPropertyOldValue"),
            changed_property_new_value=data.get("ChangedPropertyNewValue"),
            changed_property_data_type=data.get("ChangedPropertyDataType"),
            change_log_target_entity=data.get("ChangeLogTargetEntity"),
            change_log_target_identifier=data.get("ChangeLogTargetIdentifier"),
            change_log_path=data.get("ChangeLogPath"),
            change_log_modification_type=data.get("ChangeLogModificationType"),
            change_log_description=data.get("ChangeLogDescription"),
            is_active_entity=data.get("IsActiveEntity", True),
            business_object_node_type_unique_id=data.get(
                "BusinessObjectNodeTypeUniqueID"
            ),
            host_business_object_node_id=data.get("HostBusinessObjectNodeID"),
            document_type_id=data.get("DocumentTypeID"),
            document_name=data.get("DocumentName"),
        )


@dataclass
class BusinessObjectNodeChangeLog:
    """Change log entry joined with DocumentRelation context.

    Read-only view from ``GET /DocumentService/BusinessObjectNodeChangeLog``.
    Same fields as :class:`ChangeLog` but always has BO node context.
    """

    change_log_id: str
    business_object_node_type_unique_id: str | None = None
    host_business_object_node_id: str | None = None
    document_type_id: str | None = None
    document_name: str | None = None
    change_log_root_entity: str | None = None
    change_log_root_identifier: str | None = None
    change_log_target_identifier: str | None = None
    changed_property_name: str | None = None
    change_log_modification_type: str | None = None
    changed_property_old_value: str | None = None
    changed_property_new_value: str | None = None
    change_log_description: str | None = None
    change_log_is_active_entity: bool = True
    change_log_created_at_date_time: str | None = None
    change_log_created_by_user_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> BusinessObjectNodeChangeLog:
        return cls(
            change_log_id=data.get("ChangeLogID", ""),
            business_object_node_type_unique_id=data.get(
                "BusinessObjectNodeTypeUniqueID"
            ),
            host_business_object_node_id=data.get("HostBusinessObjectNodeID"),
            document_type_id=data.get("DocumentTypeID"),
            document_name=data.get("DocumentName"),
            change_log_root_entity=data.get("ChangeLogRootEntity"),
            change_log_root_identifier=data.get("ChangeLogRootIdentifier"),
            change_log_target_identifier=data.get("ChangeLogTargetIdentifier"),
            changed_property_name=data.get("ChangedPropertyName"),
            change_log_modification_type=data.get("ChangeLogModificationType"),
            changed_property_old_value=data.get("ChangedPropertyOldValue"),
            changed_property_new_value=data.get("ChangedPropertyNewValue"),
            change_log_description=data.get("ChangeLogDescription"),
            change_log_is_active_entity=data.get("ChangeLogIsActiveEntity", True),
            change_log_created_at_date_time=data.get("ChangeLogCreatedAtDateTime"),
            change_log_created_by_user_name=data.get("ChangeLogCreatedByUserName"),
        )


@dataclass
class DeleteBusinessObjectNodeResult:
    """Result of ``DeleteBusinessObjectNode`` action.

    Attributes:
        relations_deleted: Number of DocumentRelations that were deleted.
    """

    relations_deleted: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> DeleteBusinessObjectNodeResult:
        raw = data.get("value", data)
        return cls(relations_deleted=raw.get("RelationsDeleted"))


# ---------------------------------------------------------------------------
# FileExtensionPolicy model
# ---------------------------------------------------------------------------


class MimeTypePolicy(str, Enum):
    """Controls whether a file extension is allowed or blocked."""

    ALLOW = "A"
    BLOCK = "B"


@dataclass
class FileExtensionPolicy:
    """Tenant-level file extension allow/block policy.

    ADM checks this list before accepting an upload.

    Attributes:
        file_extension_policy_id: Primary key UUID.
        file_extension_policy_option: ``ALLOW`` (``"A"``) or ``BLOCK`` (``"B"``).
        file_extension: File extension string, e.g. ``"pdf"``, ``"exe"``.
    """

    file_extension_policy_id: str
    file_extension_policy_option: MimeTypePolicy
    file_extension: str

    @classmethod
    def from_dict(cls, data: dict) -> FileExtensionPolicy:
        option_raw = data.get("FileExtensionPolicyOption", MimeTypePolicy.ALLOW.value)
        try:
            option = MimeTypePolicy(option_raw)
        except ValueError:
            option = MimeTypePolicy.ALLOW
        return cls(
            file_extension_policy_id=data.get("FileExtensionPolicyID", ""),
            file_extension_policy_option=option,
            file_extension=data.get("FileExtension", ""),
        )

    def to_odata_dict(self) -> dict:
        return {
            "FileExtensionPolicyOption": self.file_extension_policy_option.value,
            "FileExtension": self.file_extension,
        }


@dataclass
class CreateFileExtensionPolicyInput:
    """Input for creating a :class:`FileExtensionPolicy` entry.

    Attributes:
        file_extension_policy_option: ``MimeTypePolicy.ALLOW`` or ``MimeTypePolicy.BLOCK``.
        file_extension: File extension to allow/block (e.g. ``"pdf"``).
    """

    file_extension_policy_option: MimeTypePolicy
    file_extension: str

    def to_odata_dict(self) -> dict:
        return {
            "FileExtensionPolicyOption": self.file_extension_policy_option.value,
            "FileExtension": self.file_extension,
        }


# ---------------------------------------------------------------------------
# ApplicationTenant model
# ---------------------------------------------------------------------------


@dataclass
class ApplicationTenant:
    """Tenant-level application configuration.

    Attributes:
        application_tenant_id: Primary key identifier.
        application_tenant_name: Human-readable tenant name.
    """

    application_tenant_id: str
    application_tenant_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> ApplicationTenant:
        return cls(
            application_tenant_id=data.get("ApplicationTenantID", ""),
            application_tenant_name=data.get("ApplicationTenantName"),
        )

    def to_odata_dict(self) -> dict:
        d: dict = {"ApplicationTenantID": self.application_tenant_id}
        if self.application_tenant_name is not None:
            d["ApplicationTenantName"] = self.application_tenant_name
        return d


@dataclass
class CreateApplicationTenantInput:
    """Input for creating an :class:`ApplicationTenant`."""

    application_tenant_id: str
    application_tenant_name: str

    def to_odata_dict(self) -> dict:
        return {
            "ApplicationTenantID": self.application_tenant_id,
            "ApplicationTenantName": self.application_tenant_name,
        }
