# SAP Cloud SDK for Python — ADMS Module: Walkthrough

A talk-track guide for explaining this contribution.
Each section maps to a stop in the walkthrough. Read it top-to-bottom or jump to any section by heading.

---

## Stop 1 — What problem are we solving?

**The pitch:**
> "Before this module, a Python application that needed to attach a document to a purchase order had to write raw `requests` calls: manually fetch an OAuth2 token, negotiate a CSRF token, hand-craft OData V4 URLs, PUT bytes to GCS using a signed URL, map PascalCase JSON keys to Python attributes by hand, and branch on HTTP status codes. Every team that needed ADMS wrote this from scratch."

**What ADMS actually is:**
- A BTP shared-SaaS service that stores documents and links them to CAP business objects via a `DocumentRelation` entity
- File bytes go to Google Cloud Storage (never through ADM itself) — ADM only stores metadata and signs presigned URLs
- Every uploaded file is virus-scanned; downloads are gated on `ScanStatus == CLEAN`
- The server uses CAP `@odata.draft.enabled` on `DocumentRelation` — source of most non-obvious behaviour

**What this SDK module gives you:**
- One method call per operation — all auth, CSRF, retries, OData URL building, JSON mapping, and exception translation are internal
- 35 typed Python `@dataclass` models with `from_dict` / `to_odata_dict` — no raw dicts in application code
- **Full sync + async parity** — every method exists in both forms; signatures are identical, only `await` differs
- OBO (on-behalf-of) support via a single `client.with_user_jwt(jwt)` call
- Pluggable token cache — swap in Redis/Memcached for multi-replica deployments
- OpenTelemetry spans automatically via `@record_metrics`, one per SDK call

