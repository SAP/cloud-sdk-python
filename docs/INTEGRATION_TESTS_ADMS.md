# DMS Integration Tests

End-to-end tests that verify the `sap_cloud_sdk.adms` module is correctly wired to a running **SAP Advanced Document Management (ADM / HDM)** server.

## Two modes

| Mode | When to use | What runs |
|---|---|---|
| **Local auto-start** | Day-to-day development | Starts `hdm/srv` via `mvn spring-boot:run` with H2 + security disabled |
| **External / BTP** | CI pipelines, acceptance tests | Points to a deployed ADM instance using real IAS credentials |

---

## Prerequisites

### Local mode
- Java 21 and Maven 3.9+ on `PATH`
- The `hdm` repo checked out at the same level as `cloud-sdk-python` (i.e. `../hdm`), **or** `CLOUD_SDK_HDM_DIR` set to its path
- No external services needed — H2 in-memory DB, mocked storage & virus scanner

### External / BTP mode
- A provisioned ADM instance
- IAS service binding credentials

---

## Running the tests

### Local mode (auto-starts HDM)

```bash
cd /path/to/cloud-sdk-python

# Run all integration tests — HDM will start automatically
.venv/bin/python -m pytest tests/adms/integration/ -m integration -v

# Skip if HDM can't start (e.g. Java not available in this env)
CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE=true \
  .venv/bin/python -m pytest tests/adms/integration/ -m integration -v
```

HDM startup takes ~30–60 seconds on first run. The server is kept alive for the entire pytest session and killed at the end.

### External / BTP mode

```bash
export CLOUD_SDK_ADMS_INTEGRATION_URL=https://your-adm.cfapps.eu20.hana.ondemand.com
export CLOUD_SDK_CFG_ADMS_DEFAULT_SERVICE_URL=$CLOUD_SDK_ADMS_INTEGRATION_URL
export CLOUD_SDK_CFG_ADMS_DEFAULT_IAS_URL=https://your-tenant.accounts.ondemand.com
export CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENT_ID=...
export CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENT_SECRET=...

.venv/bin/python -m pytest tests/adms/integration/ -m integration -v
```

### Run a specific test file

```bash
# Document lifecycle only
.venv/bin/python -m pytest tests/adms/integration/test_e2e_document_flow.py -m integration -v

# Async client only
.venv/bin/python -m pytest tests/adms/integration/test_e2e_async_flow.py -m integration -v

# SPII handler (no server needed — runs SpiiHandler logic directly)
.venv/bin/python -m pytest tests/adms/integration/test_e2e_spii_flow.py -m integration -v
```

### Run unit tests only (no server)

```bash
.venv/bin/python -m pytest tests/adms/unit/ -v
```

---

## Environment variables reference

| Variable | Default | Description |
|---|---|---|
| `CLOUD_SDK_ADMS_INTEGRATION_URL` | _(unset)_ | External ADM URL; if set, skips local HDM auto-start |
| `CLOUD_SDK_HDM_DIR` | `../hdm` | Path to the HDM repo root (local mode) |
| `CLOUD_SDK_HDM_PORT` | `18080` | Port for the locally started HDM server |
| `CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE` | `false` | Skip (not fail) if the server cannot be reached |

---

## Test files

| File | What it tests |
|---|---|
| [conftest.py](conftest.py) | Session fixtures: start HDM, `AdmsClient`, `AsyncAdmsClient`, `bo_type_id` |
| [test_e2e_document_flow.py](test_e2e_document_flow.py) | Sync client: create → query → get → update → draft lifecycle → delete |
| [test_e2e_async_flow.py](test_e2e_async_flow.py) | Async client: same operations + concurrent creates |
| [test_e2e_spii_flow.py](test_e2e_spii_flow.py) | SPII handler: CONFIG_PENDING, READY, unassign, cert gate, validation |

---

## How the local HDM server is started

The `hdm_base_url` fixture in `conftest.py`:

1. Checks if `CLOUD_SDK_ADMS_INTEGRATION_URL` is set → use it directly
2. Checks if port 18080 is already open → re-use the running server
3. Otherwise runs:
   ```
   mvn -pl srv spring-boot:run -q \
     -Dserver.port=18080 \
     -Dspring.security.enabled=false \
     -Dadm.redis.enabled=false
   ```
4. Polls `/actuator/health` every 3 seconds, up to 120 seconds
5. At session teardown, sends `SIGTERM` to the process group

**Why `spring.security.enabled=false`**: HDM's integration tests use `MockMvc` which bypasses Spring Security. For real HTTP calls from Python, security must be disabled or mocked. In the default/H2 profile without IAS/XSUAA bindings, this is safe and consistent with the existing Java IT approach.

---

## What the tests verify

### `test_e2e_document_flow.py`
1. `CreateDocumentWithRelation` returns a valid `DocumentRelation` with embedded `Document`
2. `get_all()` with `$filter` returns the created relation
3. `get()` by primary key returns correct fields
4. Newly created document has `DocumentState = PENDING` (or CLEAN in fast-scan environments)
5. `get_download_url()` raises `ScanNotCleanError` when state is PENDING
6. `PATCH /Document(...)` updates name correctly
7. Draft flow: `create_draft → validate_draft → activate_draft` produces active entities
8. Draft discard: `create_draft → discard_draft` leaves no active entities
9. `delete()` + subsequent `get()` raises `DocumentNotFoundError`

### `test_e2e_async_flow.py`
- All of the above but via `AsyncAdmsClient` (httpx-based)
- Plus: 3 concurrent `create()` calls via `asyncio.gather` — verifies connection pooling and async correctness

### `test_e2e_spii_flow.py`
- `SpiiHandler` is exercised directly (no HTTP server needed)
- Full CONFIG_PENDING → READY → UNASSIGN tenant lifecycle
- Certificate verification gate blocks wrong CN
- Validation rejects malformed notification payloads
