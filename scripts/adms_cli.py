#!/usr/bin/env python
"""Interactive CLI for testing the ADMS SDK.

Exposes every public API on :class:`AdmsClient`:

  * ``client.documents`` — Document entity (list/get/update/download URL,
    restore + soft-delete content versions).
  * ``client.relations``  — DocumentRelation entity (list/get/delete,
    presigned upload URLs, multipart completion, lock/unlock,
    full draft lifecycle: create / validate / activate / discard).
  * ``client.config``     — Tenant configuration (AllowedDomain, DocumentType,
    BusinessObjectNodeType, DocumentType↔BO type maps — full CRUD).
  * ``client.jobs``       — Async jobs (ZIP_DOWNLOAD, DELETE_USER_DATA, status poll).

Usage:
    # Load creds from .env.adms and run interactively
    set -a && source .env.adms && set +a
    .venv/bin/python scripts/adms_cli.py

    # Or pass a specific command directly (see "Commands" below)
    .venv/bin/python scripts/adms_cli.py relations list
    .venv/bin/python scripts/adms_cli.py documents update <relation-id>
    .venv/bin/python scripts/adms_cli.py config maps

Commands:
    RELATIONS
        relations list                              — list all DocumentRelations
        relations get <id>                          — get single relation
        relations delete <id>                       — delete a relation
        relations create-draft                      — start a draft for a BO node
        relations validate-draft                    — validate a draft before activation
        relations activate-draft                    — activate a draft
        relations discard-draft                     — discard a draft without activation
        relations upload-urls <id>                  — generate presigned upload URLs
        relations complete-upload <id>              — finalise a multipart upload
        relations lock <id>                         — lock document & relation
        relations unlock <id>                       — release lock
    DOCUMENTS
        documents list                              — list all Documents
        documents get <relation-id>                 — Document linked to a relation
        documents update <relation-id>              — update document metadata
        documents download <relation-id>            — presigned download URL
        documents restore <relation-id> <version>   — restore a previous content version
        documents delete-version <relation-id> <v>  — soft-delete a content version
    CONFIG
        config domains                              — list AllowedDomains
        config domains-create                       — register an AllowedDomain
        config domains-delete <id>                  — remove an AllowedDomain
        config doctypes                             — list DocumentTypes
        config doctypes-create                      — create a DocumentType
        config doctypes-delete <id>                 — delete a DocumentType
        config botypes                              — list BusinessObjectNodeTypes
        config botypes-create                       — register a BusinessObjectNodeType
        config botypes-delete <id>                  — delete a BusinessObjectNodeType
        config maps                                 — list DocumentType ↔ BO type mappings
        config maps-create                          — create a mapping
        config maps-delete <id>                     — delete a mapping
    JOBS
        jobs status <job-id>                        — poll DocumentService job status
        jobs zip <bo-type-id> <bo-node-id>          — start ZIP_DOWNLOAD job
        jobs delete-user-data <user-id>             — start DELETE_USER_DATA job (admin)
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from typing import Optional

# ── ensure src/ is on the path when run from the repo root ──────────────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from sap_cloud_sdk.adms.client import AdmsClient, create_client
from sap_cloud_sdk.adms.config import load_from_env_or_mount
from sap_cloud_sdk.adms.exceptions import (
    AdmsError,
    DocumentNotFoundError,
    HttpError,
    ScanNotCleanError,
)
from sap_cloud_sdk.adms._models import (
    BaseType,
    CreateAllowedDomainInput,
    CreateApplicationTenantInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentTypeInput,
    CreateFileExtensionPolicyInput,
    DeleteUserDataJobParameters,
    DraftActivateInput,
    DraftInput,
    MimeTypePolicy,
    UpdateAllowedDomainInput,
    UpdateBusinessObjectNodeTypeInput,
    UpdateDocumentInput,
    UpdateDocumentTypeInput,
    ZipDownloadJobParameters,
)

# ── pretty-printing helpers ──────────────────────────────────────────────────

# Maps Python snake_case field names → OData PascalCase wire key names
# so CLI output matches Postman / Bruno responses exactly.
_WIRE_KEYS: dict[str, str] = {
    # DocumentRelation
    "document_relation_id": "DocumentRelationID",
    "business_object_node_type_unique_id": "BusinessObjectNodeTypeUniqueID",
    "host_business_object_node_id": "HostBusinessObjectNodeID",
    "host_business_obj_node_display_id": "HostBusinessObjNodeDisplayID",
    "document_id": "DocumentID",
    "document_is_active_entity": "DocumentIsActiveEntity",
    "is_active_entity": "IsActiveEntity",
    "has_active_entity": "HasActiveEntity",
    "has_draft_entity": "HasDraftEntity",
    "document_relation_is_locked": "DocumentRelationIsLocked",
    "document_relation_is_deleted": "DocumentRelationIsDeleted",
    "document_relation_is_output_relevant": "DocumentRelationIsOutputRelevant",
    "draft_messages": "DraftMessages",
    "draft_administrative_data": "DraftAdministrativeData",
    # DraftAdministrativeData fields
    "draft_uuid": "DraftUUID",
    "creation_date_time": "CreationDateTime",
    "created_by_user": "CreatedByUser",
    "draft_is_created_by_me": "DraftIsCreatedByMe",
    "last_change_date_time": "LastChangeDateTime",
    "last_changed_by_user": "LastChangedByUser",
    "in_process_by_user": "InProcessByUser",
    "draft_is_processed_by_me": "DraftIsProcessedByMe",
    "doc_relation_created_by_user_name": "DocRelationCreatedByUserName",
    "doc_relation_created_at_date_time": "DocRelationCreatedAtDateTime",
    "doc_relation_changed_by_user_name": "DocRelationChangedByUserName",
    "doc_relation_changed_at_date_time": "DocRelationChangedAtDateTime",
    "document": "Document",  # expanded DocumentRelation → Document nav property
    # Document
    "document_name": "DocumentName",
    "document_base_type": "DocumentBaseType",
    "document_type_id": "DocumentTypeID",
    "document_state": "DocumentState",
    "document_mime_type": "DocumentMimeType",
    "document_description": "DocumentDescription",
    "document_size_in_byte": "DocumentSizeInByte",
    "document_content_stream_uri": "DocumentContentStreamURI",
    "document_external_content_url": "DocumentExternalContentURL",
    "document_is_locked": "DocumentIsLocked",
    "document_is_soft_deleted": "DocumentIsSoftDeleted",
    "has_active_document_entity": "HasActiveDocumentEntity",
    "has_draft_document_entity": "HasDraftDocumentEntity",
    "draft_uuid": "DraftUUID",
    "document_content_upload_urls": "DocumentContentUploadURLs",
    "document_is_multi_referenced": "DocumentIsMultiReferenced",
    "document_created_by_user_name": "DocumentCreatedByUserName",
    "document_created_at_date_time": "DocumentCreatedAtDateTime",
    "document_changed_by_user_name": "DocumentChangedByUserName",
    "document_changed_at_date_time": "DocumentChangedAtDateTime",
    # DocumentContentVersion
    "doc_content_version_id": "DocContentVersionID",
    "doc_content_version_state": "DocContentVersionState",
    "doc_content_version_name": "DocContentVersionName",
    "doc_content_version_comment": "DocContentVersionComment",
    "doc_content_version_is_latest": "DocContentVersionIsLatest",
    "doc_content_version_mime_type": "DocContentVersionMimeType",
    "doc_content_version_size_in_byte": "DocContentVersionSizeInByte",
    "doc_content_version_stream_uri": "DocContentVersionStreamURI",
    "doc_content_version_content_hash": "DocContentVersionContentHash",
    "doc_content_version_upload_id": "DocContentVersionUploadID",
    "doc_content_version_is_soft_deleted": "DocContentVersionIsSoftDeleted",
    # AllowedDomain
    "allowed_domain_id": "AllowedDomainID",
    "allowed_domain_host_name": "AllowedDomainHostName",
    "allowed_domain_protocol": "AllowedDomainProtocol",
    "allowed_domain_port": "AllowedDomainPort",
    # DocumentType
    "document_type_name": "DocumentTypeName",
    "document_type_description": "DocumentTypeDescription",
    # BusinessObjectNodeType
    "business_object_node_type": "BusinessObjectNodeType",
    "business_object_node_type_name": "BusinessObjectNodeTypeName",
    "odm_entity_name": "ODMEntityName",
    "application_tenant_id": "ApplicationTenantID",
    # DocumentTypeBusinessObjectTypeMap
    "document_type_bo_type_map_id": "DocumentTypeBOTypeMapID",
    "is_default": "IsDefault",
    # JobOutput
    "job_id": "JobID",
    "job_status": "JobStatus",
    "job_result": "JobResult",
    "job_error_details": "JobErrorDetails",
    "job_progress_percentage": "JobProgressPercentage",
}


def _to_jsonable(obj):
    """Recursively convert dataclasses / enums to JSON-serialisable dicts.

    Uses Python snake_case field names — the SDK model as application code sees it.
    """
    from enum import Enum
    from dataclasses import fields, is_dataclass

    if isinstance(obj, Enum):
        return obj.value
    elif is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_jsonable(getattr(obj, f.name)) for f in fields(obj)}
    elif isinstance(obj, list):
        return [_to_jsonable(i) for i in obj]
    return obj


def _print_json(obj) -> None:
    """Print a dataclass or dict as indented JSON."""
    print(json.dumps(_to_jsonable(obj), indent=2))


def _print_list(items, label: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {label}  ({len(items)} items)")
    print(f"{'─' * 62}")
    for item in items:
        _print_json(item)
        print()


# ── raw response capture ──────────────────────────────────────────────────────
# When raw mode is on, every HTTP response body is printed verbatim (wire JSON)
# before the parsed SDK model is shown — identical to Postman output.

_raw_mode = False
_last_raw_responses: list[str] = []


def _patch_http_for_raw(client: AdmsClient) -> None:
    """Monkey-patch AdmsHttp._request to capture raw response bodies."""
    from sap_cloud_sdk.adms._http import AdmsHttp

    original_request = AdmsHttp._request

    def _capturing_request(self, method, path, **kwargs):
        resp = original_request(self, method, path, **kwargs)
        try:
            body = resp.json()
            _last_raw_responses.append(json.dumps(body, indent=2))
        except Exception:
            _last_raw_responses.append(resp.text)
        return resp

    AdmsHttp._request = _capturing_request  # type: ignore[method-assign]


def _print_raw_if_enabled(label: str = "Raw API response") -> None:
    """Print the most recent captured raw response(s) if raw mode is on."""
    if not _raw_mode or not _last_raw_responses:
        return
    print(f"\n  ── {label} (wire JSON) ──")
    for body in _last_raw_responses:
        print(body)
    print()


def _clear_raw_captures() -> None:
    _last_raw_responses.clear()


def _prompt(prompt: str, default: Optional[str] = None) -> str:
    value = input(f"  {prompt}: ").strip()
    if not value and default:
        return default
    return value


def _prompt_optional(prompt: str) -> Optional[str]:
    """Prompt for an optional value — empty input returns None."""
    value = input(f"  {prompt} (optional): ").strip()
    return value or None


def _prompt_int(prompt: str, default: Optional[int] = None) -> Optional[int]:
    label = f" (optional, default {default})" if default is not None else " (optional)"
    raw = input(f"  {prompt}{label}: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        _err(f"  Invalid integer: {raw!r}. Skipping.")
        return None


def _prompt_bool(prompt: str, default: bool = False) -> bool:
    default_label = "y" if default else "n"
    raw = input(f"  {prompt} (y/n, default {default_label}): ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "1", "true")


def _confirm(question: str) -> bool:
    return input(f"\n  {question} (y/n): ").strip().lower() == "y"


def _ok(msg: str) -> None:
    print(f"\n  ✓  {msg}\n")


def _err(msg: str) -> None:
    print(f"\n  ✗  {msg}\n", file=sys.stderr)


def _err_exc(label: str, exc: Exception) -> None:
    """Print a user-friendly error, including the raw ADM response body when available."""
    _err(f"{label}: {exc}")
    if isinstance(exc, HttpError) and exc.response_text:
        print(f"  ADM response: {exc.response_text}\n", file=sys.stderr)


# ── build client ─────────────────────────────────────────────────────────────


def _build_client() -> AdmsClient:
    try:
        config = load_from_env_or_mount("default")
    except Exception as exc:
        _err(f"Could not load ADMS config: {exc}")
        _err("Make sure you ran:  set -a && source .env.adms && set +a")
        sys.exit(1)
    client = create_client(config=config)
    print(f"  Connected to: {config.service_url}")
    return client


# ── RELATIONS handlers ───────────────────────────────────────────────────────


def cmd_relations_list(client: AdmsClient) -> None:
    print("\nFetching all DocumentRelations …")
    items = client.relations.get_all()
    _print_list(items, "DocumentRelations")


def cmd_relations_get(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    print(f"\nFetching DocumentRelation {relation_id} (IsActiveEntity={str(is_active).lower()}) …")
    try:
        rel = client.relations.get(relation_id, is_active_entity=is_active)
        _print_json(rel)
    except DocumentNotFoundError:
        _err(f"Relation {relation_id!r} not found.")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_delete(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    if not _confirm(f"Delete relation {relation_id!r} (IsActiveEntity={str(is_active).lower()})?"):
        print("  Aborted.")
        return
    try:
        client.relations.delete(relation_id, is_active_entity=is_active)
        _ok(f"Deleted {relation_id}")
    except DocumentNotFoundError:
        _err(f"Relation {relation_id!r} not found.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


def _prompt_draft_input() -> Optional[DraftInput]:
    bo_type_id = _prompt("BusinessObjectNodeTypeUniqueID (UUID)")
    bo_node_id = _prompt("HostBusinessObjectNodeID")
    if not bo_type_id or not bo_node_id:
        _err("Both fields are required.")
        return None
    return DraftInput(
        business_object_node_type_unique_id=bo_type_id,
        host_business_object_node_id=bo_node_id,
    )


def cmd_relations_create_draft(client: AdmsClient) -> None:
    print("\n── Create draft DocumentRelations for a BO node ────────────")
    draft = _prompt_draft_input()
    if not draft:
        return
    try:
        items = client.relations.create_draft(draft)
        _print_list(items, "Draft DocumentRelations")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_validate_draft(client: AdmsClient) -> None:
    print("\n── Validate draft DocumentRelations ────────────────────────")
    draft = _prompt_draft_input()
    if not draft:
        return
    try:
        items = client.relations.validate_draft(draft)
        _print_list(items, "Validated draft DocumentRelations")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_activate_draft(client: AdmsClient) -> None:
    print("\n── Activate draft DocumentRelations ────────────────────────")
    bo_type_id = _prompt("BusinessObjectNodeTypeUniqueID (UUID)")
    bo_node_id = _prompt("HostBusinessObjectNodeID")
    if not bo_type_id or not bo_node_id:
        _err("Both fields are required.")
        return
    late = _prompt_optional("LateHostBusinessObjectNodeID")
    activate = DraftActivateInput(
        business_object_node_type_unique_id=bo_type_id,
        host_business_object_node_id=bo_node_id,
        late_host_business_object_node_id=late,
    )
    try:
        items = client.relations.activate_draft(activate)
        _print_list(items, "Activated DocumentRelations")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_discard_draft(client: AdmsClient) -> None:
    print("\n── Discard draft DocumentRelations ─────────────────────────")
    draft = _prompt_draft_input()
    if not draft:
        return
    if not _confirm("Discard the draft? This cannot be undone."):
        print("  Aborted.")
        return
    try:
        client.relations.discard_draft(draft)
        _ok("Draft discarded.")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_upload_urls(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    is_multipart = _prompt_bool("Multipart upload?", default=False)
    no_of_parts = _prompt_int("Number of parts", default=1) or 1
    print(f"\nGenerating upload URLs for {relation_id} …")
    try:
        doc = client.relations.generate_upload_urls(
            relation_id,
            is_active_entity=is_active,
            is_multipart=is_multipart,
            no_of_parts=no_of_parts,
        )
        _ok(f"Generated {len(doc.document_content_upload_urls)} upload URL(s).")
        _print_json(doc)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_complete_upload(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    print(f"\nCompleting multipart upload for {relation_id} …")
    try:
        client.relations.complete_multipart_upload(relation_id, is_active_entity=is_active)
        _ok("Multipart upload completed.")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_relations_lock(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    try:
        client.relations.lock(relation_id, is_active_entity=is_active)
        _ok(f"Locked {relation_id}.")
    except AdmsError as exc:
        _err_exc("Lock failed", exc)


def cmd_relations_unlock(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    try:
        client.relations.unlock(relation_id, is_active_entity=is_active)
        _ok(f"Unlocked {relation_id}.")
    except AdmsError as exc:
        _err_exc("Unlock failed", exc)


def cmd_relations_full_upload(client: AdmsClient, relation_id: str) -> None:
    """Generate upload URLs, PUT file to GCS, then complete the upload."""
    import os

    file_path = _prompt("Local file path (absolute or relative)")
    if not file_path or not os.path.isfile(file_path):
        _err(f"File not found: {file_path!r}")
        return
    file_name = os.path.basename(file_path)
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    is_multipart = _prompt_bool("Multipart upload?", default=False)
    no_of_parts = _prompt_int("Number of parts", default=1) or 1

    print(f"\nStep 1 — Generating upload URL(s) for relation {relation_id} …")
    try:
        doc = client.relations.generate_upload_urls(
            relation_id,
            is_active_entity=is_active,
            is_multipart=is_multipart,
            no_of_parts=no_of_parts,
        )
    except AdmsError as exc:
        _err_exc("Failed to generate upload URLs", exc)
        return

    urls = doc.document_content_upload_urls
    if not urls:
        _err("No upload URLs returned by ADM.")
        return
    _ok(f"Got {len(urls)} URL(s).")
    upload_url = urls[0]

    # The x-goog-meta-filename value was baked into the GCS signature by ADM
    # at URL-generation time. We must send the document name ADM registered,
    # not the local file name — a mismatch causes SignatureDoesNotMatch.
    adm_filename = doc.document_name or file_name

    print(f"\nStep 2 — Uploading {file_name!r} as '{adm_filename}' to GCS …")
    try:
        import urllib.request as _urllib_request

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        req = _urllib_request.Request(
            upload_url,
            data=file_bytes,
            method="PUT",
            headers={"x-goog-meta-filename": adm_filename},
        )
        try:
            with _urllib_request.urlopen(req, timeout=120) as response:
                status = response.status
        except _urllib_request.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            _err(f"GCS upload failed: HTTP {exc.code} — {body[:400]}")
            return
        if status not in (200, 204):
            _err(f"GCS upload failed: HTTP {status}")
            return
        _ok(f"Uploaded {len(file_bytes):,} bytes.")
    except Exception as exc:
        _err(f"Upload error: {exc}")
        return

    if is_multipart:
        print(f"\nStep 3 — Completing multipart upload for {relation_id} …")
        try:
            client.relations.complete_multipart_upload(relation_id, is_active_entity=is_active)
            _ok("Multipart upload completed.")
        except AdmsError as exc:
            _err_exc("Complete upload failed", exc)
    else:
        _ok("Single-part upload complete — no rcu step needed.")


def cmd_relations_delete_bo_node(client: AdmsClient) -> None:
    print("\n── Delete all DocumentRelations for a BO node ──────────────")
    print("  ⚠  This permanently deletes ALL relations for the given BO node.")
    draft = _prompt_draft_input()
    if not draft:
        return
    if not _confirm("Delete ALL relations for this BO node? This is irreversible."):
        print("  Aborted.")
        return
    try:
        result = client.relations.delete_business_object_node(draft)
        _ok(f"Deleted {result.relations_deleted} relation(s).")
        _print_json(result)
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


def cmd_relations_change_logs(client: AdmsClient) -> None:
    print("\nFetching ChangeLog …")
    items = client.relations.get_change_logs()
    _print_list(items, "ChangeLog")


def cmd_relations_bo_change_logs(client: AdmsClient) -> None:
    print("\nFetching BusinessObjectNodeChangeLog …")
    items = client.relations.get_bo_node_change_logs()
    _print_list(items, "BusinessObjectNodeChangeLog")


# ── DOCUMENTS handlers ───────────────────────────────────────────────────────


def cmd_documents_list(client: AdmsClient) -> None:
    print("\nFetching all Documents (via DocumentRelation?$expand=Document) …")
    items = client.documents.get_all()
    _print_list(items, "Documents")


def cmd_documents_get(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    print(f"\nFetching Document via relation {relation_id} (IsActiveEntity={str(is_active).lower()}) …")
    try:
        doc = client.documents.get(relation_id, is_active_entity=is_active)
        _print_json(doc)
    except DocumentNotFoundError:
        _err(f"No document found for relation {relation_id!r}.")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_documents_update(client: AdmsClient, relation_id: str) -> None:
    print("\n── Update Document metadata ─────────────────────────────────")
    print("  Leave any field blank to leave it unchanged.")
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    update = UpdateDocumentInput(
        document_name=_prompt_optional("New document name"),
        document_description=_prompt_optional("New description"),
        document_type_id=_prompt_optional("New DocumentTypeID"),
        doc_content_version_comment=_prompt_optional("Content version comment"),
        document_external_content_url=_prompt_optional("New external URL"),
    )
    if not any(v is not None for v in update.__dict__.values()):
        _err("Nothing to update — all fields blank.")
        return
    try:
        doc = client.documents.update(relation_id, update, is_active_entity=is_active)
        _ok("Document updated.")
        _print_json(doc)
    except AdmsError as exc:
        _err_exc("Update failed", exc)


def cmd_documents_download(client: AdmsClient, relation_id: str) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    version = _prompt("DocContentVersionID", default="1.0")
    print("\nFetching presigned download URL …")
    try:
        url = client.documents.get_download_url(
            document_relation_id=relation_id,
            is_active_entity=is_active,
            doc_content_version_id=version,
        )
        _ok("Presigned URL (valid for a short time — do not cache):")
        print(f"  {url}\n")
    except ScanNotCleanError as exc:
        _err_exc("Download blocked — scan not CLEAN", exc)
    except DocumentNotFoundError:
        _err(f"Relation {relation_id!r} not found.")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_documents_restore(
    client: AdmsClient, relation_id: str, version_id: str
) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    comment = _prompt_optional("Comment (optional)")
    print(f"\nRestoring version {version_id} on {relation_id} …")
    try:
        doc = client.documents.restore_content_version(
            relation_id, version_id, is_active_entity=is_active, comment=comment
        )
        _ok(f"Restored version {version_id}.")
        _print_json(doc)
    except AdmsError as exc:
        _err_exc("Restore failed", exc)


def cmd_documents_delete_version(
    client: AdmsClient, relation_id: str, version_id: str
) -> None:
    is_active = _prompt_bool("Active entity? (No = draft)", default=True)
    if not _confirm(f"Soft-delete version {version_id} on relation {relation_id} (IsActiveEntity={str(is_active).lower()})?"):
        print("  Aborted.")
        return
    try:
        client.documents.delete_content_version(relation_id, version_id, is_active_entity=is_active)
        _ok(f"Deleted version {version_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


# ── CONFIGURATION handlers ───────────────────────────────────────────────────


def cmd_config_domains(client: AdmsClient) -> None:
    print("\nFetching AllowedDomains …")
    items = client.config.get_all_allowed_domains()
    _print_list(items, "AllowedDomains")


def cmd_config_domains_create(client: AdmsClient) -> None:
    print("\n── Create AllowedDomain ────────────────────────────────────")
    host = _prompt("Hostname (e.g. storage.example.com)")
    proto = _prompt("Protocol", default="https")
    port = _prompt_int("Port (blank = protocol default)")
    if not host or not proto:
        _err("Hostname and protocol are required.")
        return
    try:
        out = client.config.create_allowed_domain(
            CreateAllowedDomainInput(host_name=host, protocol=proto, port=port)
        )
        _ok(f"Created AllowedDomain {out.allowed_domain_id}")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Create failed", exc)


def cmd_config_domains_get(client: AdmsClient, allowed_domain_id: str) -> None:
    print(f"\nFetching AllowedDomain {allowed_domain_id} …")
    try:
        out = client.config.get_allowed_domain(allowed_domain_id)
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_config_domains_update(client: AdmsClient, allowed_domain_id: str) -> None:
    print("\n── Update AllowedDomain ────────────────────────────────────")
    print("  Leave any field blank to leave it unchanged.")
    update = UpdateAllowedDomainInput(
        host_name=_prompt_optional("New hostname"),
        protocol=_prompt_optional("New protocol (https/http)"),
        port=_prompt_int("New port (blank = unchanged)"),
    )
    if not any(v is not None for v in update.__dict__.values()):
        _err("Nothing to update — all fields blank.")
        return
    try:
        out = client.config.update_allowed_domain(allowed_domain_id, update)
        _ok(f"Updated AllowedDomain {out.allowed_domain_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Update failed", exc)


def cmd_config_domains_delete(client: AdmsClient, allowed_domain_id: str) -> None:
    if not _confirm(f"Delete AllowedDomain {allowed_domain_id!r}?"):
        print("  Aborted.")
        return
    try:
        client.config.delete_allowed_domain(allowed_domain_id)
        _ok(f"Deleted {allowed_domain_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


def cmd_config_doctypes(client: AdmsClient) -> None:
    print("\nFetching DocumentTypes …")
    items = client.config.get_all_document_types()
    _print_list(items, "DocumentTypes")


def cmd_config_doctypes_create(client: AdmsClient) -> None:
    print("\n── Create DocumentType ─────────────────────────────────────")
    type_id = _prompt("DocumentTypeID (max 10 chars)")
    name = _prompt("DocumentTypeName")
    desc = _prompt_optional("Description")
    if not type_id or not name:
        _err("DocumentTypeID and DocumentTypeName are required.")
        return
    try:
        out = client.config.create_document_type(
            CreateDocumentTypeInput(
                document_type_id=type_id,
                document_type_name=name,
                document_type_description=desc,
            )
        )
        _ok(f"Created DocumentType {out.document_type_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Create failed", exc)


def cmd_config_doctypes_get(client: AdmsClient, document_type_id: str) -> None:
    print(f"\nFetching DocumentType {document_type_id} …")
    try:
        out = client.config.get_document_type(document_type_id)
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_config_doctypes_update(client: AdmsClient, document_type_id: str) -> None:
    print("\n── Update DocumentType ─────────────────────────────────────")
    print("  Leave any field blank to leave it unchanged.")
    update = UpdateDocumentTypeInput(
        document_type_name=_prompt_optional("New DocumentTypeName"),
        document_type_description=_prompt_optional("New description"),
    )
    if not any(v is not None for v in update.__dict__.values()):
        _err("Nothing to update — all fields blank.")
        return
    try:
        out = client.config.update_document_type(document_type_id, update)
        _ok(f"Updated DocumentType {out.document_type_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Update failed", exc)


def cmd_config_doctypes_delete(client: AdmsClient, document_type_id: str) -> None:
    if not _confirm(f"Delete DocumentType {document_type_id!r}?"):
        print("  Aborted.")
        return
    try:
        client.config.delete_document_type(document_type_id)
        _ok(f"Deleted {document_type_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


def cmd_config_botypes(client: AdmsClient) -> None:
    print("\nFetching BusinessObjectNodeTypes …")
    items = client.config.get_all_business_object_types()
    _print_list(items, "BusinessObjectNodeTypes")


def cmd_config_botypes_create(client: AdmsClient) -> None:
    print("\n── Create BusinessObjectNodeType ───────────────────────────")
    bo_type = _prompt("BusinessObjectNodeType (short code, e.g. PO)")
    bo_name = _prompt("BusinessObjectNodeTypeName")
    tenant_id = _prompt("ApplicationTenantID (UUID of the owning tenant)")
    if not bo_type or not bo_name or not tenant_id:
        _err("BusinessObjectNodeType, name, and ApplicationTenantID are required.")
        return
    try:
        out = client.config.create_business_object_type(
            CreateBusinessObjectNodeTypeInput(
                business_object_node_type=bo_type,
                business_object_node_type_name=bo_name,
                application_tenant_id=tenant_id,
            )
        )
        _ok(
            f"Created BusinessObjectNodeType {out.business_object_node_type_unique_id}."
        )
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Create failed", exc)


def cmd_config_botypes_get(client: AdmsClient, bo_type_unique_id: str) -> None:
    print(f"\nFetching BusinessObjectNodeType {bo_type_unique_id} …")
    try:
        out = client.config.get_business_object_type(bo_type_unique_id)
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_config_botypes_update(client: AdmsClient, bo_type_unique_id: str) -> None:
    print("\n── Update BusinessObjectNodeType ───────────────────────────")
    print("  Leave any field blank to leave it unchanged.")
    update = UpdateBusinessObjectNodeTypeInput(
        business_object_node_type=_prompt_optional("New BusinessObjectNodeType code"),
        business_object_node_type_name=_prompt_optional("New BusinessObjectNodeTypeName"),
    )
    if not any(v is not None for v in update.__dict__.values()):
        _err("Nothing to update — all fields blank.")
        return
    try:
        out = client.config.update_business_object_type(bo_type_unique_id, update)
        _ok(f"Updated BusinessObjectNodeType {out.business_object_node_type_unique_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Update failed", exc)


def cmd_config_botypes_delete(client: AdmsClient, bo_type_unique_id: str) -> None:
    if not _confirm(f"Delete BusinessObjectNodeType {bo_type_unique_id!r}?"):
        print("  Aborted.")
        return
    try:
        client.config.delete_business_object_type(bo_type_unique_id)
        _ok(f"Deleted {bo_type_unique_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


def cmd_config_maps(client: AdmsClient) -> None:
    print("\nFetching DocumentType ↔ BusinessObjectNodeType mappings …")
    items = client.config.get_type_mappings()
    _print_list(items, "DocumentTypeBusinessObjectTypeMaps")


def cmd_config_maps_create(client: AdmsClient) -> None:
    print("\n── Create DocumentType ↔ BO type mapping ───────────────────")
    bo_unique_id = _prompt("BusinessObjectNodeTypeUniqueID (UUID)")
    doc_type_id = _prompt("DocumentTypeID")
    is_default = _prompt_bool("Mark as default for this BO type?", default=False)
    if not bo_unique_id or not doc_type_id:
        _err("Both IDs are required.")
        return
    try:
        out = client.config.create_type_mapping(
            CreateDocumentTypeBoTypeMapInput(
                business_object_node_type_unique_id=bo_unique_id,
                document_type_id=doc_type_id,
                is_default=is_default,
            )
        )
        _ok(f"Created mapping {out.document_type_bo_type_map_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Create failed", exc)


def cmd_config_maps_get(client: AdmsClient, mapping_id: str) -> None:
    print(f"\nFetching mapping {mapping_id} …")
    try:
        out = client.config.get_type_mapping(mapping_id)
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_config_maps_delete(client: AdmsClient, mapping_id: str) -> None:
    if not _confirm(f"Delete mapping {mapping_id!r}?"):
        print("  Aborted.")
        return
    try:
        client.config.delete_type_mapping(mapping_id)
        _ok(f"Deleted {mapping_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


def cmd_config_maps_mark_default(client: AdmsClient, mapping_id: str) -> None:
    try:
        client.config.mark_default(mapping_id)
        _ok(f"Mapping {mapping_id} marked as default.")
    except AdmsError as exc:
        _err_exc("Failed", exc)


# ── CONFIG: FileExtensionPolicy ───────────────────────────────────────────────


def cmd_config_file_ext_list(client: AdmsClient) -> None:
    print("\nFetching FileExtensionPolicies …")
    items = client.config.get_all_file_extension_policies()
    _print_list(items, "FileExtensionPolicies")


def cmd_config_file_ext_create(client: AdmsClient) -> None:
    print("\n── Create FileExtensionPolicy ──────────────────────────────")
    ext = _prompt("File extension (e.g. pdf, exe)")
    print("  Policy option:")
    print("    A — Allow")
    print("    B — Block")
    policy_raw = _prompt("Policy (A/B)", default="A").upper()
    try:
        policy = MimeTypePolicy(policy_raw)
    except ValueError:
        _err(f"Invalid policy {policy_raw!r} — must be A or B.")
        return
    if not ext:
        _err("File extension is required.")
        return
    try:
        out = client.config.create_file_extension_policy(
            CreateFileExtensionPolicyInput(
                file_extension_policy_option=policy,
                file_extension=ext,
            )
        )
        _ok(f"Created FileExtensionPolicy {out.file_extension_policy_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Create failed", exc)


def cmd_config_file_ext_get(client: AdmsClient, policy_id: str) -> None:
    print(f"\nFetching FileExtensionPolicy {policy_id} …")
    try:
        out = client.config.get_file_extension_policy(policy_id)
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_config_file_ext_delete(client: AdmsClient, policy_id: str) -> None:
    if not _confirm(f"Delete FileExtensionPolicy {policy_id!r}?"):
        print("  Aborted.")
        return
    try:
        client.config.delete_file_extension_policy(policy_id)
        _ok(f"Deleted {policy_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


# ── CONFIG: ApplicationTenant ─────────────────────────────────────────────────


def cmd_config_tenant_list(client: AdmsClient) -> None:
    subaccount_id = _prompt_optional("Subaccount ID (x-subaccount-id header)")
    print("\nFetching ApplicationTenants …")
    items = client.config.get_all_application_tenants(subaccount_id=subaccount_id)
    _print_list(items, "ApplicationTenants")


def cmd_config_tenant_create(client: AdmsClient) -> None:
    print("\n── Create ApplicationTenant ────────────────────────────────")
    tenant_id = _prompt("ApplicationTenantID")
    tenant_name = _prompt("ApplicationTenantName")
    subaccount_id = _prompt("Subaccount ID (x-subaccount-id header)")
    if not tenant_id or not tenant_name or not subaccount_id:
        _err("ApplicationTenantID, name, and Subaccount ID are required.")
        return
    try:
        out = client.config.create_application_tenant(
            CreateApplicationTenantInput(
                application_tenant_id=tenant_id,
                application_tenant_name=tenant_name,
            ),
            subaccount_id=subaccount_id,
        )
        _ok(f"Created ApplicationTenant {out.application_tenant_id}.")
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Create failed", exc)


def cmd_config_tenant_get(client: AdmsClient, tenant_id: str) -> None:
    subaccount_id = _prompt_optional("Subaccount ID (x-subaccount-id header)")
    print(f"\nFetching ApplicationTenant {tenant_id} …")
    try:
        out = client.config.get_application_tenant(tenant_id, subaccount_id=subaccount_id)
        _print_json(out)
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_config_tenant_delete(client: AdmsClient, tenant_id: str) -> None:
    subaccount_id = _prompt_optional("Subaccount ID (x-subaccount-id header)")
    if not _confirm(f"Delete ApplicationTenant {tenant_id!r}?"):
        print("  Aborted.")
        return
    try:
        client.config.delete_application_tenant(tenant_id, subaccount_id=subaccount_id)
        _ok(f"Deleted {tenant_id}.")
    except AdmsError as exc:
        _err_exc("Delete failed", exc)


# ── JOBS handlers ────────────────────────────────────────────────────────────


def cmd_jobs_status(
    client: AdmsClient, job_id: str, *, use_admin_service: bool = False
) -> None:
    service = "AdminService" if use_admin_service else "DocumentService"
    print(f"\nFetching {service} status for job {job_id} …")
    try:
        output = client.jobs.get_status(job_id, use_admin_service=use_admin_service)
        _print_json(output)
        if output.job_status and output.job_status.is_terminal():
            _ok(f"Job is in terminal state: {output.job_status.value}")
        else:
            print(f"  ⟳  Job still running: {output.job_status}")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_jobs_zip(client: AdmsClient) -> None:
    print("\n── Start ZIP_DOWNLOAD job ──────────────────────────────────")
    bo_type_id = _prompt("BusinessObjectNodeTypeUniqueID (UUID)")
    bo_node_id = _prompt("HostBusinessObjectNodeID")
    if not bo_type_id or not bo_node_id:
        _err("Both fields are required.")
        return
    rel_ids_raw = _prompt_optional(
        "DocumentRelationIDs (comma-separated UUIDs, blank = all)"
    )
    rel_ids = (
        [r.strip() for r in rel_ids_raw.split(",") if r.strip()]
        if rel_ids_raw
        else []
    )
    print(f"\nStarting ZIP_DOWNLOAD job for {bo_node_id} …")
    try:
        output = client.jobs.start_zip_download(
            ZipDownloadJobParameters(
                business_object_node_type_unique_id=bo_type_id,
                host_business_object_node_id=bo_node_id,
                document_relation_ids=rel_ids,
            )
        )
        _ok(f"Job started: {output.job_id}  status={output.job_status}")
        _print_json(output)
        print(f"  → Poll with: js  (Job ID: {output.job_id})")
    except AdmsError as exc:
        _err_exc("Failed", exc)


def cmd_jobs_delete_user_data(client: AdmsClient) -> None:
    print("\n── Start DELETE_USER_DATA job (AdminService) ───────────────")
    print("  ⚠  This is a GDPR erasure operation and is irreversible.")
    user_id = _prompt("UserID to erase")
    if not user_id:
        _err("UserID is required.")
        return
    replacement = _prompt_optional("ReplacementUserID (default: SYSTEM)")
    if not _confirm(f"Erase all references to user {user_id!r}? This is irreversible."):
        print("  Aborted.")
        return
    try:
        output = client.jobs.start_delete_user_data(
            DeleteUserDataJobParameters(
                user_id=user_id,
                replacement_user_id=replacement,
            )
        )
        _ok(f"Job started: {output.job_id}  status={output.job_status}")
        _print_json(output)
        print(f"  → Poll with: js  (Job ID: {output.job_id})")
    except AdmsError as exc:
        _err_exc("Failed", exc)


# ── interactive menu ──────────────────────────────────────────────────────────

_MENU = textwrap.dedent("""
    ┌──────────────────────────────────────────────────────────────────┐
    │                    ADMS Interactive CLI                          │
    ├──────────────────────────────────────────────────────────────────┤
    │  RELATIONS (AdmsRelationsClientApi)                              │
    │    rl   — list all DocumentRelations                             │
    │    rg   — get relation by ID                                     │
    │    rd   — delete relation by ID                                  │
    │    rcd  — createDraft  (BO type + node ID)                       │
    │    rvd  — validateDraft (BO type + node ID)                      │
    │    rad  — activateDraft (BO type + node ID)                      │
    │    rdd  — discardDraft (BO type + node ID)                       │
    │    ru   — generateUploadUrls (relation ID)                       │
    │    rfu  — fullUpload: generate URL + PUT file + complete         │
    │    rcu  — completeMultipartUpload (relation ID)                  │
    │    rlk  — lock relation                                          │
    │    ruk  — unlock relation                                        │
    │    rbn  — deleteBusinessObjectNode [irreversible!]               │
    │    rcl  — getChangeLog (all changes)                             │
    │    rbl  — getBusinessObjectNodeChangeLog                         │
    ├──────────────────────────────────────────────────────────────────┤
    │  DOCUMENTS (AdmsDocumentsClientApi)                              │
    │    dl   — list all Documents                                     │
    │    dg   — get Document by relation ID                            │
    │    du   — update Document (rename)                               │
    │    dd   — getDownloadUrl (pre-signed URL)                        │
    │    drv  — restoreContentVersion                                  │
    │    ddv  — deleteContentVersion                                   │
    ├──────────────────────────────────────────────────────────────────┤
    │  CONFIGURATION (AdmsConfigClientApi)                             │
    │    cd   — list AllowedDomains                                    │
    │    cdg  — get AllowedDomain by ID                                │
    │    cda  — create AllowedDomain                                   │
    │    cdu  — update AllowedDomain                                   │
    │    cdd  — delete AllowedDomain                                   │
    │    ct   — list DocumentTypes                                     │
    │    ctg  — get DocumentType by ID                                 │
    │    cta  — create DocumentType                                    │
    │    ctu  — update DocumentType                                    │
    │    ctd  — delete DocumentType                                    │
    │    cb   — list BusinessObjectNodeTypes                           │
    │    cbg  — get BusinessObjectNodeType by ID                       │
    │    cba  — create BusinessObjectNodeType                          │
    │    cbu  — update BusinessObjectNodeType                          │
    │    cbd  — delete BusinessObjectNodeType                          │
    │    cm   — list DocType ↔ BOType mappings                        │
    │    cmg  — get mapping by ID                                      │
    │    cma  — create mapping                                         │
    │    cmd  — delete mapping                                         │
    │    cmk  — markDefault (mapping ID)                               │
    │    cfl  — list FileExtensionPolicies                             │
    │    cfg  — get FileExtensionPolicy by ID                          │
    │    cfc  — create FileExtensionPolicy                             │
    │    cfd  — delete FileExtensionPolicy                             │
    │    cal  — list ApplicationTenants                                │
    │    cag  — get ApplicationTenant by ID                            │
    │    cac  — create ApplicationTenant                               │
    │    cad  — delete ApplicationTenant                               │
    ├──────────────────────────────────────────────────────────────────┤
    │  JOBS (AdmsJobsClientApi)                                        │
    │    js   — getStatus (job ID)                                     │
    │    jz   — startZipDownload (relation IDs CSV)                    │
    │    jd   — startDeleteUserData (user ID) [GDPR — irreversible!]  │
    ├──────────────────────────────────────────────────────────────────┤
    │  OTHER                                                           │
    │    raw  — toggle raw wire JSON output (shows exact Postman response)    │
    │    ?    — re-print this menu                                     │
    │    q    — quit                                                   │
    └──────────────────────────────────────────────────────────────────┘
