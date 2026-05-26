#!/usr/bin/env python
"""Interactive CLI for testing the ADMS SDK.

Usage:
    # Load creds from .env.adms and run interactively
    set -a && source .env.adms && set +a
    .venv/bin/python scripts/adms_cli.py

    # Or pass a specific command directly
    .venv/bin/python scripts/adms_cli.py relations list
    .venv/bin/python scripts/adms_cli.py relations get <relation-id>
    .venv/bin/python scripts/adms_cli.py documents get <relation-id>
    .venv/bin/python scripts/adms_cli.py config domains
    .venv/bin/python scripts/adms_cli.py config doctypes

Commands:
    relations list                          — list all DocumentRelations
    relations get <id>                      — get single relation by ID
    relations create                        — create a URL-type relation (prompts for inputs)
    relations delete <id>                   — delete a relation
    documents get <relation-id>             — get Document linked to a relation
    documents download <relation-id>        — get presigned download URL
    config domains                          — list AllowedDomains
    config doctypes                         — list DocumentTypes
    config botypes                          — list BusinessObjectNodeTypes
    jobs zip <bo-type-id> <bo-node-id>      — start ZIP download job
    jobs status <job-id>                    — get job status
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
    ScanNotCleanError,
)
from sap_cloud_sdk.adms._models import (
    BaseType,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    ZipDownloadJobParameters,
)
# ── pretty-printing helpers ──────────────────────────────────────────────────


def _to_jsonable(obj):
    """Recursively convert dataclasses / enums to JSON-serialisable dicts."""
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
    print(f"\n{'─' * 60}")
    print(f"  {label}  ({len(items)} items)")
    print(f"{'─' * 60}")
    for item in items:
        _print_json(item)
        print()


def _prompt(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"  {prompt}{suffix}: ").strip()
    if not value and default:
        return default
    return value


def _ok(msg: str) -> None:
    print(f"\n  ✓  {msg}\n")


def _err(msg: str) -> None:
    print(f"\n  ✗  {msg}\n", file=sys.stderr)


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


# ── command handlers ──────────────────────────────────────────────────────────


def cmd_relations_list(client: AdmsClient) -> None:
    print("\nFetching all DocumentRelations …")
    items = client.relations.get_all(expand=["Document"])
    _print_list(items, "DocumentRelations")


def cmd_relations_get(client: AdmsClient, relation_id: str) -> None:
    print(f"\nFetching DocumentRelation {relation_id} …")
    try:
        rel = client.relations.get(relation_id, expand=["Document"])
        _print_json(rel)
    except DocumentNotFoundError:
        _err(f"Relation {relation_id!r} not found.")


def cmd_relations_create(client: AdmsClient) -> None:
    print("\n── Create DocumentRelation (URL type) ──────────────────")
    print("  (Tip: use 'config botypes' to find a valid bo_type_id)")
    bo_type_id = _prompt("BusinessObjectNodeTypeUniqueID (UUID)")
    bo_node_id = _prompt("HostBusinessObjectNodeID", default="CLI-TEST-001")
    doc_name = _prompt("Document name", default="test-document.pdf")
    doc_url = _prompt("External URL", default="https://example.com/test.pdf")
    doc_type = _prompt("DocumentTypeID (e.g. SAT)", default="SAT")

    if not bo_type_id:
        _err("BusinessObjectNodeTypeUniqueID is required.")
        return

    print("\nCreating …")
    try:
        relation = client.relations.create(
            CreateDocumentRelationInput(
                business_object_node_type_unique_id=bo_type_id,
                host_business_object_node_id=bo_node_id,
                document=CreateDocumentInput(
                    document_name=doc_name,
                    document_base_type=BaseType.URL,
                    document_type_id=doc_type,
                    document_external_content_url=doc_url,
                ),
                is_active_entity=True,
            )
        )
        _ok(f"Created relation: {relation.document_relation_id}")
        _print_json(relation)
    except AdmsError as exc:
        _err(f"Create failed: {exc}")


def cmd_relations_delete(client: AdmsClient, relation_id: str) -> None:
    confirm = input(f"\n  Delete relation {relation_id!r}? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Aborted.")
        return
    try:
        client.relations.delete(relation_id)
        _ok(f"Deleted {relation_id}")
    except DocumentNotFoundError:
        _err(f"Relation {relation_id!r} not found.")
    except AdmsError as exc:
        _err(f"Delete failed: {exc}")


def cmd_documents_get(client: AdmsClient, relation_id: str) -> None:
    print(f"\nFetching Document via relation {relation_id} …")
    try:
        doc = client.documents.get(relation_id)
        _print_json(doc)
    except DocumentNotFoundError:
        _err(f"No document found for relation {relation_id!r}.")
    except AdmsError as exc:
        _err(f"Failed: {exc}")


def cmd_documents_download(client: AdmsClient, relation_id: str) -> None:
    version = _prompt("DocContentVersionID", default="1.0")
    print("\nFetching presigned download URL …")
    try:
        url = client.documents.get_download_url(
            document_relation_id=relation_id,
            doc_content_version_id=version,
        )
        _ok("Presigned URL (valid for a short time — do not cache):")
        print(f"  {url}\n")
    except ScanNotCleanError as exc:
        _err(f"Download blocked — scan not CLEAN: {exc}")
    except DocumentNotFoundError:
        _err(f"Relation {relation_id!r} not found.")
    except AdmsError as exc:
        _err(f"Failed: {exc}")


def cmd_config_domains(client: AdmsClient) -> None:
    print("\nFetching AllowedDomains …")
    items = client.config.get_all_allowed_domains()
    _print_list(items, "AllowedDomains")


def cmd_config_doctypes(client: AdmsClient) -> None:
    print("\nFetching DocumentTypes …")
    items = client.config.get_all_document_types()
    _print_list(items, "DocumentTypes")


def cmd_config_botypes(client: AdmsClient) -> None:
    print("\nFetching BusinessObjectNodeTypes …")
    items = client.config.get_all_business_object_types()
    _print_list(items, "BusinessObjectNodeTypes")


def cmd_jobs_zip(client: AdmsClient, bo_type_id: str, bo_node_id: str) -> None:
    print(f"\nStarting ZIP_DOWNLOAD job for {bo_node_id} …")
    try:
        output = client.jobs.start_zip_download(
            ZipDownloadJobParameters(
                business_object_node_type_unique_id=bo_type_id,
                host_business_object_node_id=bo_node_id,
            )
        )
        _ok(f"Job started: {output.job_id}  status={output.job_status}")
        _print_json(output)
    except AdmsError as exc:
        _err(f"Failed: {exc}")


def cmd_jobs_status(client: AdmsClient, job_id: str) -> None:
    print(f"\nFetching status for job {job_id} …")
    try:
        output = client.jobs.get_status(job_id)
        _print_json(output)
        if output.job_status and output.job_status.is_terminal():
            _ok(f"Job is in terminal state: {output.job_status.value}")
        else:
            print(f"  ⟳  Job still running: {output.job_status}")
    except AdmsError as exc:
        _err(f"Failed: {exc}")


# ── interactive menu ──────────────────────────────────────────────────────────

_MENU = textwrap.dedent("""
    ┌─────────────────────────────────────────────────────────┐
    │              ADMS Interactive CLI                      │
    ├─────────────────────────────────────────────────────────┤
    │  RELATIONS                                              │
    │    rl  — list all relations                             │
    │    rg  — get relation by ID                             │
    │    rc  — create a new URL-type relation                 │
    │    rd  — delete a relation                              │
    │  DOCUMENTS                                              │
    │    dg  — get document via relation ID                   │
    │    dd  — get presigned download URL                     │
    │  CONFIGURATION                                          │
    │    cd  — list AllowedDomains                            │
    │    ct  — list DocumentTypes                             │
    │    cb  — list BusinessObjectNodeTypes                   │
    │  JOBS                                                   │
    │    jz  — start ZIP download job                         │
    │    js  — get job status                                 │
    │  OTHER                                                  │
    │    q   — quit                                           │
    └─────────────────────────────────────────────────────────┘