**Python-specific differences from Java:**
- `snake_case` method and field names (vs Java's `camelCase`)
- Dataclasses instead of Lombok builders — construct with keyword arguments
- `requests.Session` (sync) / `httpx.AsyncClient` (async) instead of `java.net.http.HttpClient`
- Token URL is **derived automatically** from `CLOUD_SDK_CFG_ADMS_DEFAULT_URL` — Java requires it explicitly
- No `CLOUD_SDK_CFG_ADMS_DEFAULT_TOKENURL` env var needed

---

## Stop 2 — Module layout

```
sap_cloud_sdk/adms/
├── __init__.py            ← public re-exports: create_client, create_async_client, all models
├── _client.py             ← AdmsClient + AsyncAdmsClient (the only classes callers need)
│
├── _relation_api.py       ← _DocumentRelationApi (15 methods) + async twin
├── _document_api.py       ← _DocumentApi          (4 methods)  + async twin
├── _configuration_api.py  ← _ConfigurationApi     (27 methods) + async twin
├── _job_api.py            ← _JobApi               (3 methods)  + async twin
│
├── _models.py             ← 35 dataclasses + 5 enums
├── _query_options.py      ← ConfigQueryOptions / RelationQueryOptions / DocumentQueryOptions
├── _exceptions.py         ← AdmsError hierarchy (6 exception classes)
├── _http.py               ← HTTP transport (CSRF, retries, Bearer, OData URL helpers)
├── _auth.py               ← IAS token fetching
├── _config.py             ← env var + BTP service binding discovery
└── _token_cache.py        ← TokenCache ABC + InMemoryTokenCache
```

**Key point to make:** Callers only ever import from `sap_cloud_sdk.adms` (the `__init__.py`). Everything prefixed with `_` is internal.

---

## Stop 3 — Getting a client

**Sync:**
```python
from sap_cloud_sdk.adms import create_client

client = create_client()  # reads env vars or BTP service binding automatically
```

**Async (FastAPI / async frameworks):**
```python
from sap_cloud_sdk.adms import create_async_client

async with create_async_client() as client:
    relations = await client.relations.get_all()
```

**The credential env vars (local dev):**

| Variable | What it is |
|---|---|
| `CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTID` | IAS client ID |
| `CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTSECRET` | IAS client secret |
| `CLOUD_SDK_CFG_ADMS_DEFAULT_URL` | IAS tenant base URL — token URL is derived from this automatically |
| `CLOUD_SDK_CFG_ADMS_DEFAULT_ENDPOINTS_ADM_V1` | ADMS service host |

**In production (BTP service binding):** The SDK auto-discovers credentials from the mounted secret at `/etc/secrets/appfnd/adms/default/`. No env vars needed in CF / Kyma.

```
/etc/secrets/appfnd/adms/default/
    clientid
    clientsecret
    url                  # IAS token endpoint
    endpoints.adm_v1     # ADM OData root
```

---

## Stop 4 — The four sub-clients

```python
client.relations   # DocumentRelation CRUD + draft lifecycle + upload
client.documents   # Document metadata + download URL + version management
client.jobs        # Async ZIP-download + GDPR delete jobs
client.config      # Tenant config: domains, doc types, BO types, mappings, etc.
```

Sub-clients are plain attributes on `AdmsClient`. No state — thin wrappers over the shared HTTP transport. The async client (`AsyncAdmsClient`) exposes the same four attributes with identical signatures, just `async def`.

---

## Stop 5 — Creating a document relation (the main use case)

**Two paths depending on whether active rows already exist:**

### Path A — Fresh create (most common)

```python
from sap_cloud_sdk.adms import create_client
from sap_cloud_sdk.adms._models import CreateDocumentRelationInput, CreateDocumentInput, BaseType

client = create_client()

# Creates relation + document metadata in one round-trip (POST /CreateDocumentWithRelation)
rel = client.relations.create(
    CreateDocumentRelationInput(
        business_object_node_type_unique_id=bo_type_id,   # UUID of the BO type
        host_business_object_node_id="PO-42",              # the business object
        host_business_obj_node_display_id="PO-42",
        is_active_entity=True,
        document=CreateDocumentInput(
            document_name="invoice.jpg",
            document_type_id="INVOICE",
            document_base_type=BaseType.DOCUMENT,          # D = file, F = folder, U = URL
            document_description="March invoice",
        ),
    )
)
print(rel.document_relation_id)
```

**Note on `create()` vs Java:** In Python `client.relations.create()` maps to `POST /CreateDocumentWithRelation` — the same unbound action that Java's `createDocumentWithRelation()` uses. There is no separate method name; the Python SDK uses `create` as the idiomatic name for this operation.

### Path B — Draft lifecycle (editing existing rows)

```python
from sap_cloud_sdk.adms._models import DraftInput, DraftActivateInput

# Only works when active rows already exist for this BO node
drafts = client.relations.create_draft(
    DraftInput(
        business_object_node_type_unique_id=bo_type_id,
        host_business_object_node_id="PO-42",
    )
)

client.relations.validate_draft(DraftInput(...))   # optional
client.relations.activate_draft(DraftActivateInput(...))
# or
client.relations.discard_draft(DraftInput(...))
```

⚠️ **Gotcha to mention:** `create_draft` returns `[]` silently (HTTP 200, empty list) when no active row exists for the BO node. This is server-side behaviour in `DocumentDraftServiceImpl.editDraft:81`. The integration tests self-seed one active row via `create()` before calling `create_draft`.

---

## Stop 6 — Uploading a file (the 3-step flow)

ADM never accepts file bytes directly. The pattern is:

```
Step 1:  POST /CreateDocumentWithRelation          → creates the relation
Step 2:  POST .../GenerateDocumentUploadURLs        → gets a presigned GCS URL
Step 3:  PUT <gcs-url> + file bytes                → upload direct to GCS (no Bearer token)
         (optional) POST .../CompleteMultipartUpload → finalize multipart only
```

```python
# Step 1 — already done above (rel.document_relation_id)

# Step 2 — get the presigned URL
doc = client.relations.generate_upload_urls(
    rel.document_relation_id,
    is_active_entity=True,
    is_multipart=False,
    no_of_parts=1,
)
upload_url = doc.document_content_upload_urls[0]

# Step 3 — PUT bytes to GCS (not to ADM)
# IMPORTANT: use urllib, NOT requests — requests adds headers that break the GCS V4 signature
import urllib.request

adm_filename = doc.document_name  # use the ADM-registered name, not your local filename
with open("invoice.jpg", "rb") as f:
    file_bytes = f.read()

req = urllib.request.Request(
    upload_url,
    data=file_bytes,
    method="PUT",
    headers={
        "Content-Type": "image/jpeg",
        "x-goog-meta-filename": adm_filename,  # required for single-part
    },
)
urllib.request.urlopen(req)

# No completeMultipartUpload needed for single-part
# For multipart: call client.relations.complete_multipart_upload(rel.document_relation_id)
```

**Key points:**
- File bytes never go through ADM — they go direct to Google Cloud Storage
- The presigned URL is short-lived (~5 min)
- Must use `urllib` (not `requests`) — `requests` injects headers that invalidate the GCS V4 signature
- `x-goog-meta-filename` must be the ADM-registered document name, not the local filename
- For multipart: call `complete_multipart_upload()` after all parts are PUT; not needed for single-part

---

## Stop 7 — Downloading a file

```python
# Returns a presigned GCS download URL.
# Raises ScanNotCleanError if the document hasn't passed virus scan yet.
url = client.documents.get_download_url(
    rel.document_relation_id,
    is_active_entity=True,
    doc_content_version_id=None,   # None = latest version
)
```

**Async:**
```python
url = await client.documents.get_download_url(
    rel.document_relation_id,
    is_active_entity=True,
)
```

---

## Stop 8 — Other document operations

```python
from sap_cloud_sdk.adms._models import UpdateDocumentInput

# Rename / update metadata
doc = client.documents.update(
    rel.document_relation_id,
    UpdateDocumentInput(document_name="invoice-final.jpg"),
    is_active_entity=True,
)

# Restore a previous content version
doc = client.documents.restore_content_version(
    rel.document_relation_id,
    doc_content_version_id="1.0",
    is_active_entity=True,
    comment="rolling back",
)

# Soft-delete a content version
client.documents.delete_content_version(
    rel.document_relation_id,
    doc_content_version_id="2.0",
    is_active_entity=True,
)
```

---

## Stop 9 — Locking and deleting

```python
# Lock a relation to prevent concurrent modifications
client.relations.lock(rel.document_relation_id, is_active_entity=True)
client.relations.unlock(rel.document_relation_id, is_active_entity=True)

# Delete a single relation
client.relations.delete(rel.document_relation_id, is_active_entity=True)

# Bulk-delete ALL relations for a BO node (irreversible, requires system-user scope)
result = client.relations.delete_business_object_node(
    DraftInput(
        business_object_node_type_unique_id=bo_type_id,
        host_business_object_node_id="PO-42",
    )
)
print(f"Deleted: {result.relations_deleted}")
```

---

## Stop 10 — Change logs

```python
from sap_cloud_sdk.adms._query_options import ConfigQueryOptions

# Full audit trail across all document management operations
logs = client.relations.get_change_logs(ConfigQueryOptions(top=50))

# Audit joined with BO node context
bo_logs = client.relations.get_bo_node_change_logs(ConfigQueryOptions(top=50))
```

---

## Stop 11 — Async jobs

```python
from sap_cloud_sdk.adms._models import ZipDownloadJobParameters, DeleteUserDataJobParameters

# Start a ZIP download of all documents for a BO node
job = client.jobs.start_zip_download(
    ZipDownloadJobParameters(
        business_object_node_type_unique_id=bo_type_id,
        host_business_object_node_id="PO-42",
        document_relation_ids=[],  # empty = all relations
    )
)

# Poll until done
status = client.jobs.get_status(job.job_id, use_admin_service=False)
print(status.job_status)  # JobStatus enum: PENDING / RUNNING / COMPLETED / FAILED

# GDPR erasure (irreversible, goes via AdminService)
job = client.jobs.start_delete_user_data(
    DeleteUserDataJobParameters(
        user_id="I123456",
        replacement_user_id="SYSTEM",  # optional
    )
)
# Poll with use_admin_service=True
status = client.jobs.get_status(job.job_id, use_admin_service=True)
```

---

## Stop 12 — Configuration API (tenant setup)

27 methods across 6 entity sets:

```python
from sap_cloud_sdk.adms._models import (
    CreateAllowedDomainInput, CreateDocumentTypeInput,
    CreateBusinessObjectNodeTypeInput, CreateDocumentTypeBoTypeMapInput,
    CreateFileExtensionPolicyInput, CreateApplicationTenantInput,
)
from sap_cloud_sdk.adms._query_options import ConfigQueryOptions

opts = ConfigQueryOptions(top=50)

# AllowedDomains — which GCS domains can be used for uploads
client.config.get_all_allowed_domains(opts)
client.config.create_allowed_domain(CreateAllowedDomainInput(host_name="storage.example.com", protocol="https"))
client.config.update_allowed_domain(domain_id, UpdateAllowedDomainInput(host_name="new.example.com"))
client.config.delete_allowed_domain(domain_id)

# DocumentTypes — classification labels (e.g. INVOICE, CONTRACT, max 10 chars)
client.config.get_all_document_types(opts)
client.config.create_document_type(CreateDocumentTypeInput(document_type_id="INVOICE", document_type_name="Invoice"))

# BusinessObjectNodeTypes — registers which BO types can have documents
client.config.get_all_business_object_types(opts)
client.config.create_business_object_type(
    CreateBusinessObjectNodeTypeInput(
        business_object_node_type="PO",
        business_object_node_type_name="Purchase Order",
        application_tenant_id=tenant_uuid,
    )
)

# DocType ↔ BOType mappings
client.config.get_type_mappings(opts)
client.config.create_type_mapping(
    CreateDocumentTypeBoTypeMapInput(document_type_id="INVOICE", business_object_node_type_unique_id=bo_uuid)
)
client.config.mark_default("INVOICE", bo_uuid)   # sets this mapping as the default

# FileExtensionPolicies — which extensions are allowed per doc type
client.config.get_all_file_extension_policies(opts)
client.config.create_file_extension_policy(CreateFileExtensionPolicyInput(document_type_id="INVOICE", file_extension="pdf"))

# ApplicationTenants — all methods accept optional subaccount_id kwarg
client.config.get_all_application_tenants(opts, subaccount_id="<uuid>")
client.config.create_application_tenant(
    CreateApplicationTenantInput(application_tenant_id="<uuid>", application_tenant_name="My Tenant"),
    subaccount_id="<uuid>",
)
```

---

## Stop 13 — Query options (tiered inheritance)

Three classes — you can only pass options the entity actually supports:

```python
from sap_cloud_sdk.adms._query_options import (
    ConfigQueryOptions,      # filter, top, skip         — used by config.*
    RelationQueryOptions,    # + select, expand          — used by relations.*
    DocumentQueryOptions,    # + orderby                 — used by documents.*
)

# Filter relations for a specific BO node, expanding the embedded Document
from sap_cloud_sdk.adms import RelationQueryOptions

relations = client.relations.get_all(
    RelationQueryOptions(
        filter="HostBusinessObjectNodeID eq 'PO-42'",
        expand=["Document"],
        top=20,
    )
)

# The $ prefix is added automatically — write filter=, the SDK sends $filter=
```

---

## Stop 14 — OBO (on-behalf-of, per-user calls)

```python
# FastAPI example — switch to per-user token when Authorization header is present
from typing import Optional
from fastapi import Header

def get_client(authorization: Optional[str] = Header(default=None)):
    base_client = app.state.adms_client  # shared service-to-service client
    if authorization and authorization.lower().startswith("bearer "):
        user_jwt = authorization.split(" ", 1)[1]
        return base_client.with_user_jwt(user_jwt)  # OBO — no new connection pool
    return base_client
```

**How `with_user_jwt` works:**
- Exchanges the inbound user JWT for an IAS OBO token (`urn:ietf:params:oauth:grant-type:jwt-bearer`)
- Shares the parent's connection pool — no port exhaustion
- OBO token is **not cached** — an OBO token is scoped to a specific user; caching would allow one user's token to serve another user's request (privilege boundary violation)

---

## Stop 15 — Pluggable token cache

The default `InMemoryTokenCache` is fine for single-process apps. For Kyma with multiple replicas or CF with multiple instances, swap in a shared cache:

```python
from sap_cloud_sdk.adms import create_client, TokenCache

class RedisTokenCache(TokenCache):
    def get(self, key: str):
        return redis_client.get(key)

    def set(self, key: str, token: str, ttl_seconds: int):
        redis_client.setex(key, ttl_seconds, token)

    def delete(self, key: str):
        redis_client.delete(key)

client = create_client(token_cache=RedisTokenCache(redis_url="redis://..."))
```

**Key contract:** The `set()` implementation must honour `ttl_seconds`. The SDK does not re-validate TTL at retrieval time — that's the cache's responsibility.

---

## Stop 16 — Exception handling

```python
from sap_cloud_sdk.adms import (
    AdmsError,
    DocumentNotFoundError,
    HttpError,
    ScanNotCleanError,
)

try:
    url = client.documents.get_download_url(relation_id)

except DocumentNotFoundError:
    return 404                       # relation/document doesn't exist

except ScanNotCleanError:
    return 423                       # Locked — scan not CLEAN yet

except HttpError as exc:
    log.warning("ADM %d: %s", exc.status_code, exc.response_text)
    return 502

except AdmsError:
    log.exception("Unexpected ADM SDK error")
    return 500
```

**Full exception hierarchy:**
```
AdmsError                         ← root, all SDK errors inherit from this
├── AdmsOperationError            ← malformed input / illegal state
├── AuthError                     ← IAS / OAuth failures
├── ConfigError                   ← missing / malformed AdmsConfig
├── DocumentNotFoundError         ← HTTP 404
├── HttpError                     ← any other non-2xx (has .status_code + .response_text)
└── ScanNotCleanError             ← download refused (scan_status != CLEAN)
```

---

## Stop 17 — What the SDK handles invisibly

Every call goes through this pipeline, automatically:

1. **OAuth2 token** — fetched via `client_credentials`, cached until 60s before expiry, refreshed transparently
2. **CSRF token** — fetched once per service root, retried on 403, evicted on `X-CSRF-Token: Required`
3. **HTTP transport** — `requests.Session` (sync) or `httpx.AsyncClient` (async); connection pooling shared across all calls
4. **OData URL building** — `DocumentRelation(DocumentRelationID='...',IsActiveEntity=true)` built from typed params
5. **Wire ↔ Python conversion** — PascalCase JSON keys mapped to `snake_case` Python attributes via `from_dict`
6. **Exception mapping** — 404 → `DocumentNotFoundError`, bad scan → `ScanNotCleanError`
7. **OpenTelemetry** — one span per call via `@record_metrics(Module.ADMS, Operation.ADMS_*)`

You write zero of this.

---

## Stop 18 — OData envelope conventions (non-obvious gotcha)

The server has three different envelope shapes depending on the endpoint type:

| Endpoint type | Payload format |
|---|---|
| Entity-set POST (e.g. `POST /AllowedDomain`) | `{ ...fields }` bare |
| Unbound action import (e.g. `/CreateBusinessObjNodeDraft`) | `{ "BusinessObjectNode": { ...fields } }` |
| `/CreateDocumentWithRelation` | `{ "DocumentRelation": { ...fields } }` — exception to the above rule |

**The SDK hides all three.** Callers only ever pass the dataclass. Mention this when someone inspects the wire with Bruno/Postman and asks "why is the payload wrapped in `DocumentRelation`?"

**Namespace-qualified bound actions (PR #183 alignment):**
All bound OData action paths must use the fully qualified `com.sap.adm.{Service}.{Action}` prefix:
```
DocumentRelation(...)/com.sap.adm.DocumentService.GenerateDocumentUploadURLs
DocumentRelation(...)/com.sap.adm.DocumentService.UpdateDocument
```
This is a hard requirement aligned with the Java SDK, enforced in PR #183.

---

## Stop 19 — Data models

**35 dataclasses, 5 enums** — all live in `_models.py`, all re-exported from `sap_cloud_sdk.adms`.

**Enums to know:**

| Enum | Values | Used for |
|---|---|---|
| `BaseType` | `DOCUMENT`, `FOLDER`, `LINK` | `document_base_type` when creating |
| `ScanStatus` | `PENDING`, `CLEAN`, `QUARANTINED`, `FAILED`, `FILE_EXT_RESTRICTED` | `document_state` on downloaded doc |
| `JobStatus` | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` | `job_status` from `get_status()` |
| `JobType` | `ZIP_DOWNLOAD`, `DELETE_USER_DATA` | internal job discriminator |

**Dataclass convention:**
```python
# Reading: server JSON → Python
rel = DocumentRelation.from_dict({"DocumentRelationID": "abc-123", "IsActiveEntity": True, ...})
print(rel.document_relation_id)   # snake_case

# Writing: Python → OData JSON
payload = CreateDocumentRelationInput(...).to_odata_dict()
# → {"BusinessObjectNodeTypeUniqueID": "...", "HostBusinessObjectNodeID": "...", ...}
```

---

## Stop 20 — Test coverage

| Suite | Count |
|---|---|
| Unit tests (`tests/adms/unit/`) | 3,259 lines of test code |
| Integration tests — read paths (`test_e2e_document_flow.py`) | full flow |
| Integration tests — async paths (`test_e2e_async_flow.py`) | full async flow |

```bash
# Run unit tests
pytest tests/adms/unit/

# Run integration tests (requires .env.adms)
set -a && source .env.adms && set +a
pytest tests/adms/integration/
```

---

## Stop 21 — Cross-SDK parity with Java

The `document_flow.feature` Cucumber file is **byte-identical** between Python and Java, with one deliberate difference: draft scenario BO-node IDs use `PY-SDK-IT-DRAFT-001` / `-002` (vs `JAVA-SDK-IT-DRAFT-*` in Java) so both SDKs can run against the same shared tenant without colliding on unique constraints.

A passing scenario in Java guarantees the same shape passes in Python.

---

## Stop 22 — Open follow-ups

1. **`scripts/adms_cli.py` is temporary** — used only for reviewer testing on PR #183; will be removed before merge
2. **Shared token cache** — currently in-process only (`InMemoryTokenCache`); needs Redis/Memcached plug-in for multi-replica Kyma deployments
3. **`documents.get()` not top-level** — `Document` is only reachable as a nav property of `DocumentRelation`; use `relations.get(..., expand=["Document"])` to inline it

---

## Quick reference — CLI demo commands

The interactive CLI at `scripts/adms_cli.py` covers every API. Useful for live demos:

```bash
set -a && source .env.adms && set +a
.venv/bin/python scripts/adms_cli.py

# Key shortcuts:
# rl   — list all relations          (client.relations.get_all)
# rfu  — full upload: create → URL → PUT → complete
# rcd  — create_draft
# rad  — activate_draft
# dd   — get_download_url
# js   — get_status (poll job)
# cd   — list AllowedDomains
# ct   — list DocumentTypes
# cfl  — list FileExtensionPolicies
# cgf  — GetGlobalAllowedFileExtensions (raw HTTP)
# cal  — list ApplicationTenants
# raw  — toggle wire JSON output (shows exact Postman/Bruno response)
```
