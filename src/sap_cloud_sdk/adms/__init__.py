"""SAP Cloud SDK for Python — ADMS (Advanced Document Management Service) module.

Provides a typed, high-level Python client for the SAP ADM OData V4 service.

ADM is a **BTP Shared SaaS Application** (IAS-based multi-tenant service).
It must be provisioned as a BTP service instance before use.

Quick start::

    from sap_cloud_sdk.adms import (
        create_client,
        BaseType,
        CreateDocumentInput,
        CreateDocumentRelationInput,
    )

    # Reads binding from /etc/secrets/appfnd/adms/default/ or env vars
    client = create_client("default")

    # Link a document to a business object
    relation = client.relations.create(
        CreateDocumentRelationInput(
            business_object_node_type_unique_id="PurchaseOrder",
            host_business_object_node_id="PO-4500012345",
            document=CreateDocumentInput(
                document_name="Invoice.pdf",
                document_base_type=BaseType.DOCUMENT,
                document_type_id="INVOICE",
            ),
            is_active_entity=False,
        )
    )
    # Upload bytes to presigned URL (outside SDK)
    import requests
    requests.put(relation.document.document_content_upload_urls[0], data=open("f.pdf","rb"))
"""

from __future__ import annotations

from sap_cloud_sdk.adms.client import (
    AdmsClient,
    AsyncAdmsClient,
    create_client,
    create_async_client,
)
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import (
    AuthError,
    ClientCreationError,
    ConfigError,
    AdmsError,
    AdmsOperationError,
    DocumentNotFoundError,
    HttpError,
    ScanNotCleanError,
)
from sap_cloud_sdk.adms._models import (
    AllowedDomain,
    BaseType,
    BusinessObjectNodeType,
    CreateAllowedDomainInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    CreateDocumentTypeInput,
    DeleteUserDataJobParameters,
    Document,
    DocumentContentVersion,
    DocumentRelation,
    DocumentType,
    DocumentTypeBusinessObjectTypeMap,
    DocumentTypeText,
    DraftActivateInput,
    DraftAdministrativeData,
    DraftInput,
    JobInput,
    JobOutput,
    JobStatus,
    JobType,
    ScanStatus,
    UpdateAllowedDomainInput,
    UpdateBusinessObjectNodeTypeInput,
    UpdateDocumentInput,
    UpdateDocumentTypeInput,
    ZipDownloadJobParameters,
)
from sap_cloud_sdk.adms._query_options import (
    ConfigQueryOptions,
    DocumentQueryOptions,
    RelationQueryOptions,
)
from sap_cloud_sdk.adms._token_cache import InMemoryTokenCache, TokenCache


__all__ = [
    # factories
    "create_client",
    "create_async_client",
    # clients
    "AdmsClient",
    "AsyncAdmsClient",
    # config
    "AdmsConfig",
    # exceptions
    "AdmsError",
    "AdmsOperationError",
    "AuthError",
    "ClientCreationError",
    "ConfigError",
    "DocumentNotFoundError",
    "HttpError",
    "ScanNotCleanError",
    # models — core
    "BaseType",
    "CreateDocumentInput",
    "CreateDocumentRelationInput",
    "DeleteUserDataJobParameters",
    "Document",
    "DocumentContentVersion",
    "DocumentRelation",
    "DraftActivateInput",
    "DraftAdministrativeData",
    "DraftInput",
    "JobInput",
    "JobOutput",
    "JobStatus",
    "JobType",
    "ScanStatus",
    "UpdateDocumentInput",
    "ZipDownloadJobParameters",
    # models — config
    "AllowedDomain",
    "BusinessObjectNodeType",
    "CreateAllowedDomainInput",
    "CreateBusinessObjectNodeTypeInput",
    "UpdateAllowedDomainInput",
    "UpdateBusinessObjectNodeTypeInput",
    "UpdateDocumentTypeInput",
    "CreateDocumentTypeBoTypeMapInput",
    "CreateDocumentTypeInput",
    "DocumentType",
    "DocumentTypeBusinessObjectTypeMap",
    "DocumentTypeText",
    # query options
    "ConfigQueryOptions",
    "DocumentQueryOptions",
    "RelationQueryOptions",
    # token cache
    "TokenCache",
    "InMemoryTokenCache",
]