""")


def _interactive(client: AdmsClient) -> None:
    global _raw_mode
    print(_MENU)
    while True:
        try:
            choice = input("adms> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not choice:
            continue
        elif choice in ("q", "quit", "exit"):
            print("Bye.")
            break
        elif choice in ("?", "help", "h"):
            print(_MENU)
        elif choice == "raw":
            _raw_mode = not _raw_mode
            state = "ON  — wire JSON printed after each response" if _raw_mode else "OFF — SDK model printed only"
            print(f"\n  Raw mode: {state}\n")
            continue

        _clear_raw_captures()

        # ── relations ──
        if choice == "rl":
            cmd_relations_list(client)
        elif choice == "rg":
            rid = _prompt("Relation ID")
            if rid:
                cmd_relations_get(client, rid)
        elif choice == "rd":
            rid = _prompt("Relation ID to delete")
            if rid:
                cmd_relations_delete(client, rid)
        elif choice == "rcd":
            cmd_relations_create_draft(client)
        elif choice == "rvd":
            cmd_relations_validate_draft(client)
        elif choice == "rad":
            cmd_relations_activate_draft(client)
        elif choice == "rdd":
            cmd_relations_discard_draft(client)
        elif choice == "ru":
            rid = _prompt("Relation ID")
            if rid:
                cmd_relations_upload_urls(client, rid)
        elif choice == "rcu":
            rid = _prompt("Relation ID")
            if rid:
                cmd_relations_complete_upload(client, rid)
        elif choice == "rlk":
            rid = _prompt("Relation ID to lock")
            if rid:
                cmd_relations_lock(client, rid)
        elif choice == "ruk":
            rid = _prompt("Relation ID to unlock")
            if rid:
                cmd_relations_unlock(client, rid)
        elif choice == "rfu":
            rid = _prompt("Relation ID")
            if rid:
                cmd_relations_full_upload(client, rid)
        elif choice == "rbn":
            cmd_relations_delete_bo_node(client)
        elif choice == "rcl":
            cmd_relations_change_logs(client)
        elif choice == "rbl":
            cmd_relations_bo_change_logs(client)

        # ── documents ──
        elif choice == "dl":
            cmd_documents_list(client)
        elif choice == "dg":
            rid = _prompt("Relation ID")
            if rid:
                cmd_documents_get(client, rid)
        elif choice == "du":
            rid = _prompt("Relation ID")
            if rid:
                cmd_documents_update(client, rid)
        elif choice == "dd":
            rid = _prompt("Relation ID")
            if rid:
                cmd_documents_download(client, rid)
        elif choice == "drv":
            rid = _prompt("Relation ID")
            ver = _prompt("DocContentVersionID to restore", default="1.0")
            if rid and ver:
                cmd_documents_restore(client, rid, ver)
        elif choice == "ddv":
            rid = _prompt("Relation ID")
            ver = _prompt("DocContentVersionID to delete")
            if rid and ver:
                cmd_documents_delete_version(client, rid, ver)

        # ── config: AllowedDomain ──
        elif choice == "cd":
            cmd_config_domains(client)
        elif choice == "cdg":
            did = _prompt("AllowedDomainID")
            if did:
                cmd_config_domains_get(client, did)
        elif choice == "cda":
            cmd_config_domains_create(client)
        elif choice == "cdu":
            did = _prompt("AllowedDomainID to update")
            if did:
                cmd_config_domains_update(client, did)
        elif choice == "cdd":
            did = _prompt("AllowedDomainID to delete")
            if did:
                cmd_config_domains_delete(client, did)

        # ── config: DocumentType ──
        elif choice == "ct":
            cmd_config_doctypes(client)
        elif choice == "ctg":
            tid = _prompt("DocumentTypeID")
            if tid:
                cmd_config_doctypes_get(client, tid)
        elif choice == "cta":
            cmd_config_doctypes_create(client)
        elif choice == "ctu":
            tid = _prompt("DocumentTypeID to update")
            if tid:
                cmd_config_doctypes_update(client, tid)
        elif choice == "ctd":
            tid = _prompt("DocumentTypeID to delete")
            if tid:
                cmd_config_doctypes_delete(client, tid)

        # ── config: BusinessObjectNodeType ──
        elif choice == "cb":
            cmd_config_botypes(client)
        elif choice == "cbg":
            bid = _prompt("BusinessObjectNodeTypeUniqueID")
            if bid:
                cmd_config_botypes_get(client, bid)
        elif choice == "cba":
            cmd_config_botypes_create(client)
        elif choice == "cbu":
            bid = _prompt("BusinessObjectNodeTypeUniqueID to update")
            if bid:
                cmd_config_botypes_update(client, bid)
        elif choice == "cbd":
            bid = _prompt("BusinessObjectNodeTypeUniqueID to delete")
            if bid:
                cmd_config_botypes_delete(client, bid)

        # ── config: type mappings ──
        elif choice == "cm":
            cmd_config_maps(client)
        elif choice == "cmg":
            mid = _prompt("DocumentTypeBOTypeMapID")
            if mid:
                cmd_config_maps_get(client, mid)
        elif choice == "cma":
            cmd_config_maps_create(client)
        elif choice == "cmd":
            mid = _prompt("DocumentTypeBOTypeMapID to delete")
            if mid:
                cmd_config_maps_delete(client, mid)
        elif choice == "cmk":
            mid = _prompt("DocumentTypeBOTypeMapID to mark as default")
            if mid:
                cmd_config_maps_mark_default(client, mid)

        # ── config: FileExtensionPolicy ──
        elif choice == "cfl":
            cmd_config_file_ext_list(client)
        elif choice == "cfg":
            pid = _prompt("FileExtensionPolicyID")
            if pid:
                cmd_config_file_ext_get(client, pid)
        elif choice == "cfc":
            cmd_config_file_ext_create(client)
        elif choice == "cfd":
            pid = _prompt("FileExtensionPolicyID to delete")
            if pid:
                cmd_config_file_ext_delete(client, pid)

        # ── config: ApplicationTenant ──
        elif choice == "cal":
            cmd_config_tenant_list(client)
        elif choice == "cag":
            tid = _prompt("ApplicationTenantID")
            if tid:
                cmd_config_tenant_get(client, tid)
        elif choice == "cac":
            cmd_config_tenant_create(client)
        elif choice == "cad":
            tid = _prompt("ApplicationTenantID to delete")
            if tid:
                cmd_config_tenant_delete(client, tid)

        # ── jobs ──
        elif choice == "js":
            job_id = _prompt("Job ID")
            if job_id:
                cmd_jobs_status(client, job_id, use_admin_service=False)
        elif choice == "jz":
            cmd_jobs_zip(client)
        elif choice == "jd":
            cmd_jobs_delete_user_data(client)

        else:
            print(
                f"  Unknown command: {choice!r}  (type '?' for the menu, 'q' to quit)"
            )
            continue

        _print_raw_if_enabled()


# ── CLI argument dispatch ─────────────────────────────────────────────────────


def _cli(client: AdmsClient, args: list[str]) -> None:
    if not args:
        _interactive(client)
        return

    cmd = args[0]

    if cmd == "relations":
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            cmd_relations_list(client)
        elif sub == "get" and len(args) > 2:
            cmd_relations_get(client, args[2])
        elif sub == "delete" and len(args) > 2:
            cmd_relations_delete(client, args[2])
        elif sub == "create-draft":
            cmd_relations_create_draft(client)
        elif sub == "validate-draft":
            cmd_relations_validate_draft(client)
        elif sub == "activate-draft":
            cmd_relations_activate_draft(client)
        elif sub == "discard-draft":
            cmd_relations_discard_draft(client)
        elif sub == "upload-urls" and len(args) > 2:
            cmd_relations_upload_urls(client, args[2])
        elif sub == "complete-upload" and len(args) > 2:
            cmd_relations_complete_upload(client, args[2])
        elif sub == "lock" and len(args) > 2:
            cmd_relations_lock(client, args[2])
        elif sub == "unlock" and len(args) > 2:
            cmd_relations_unlock(client, args[2])
        else:
            _err(
                "Usage: relations list | get <id> | delete <id> "
                "| create-draft | validate-draft | activate-draft | discard-draft "
                "| upload-urls <id> | complete-upload <id> | lock <id> | unlock <id>"
            )

    elif cmd == "documents":
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            cmd_documents_list(client)
        elif sub == "get" and len(args) > 2:
            cmd_documents_get(client, args[2])
        elif sub == "update" and len(args) > 2:
            cmd_documents_update(client, args[2])
        elif sub == "download" and len(args) > 2:
            cmd_documents_download(client, args[2])
        elif sub == "restore" and len(args) > 3:
            cmd_documents_restore(client, args[2], args[3])
        elif sub == "delete-version" and len(args) > 3:
            cmd_documents_delete_version(client, args[2], args[3])
        else:
            _err(
                "Usage: documents list | get <id> | update <id> | download <id> "
                "| restore <id> <version> | delete-version <id> <version>"
            )

    elif cmd == "config":
        sub = args[1] if len(args) > 1 else ""
        if sub == "domains":
            cmd_config_domains(client)
        elif sub == "domains-create":
            cmd_config_domains_create(client)
        elif sub == "domains-delete" and len(args) > 2:
            cmd_config_domains_delete(client, args[2])
        elif sub == "doctypes":
            cmd_config_doctypes(client)
        elif sub == "doctypes-create":
            cmd_config_doctypes_create(client)
        elif sub == "doctypes-delete" and len(args) > 2:
            cmd_config_doctypes_delete(client, args[2])
        elif sub == "botypes":
            cmd_config_botypes(client)
        elif sub == "botypes-create":
            cmd_config_botypes_create(client)
        elif sub == "botypes-delete" and len(args) > 2:
            cmd_config_botypes_delete(client, args[2])
        elif sub == "maps":
            cmd_config_maps(client)
        elif sub == "maps-create":
            cmd_config_maps_create(client)
        elif sub == "maps-delete" and len(args) > 2:
            cmd_config_maps_delete(client, args[2])
        else:
            _err(
                "Usage: config domains[-create|-delete <id>] "
                "| doctypes[-create|-delete <id>] "
                "| botypes[-create|-delete <id>] | maps[-create|-delete <id>]"
            )

    elif cmd == "jobs":
        sub = args[1] if len(args) > 1 else ""
        if sub == "status" and len(args) > 2:
            cmd_jobs_status(client, args[2], use_admin_service=False)
        elif sub == "zip":
            cmd_jobs_zip(client)
        elif sub == "delete-user-data":
            cmd_jobs_delete_user_data(client)
        else:
            _err(
                "Usage: jobs status <job-id> | jobs zip | jobs delete-user-data"
            )

    else:
        _err(f"Unknown command: {cmd!r}")
        print("Run without arguments for the interactive menu.")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _client = _build_client()
    _patch_http_for_raw(_client)
    _cli(_client, sys.argv[1:])