""")


def _interactive(client: AdmsClient) -> None:
    print(_MENU)
    while True:
        try:
            choice = input("adms> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not choice:
            continue
        elif choice == "q":
            print("Bye.")
            break
        elif choice == "rl":
            cmd_relations_list(client)
        elif choice == "rg":
            rid = _prompt("Relation ID")
            if rid:
                cmd_relations_get(client, rid)
        elif choice == "rc":
            cmd_relations_create(client)
        elif choice == "rd":
            rid = _prompt("Relation ID to delete")
            if rid:
                cmd_relations_delete(client, rid)
        elif choice == "dg":
            rid = _prompt("Relation ID")
            if rid:
                cmd_documents_get(client, rid)
        elif choice == "dd":
            rid = _prompt("Relation ID")
            if rid:
                cmd_documents_download(client, rid)
        elif choice == "cd":
            cmd_config_domains(client)
        elif choice == "ct":
            cmd_config_doctypes(client)
        elif choice == "cb":
            cmd_config_botypes(client)
        elif choice == "jz":
            bo_type = _prompt("BusinessObjectNodeTypeUniqueID (UUID)")
            bo_node = _prompt("HostBusinessObjectNodeID")
            if bo_type and bo_node:
                cmd_jobs_zip(client, bo_type, bo_node)
        elif choice == "js":
            job_id = _prompt("Job ID")
            if job_id:
                cmd_jobs_status(client, job_id)
        else:
            print(f"  Unknown command: {choice!r}  (type 'q' to quit)")


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
        elif sub == "create":
            cmd_relations_create(client)
        elif sub == "delete" and len(args) > 2:
            cmd_relations_delete(client, args[2])
        else:
            _err("Usage: relations list | get <id> | create | delete <id>")

    elif cmd == "documents":
        sub = args[1] if len(args) > 1 else ""
        if sub == "get" and len(args) > 2:
            cmd_documents_get(client, args[2])
        elif sub == "download" and len(args) > 2:
            cmd_documents_download(client, args[2])
        else:
            _err("Usage: documents get <relation-id> | download <relation-id>")

    elif cmd == "config":
        sub = args[1] if len(args) > 1 else ""
        if sub == "domains":
            cmd_config_domains(client)
        elif sub == "doctypes":
            cmd_config_doctypes(client)
        elif sub == "botypes":
            cmd_config_botypes(client)
        else:
            _err("Usage: config domains | doctypes | botypes")

    elif cmd == "jobs":
        sub = args[1] if len(args) > 1 else ""
        if sub == "zip" and len(args) > 3:
            cmd_jobs_zip(client, args[2], args[3])
        elif sub == "status" and len(args) > 2:
            cmd_jobs_status(client, args[2])
        else:
            _err("Usage: jobs zip <bo-type-id> <bo-node-id> | jobs status <job-id>")

    else:
        _err(f"Unknown command: {cmd!r}")
        print("Run without arguments for the interactive menu.")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _cli(_build_client(), sys.argv[1:])
