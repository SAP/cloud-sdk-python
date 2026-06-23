# ADMS User Guide

This module integrates with the SAP Advanced Document Management Service (ADM) OData V4 API.
It provides typed, high-level Python clients for managing document relations, documents,
jobs, and tenant configuration.

## Installation

This package is part of the SAP Cloud SDK for Python. Import and use it directly in your application.

## Prerequisites

ADM is a BTP Shared SaaS Application (IAS-based multi-tenant service). It must be provisioned
as a BTP service instance before use. See [INTEGRATION_TESTS.md](../../../docs/INTEGRATION_TESTS.md)
for the env vars used by integration tests.

## Quick Start

```python
from sap_cloud_sdk.adms import (
    create_client,
    AdmsConfig,
    BaseType,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    ScanStatus,
)

# Reads binding from /etc/secrets/appfnd/adms/default/ or env vars
client = create_client()

# Link a document to a business object (creates a draft relation + document)
relation = client.relations.create(
    CreateDocumentRelationInput(
        business_object_node_type_unique_id="PurchaseOrder",
        host_business_object_node_id="PO-4500012345",
        document=CreateDocumentInput(
            document_name="Invoice.pdf",
            document_base_type=BaseType.DOCUMENT,
            document_type_id="INVOICE",
        ),
        is_active_entity=False,  # start as draft
    )
)

# Upload bytes to the presigned URL (outside SDK)
import requests
upload_url = relation.document.document_content_upload_urls[0]
requests.put(upload_url, data=open("Invoice.pdf", "rb"))
```

## Named Instance

```python
# Use a specific binding instance (e.g. "production")
client = create_client(instance="production")
```

## Explicit Configuration

```python
from sap_cloud_sdk.adms import create_client, AdmsConfig

config = AdmsConfig(
    service_url="https://adm.cfapps.eu10.hana.ondemand.com",
    ias_url="https://your-tenant.accounts.ondemand.com",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
client = create_client(config=config)
```

## User-Context (AMS Per-User Policies)

```python
# Pass the user's JWT to enforce AMS per-user access policies
client = create_client(user_jwt=request.headers["Authorization"].split()[1])
```

## Token Cache for Scale-Out

```python
from sap_cloud_sdk.adms import create_client, TokenCache

# By default tokens are cached in-process via InMemoryTokenCache.
# For multi-instance deployments (Kyma replicas > 1, CF instances > 1),
# implement your own TokenCache subclass backed by the shared cache your
# runtime offers, then pass it via create_client(token_cache=...).
class MySharedCache(TokenCache):
    def get(self, key): ...
    def set(self, key, token, ttl_seconds): ...
    def delete(self, key): ...

client = create_client(token_cache=MySharedCache())
```

## Async Client

```python
from sap_cloud_sdk.adms import create_async_client, BaseType, CreateDocumentInput, CreateDocumentRelationInput, RelationQueryOptions

async def main():
    async with create_async_client() as client:
        # List all document relations for a business object
        relations = await client.relations.get_all(
            RelationQueryOptions(
                filter="HostBusinessObjectNodeID eq 'PO-4500012345'",
                expand=["Document"],
            )
        )
        for relation in relations:
            doc = relation.document
            if doc and doc.document_state == ScanStatus.CLEAN:
                url = await client.documents.get_download_url(
                    relation.document_relation_id,
                    doc_content_version_id="1.0",
                )
                print(url)
```

## Query Options

List endpoints (`documents.get_all`, `relations.get_all`,
`config.get_all_*`) accept an options class that encapsulates the OData V4
query parameters.  The classes nest by capability — Configuration endpoints
expose the smallest subset, DocumentRelation adds `$select`/`$expand`, and
Document adds `$orderby` on top of that.

| Class | filter | select | expand | top | skip | orderby |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `ConfigQueryOptions` | ✓ | – | – | ✓ | ✓ | – |
| `RelationQueryOptions` | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `DocumentQueryOptions` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

```python
from sap_cloud_sdk.adms import (
    ConfigQueryOptions,
    DocumentQueryOptions,
    RelationQueryOptions,
)

# Document — full OData surface
docs = client.documents.get_all(
    DocumentQueryOptions(
        filter="DocumentName eq 'Invoice.pdf'",
        top=10,
        orderby="CreatedAt desc",
    )
)

# Relation — no $orderby on this entity set
relations = client.relations.get_all(
    RelationQueryOptions(
        filter="HostBusinessObjectNodeID eq 'PO-4500012345'",
        expand=["Document"],
    )
)

# Configuration endpoints — only $filter/$top/$skip
domains = client.config.get_all_allowed_domains(
    ConfigQueryOptions(filter="AllowedDomainProtocol eq 'https'")
)
```

Passing no options yields an unfiltered, unpaginated request:

```python
all_relations = client.relations.get_all()
```

## Document Operations

```python
from sap_cloud_sdk.adms import UpdateDocumentInput

# Get a specific document through its relation
doc = client.documents.get(document_relation_id)

# Update document metadata
updated = client.documents.update(
    document_relation_id,
    UpdateDocumentInput(document_name="InvoiceV2.pdf"),
)

# Get a presigned download URL (only works when scan state is CLEAN)
url = client.documents.get_download_url(
    document_relation_id,
    doc_content_version_id="1.0",
)
```

## Job Operations

```python
from sap_cloud_sdk.adms import ZipDownloadJobParameters

# Start a ZIP download job
params = ZipDownloadJobParameters(
    business_object_node_type_unique_id="PurchaseOrder",
    host_business_object_node_id="PO-4500012345",
)
job = client.jobs.start_zip_download(params)

# Poll until terminal state
import time
while not job.job_status or not job.job_status.is_terminal():
    time.sleep(2)
    job = client.jobs.get_status(job.job_id)
```

## Tenant Configuration

```python
from sap_cloud_sdk.adms import CreateDocumentTypeInput

# Manage allowed domains, document types, and BO node type mappings
doc_type = client.config.create_document_type(
    CreateDocumentTypeInput(
        document_type_id="INVOICE",
        document_type_name="Invoice",
    )
)
```

## Draft Lifecycle

```python
from sap_cloud_sdk.adms import DraftInput, DraftActivateInput

draft_input = DraftInput(
    business_object_node_type_unique_id="PurchaseOrder",
    host_business_object_node_id="PO-4500012345",
)

# Create and validate draft relations
drafts = client.relations.create_draft(draft_input)
validated = client.relations.validate_draft(draft_input)

# Activate when ready
activate_input = DraftActivateInput(
    business_object_node_type_unique_id="PurchaseOrder",
    host_business_object_node_id="PO-4500012345",
)
active = client.relations.activate_draft(activate_input)
```

## Error Handling

```python
from sap_cloud_sdk.adms import (
    AdmsError,
    AdmsOperationError,
    AuthError,
    ConfigError,
    DocumentNotFoundError,
    HttpError,
    ScanNotCleanError,
)

try:
    url = client.documents.get_download_url(relation_id, doc_content_version_id="1.0")
except ScanNotCleanError as e:
    print(f"Document not yet clean: {e}")
except DocumentNotFoundError as e:
    print(f"Document not found: {e}")
except AuthError as e:
    print(f"Authentication failed: {e}")
except HttpError as e:
    print(f"HTTP error {e.status_code}: {e}")
except AdmsError as e:
    print(f"ADMS error: {e}")
```
