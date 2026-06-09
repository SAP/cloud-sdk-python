"""Sync + async API for the ADMS Configuration service (allowed domains,
document types, business object node types, type mappings)."""

from __future__ import annotations

from sap_cloud_sdk.adms._http import (
    AdmsHttp,
    AsyncAdmsHttp,
    build_allowed_domain_key_path,
    build_business_object_node_type_key_path,
    build_doctype_botype_map_key_path,
    build_document_type_key_path,
)
from sap_cloud_sdk.adms._models import (
    AllowedDomain,
    BusinessObjectNodeType,
    CreateAllowedDomainInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentTypeInput,
    DocumentType,
    DocumentTypeBusinessObjectTypeMap,
)
from sap_cloud_sdk.adms._query_options import ConfigQueryOptions
from sap_cloud_sdk.adms.config import _CONFIG_SERVICE_PATH
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class _ConfigurationApi:
    """Configuration-service operations.

    Access via :attr:`AdmsClient.config`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_ALLOWED_DOMAINS)
    def get_all_allowed_domains(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[AllowedDomain]:
        """Return all allowed-domain entries visible to the current tenant."""
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "AllowedDomain", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [AllowedDomain.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_ALLOWED_DOMAIN)
    def create_allowed_domain(self, payload: CreateAllowedDomainInput) -> AllowedDomain:
        """Register a new hostname/protocol combination in the allow-list."""
        resp = self._http.post(
            "AllowedDomain",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return AllowedDomain.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_ALLOWED_DOMAIN)
    def delete_allowed_domain(self, allowed_domain_id: str) -> None:
        """Remove an entry from the domain allow-list."""
        self._http.delete(
            build_allowed_domain_key_path(allowed_domain_id),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCUMENT_TYPES)
    def get_all_document_types(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[DocumentType]:
        """Return all document type classifications."""
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "DocumentType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [DocumentType.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCUMENT_TYPE)
    def create_document_type(self, payload: CreateDocumentTypeInput) -> DocumentType:
        """Create a new document type classification."""
        resp = self._http.post(
            "DocumentType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCUMENT_TYPE)
    def delete_document_type(self, document_type_id: str) -> None:
        """Delete a document type classification."""
        self._http.delete(
            build_document_type_key_path(document_type_id),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_BUSINESS_OBJECT_TYPES)
    def get_all_business_object_types(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[BusinessObjectNodeType]:
        """Return all registered business object node types."""
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "BusinessObjectNodeType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [
            BusinessObjectNodeType.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_BUSINESS_OBJECT_TYPE)
    def create_business_object_type(
        self, payload: CreateBusinessObjectNodeTypeInput
    ) -> BusinessObjectNodeType:
        """Register a new business object node type."""
        resp = self._http.post(
            "BusinessObjectNodeType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return BusinessObjectNodeType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_BUSINESS_OBJECT_TYPE)
    def delete_business_object_type(
        self, business_object_node_type_unique_id: str
    ) -> None:
        """Delete a business object node type registration."""
        self._http.delete(
            build_business_object_node_type_key_path(
                business_object_node_type_unique_id
            ),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCTYPE_BOTYPE_MAPS)
    def get_type_mappings(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[DocumentTypeBusinessObjectTypeMap]:
        """Return all DocumentType ↔ BusinessObjectNodeType mappings."""
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "DocumentTypeBusinessObjectTypeMap",
            params=params,
            service_base=_CONFIG_SERVICE_PATH,
        )
        return [
            DocumentTypeBusinessObjectTypeMap.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCTYPE_BOTYPE_MAP)
    def create_type_mapping(
        self, payload: CreateDocumentTypeBoTypeMapInput
    ) -> DocumentTypeBusinessObjectTypeMap:
        """Create a DocumentType ↔ BusinessObjectNodeType mapping."""
        resp = self._http.post(
            "DocumentTypeBusinessObjectTypeMap",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentTypeBusinessObjectTypeMap.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCTYPE_BOTYPE_MAP)
    def delete_type_mapping(self, document_type_bo_type_map_id: str) -> None:
        """Delete a DocumentType ↔ BusinessObjectNodeType mapping."""
        self._http.delete(
            build_doctype_botype_map_key_path(document_type_bo_type_map_id),
            service_base=_CONFIG_SERVICE_PATH,
        )


class _AsyncConfigurationApi:
    """Async version of :class:`_ConfigurationApi`.

    Access via :attr:`AsyncAdmsClient.config`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_ALLOWED_DOMAINS)
    async def get_all_allowed_domains(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[AllowedDomain]:
        """Async variant of :meth:`_ConfigurationApi.get_all_allowed_domains` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "AllowedDomain", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [AllowedDomain.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_ALLOWED_DOMAIN)
    async def create_allowed_domain(
        self, payload: CreateAllowedDomainInput
    ) -> AllowedDomain:
        """Async variant of :meth:`_ConfigurationApi.create_allowed_domain` — same semantics."""
        resp = await self._http.post(
            "AllowedDomain",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return AllowedDomain.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_ALLOWED_DOMAIN)
    async def delete_allowed_domain(self, allowed_domain_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_allowed_domain` — same semantics."""
        await self._http.delete(
            build_allowed_domain_key_path(allowed_domain_id),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCUMENT_TYPES)
    async def get_all_document_types(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[DocumentType]:
        """Async variant of :meth:`_ConfigurationApi.get_all_document_types` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "DocumentType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [DocumentType.from_dict(item) for item in resp.json().get("value", [])]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCUMENT_TYPE)
    async def create_document_type(
        self, payload: CreateDocumentTypeInput
    ) -> DocumentType:
        """Async variant of :meth:`_ConfigurationApi.create_document_type` — same semantics."""
        resp = await self._http.post(
            "DocumentType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCUMENT_TYPE)
    async def delete_document_type(self, document_type_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_document_type` — same semantics."""
        await self._http.delete(
            build_document_type_key_path(document_type_id),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_BUSINESS_OBJECT_TYPES)
    async def get_all_business_object_types(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[BusinessObjectNodeType]:
        """Async variant of :meth:`_ConfigurationApi.get_all_business_object_types` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "BusinessObjectNodeType", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [
            BusinessObjectNodeType.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_BUSINESS_OBJECT_TYPE)
    async def create_business_object_type(
        self, payload: CreateBusinessObjectNodeTypeInput
    ) -> BusinessObjectNodeType:
        """Async variant of :meth:`_ConfigurationApi.create_business_object_type` — same semantics."""
        resp = await self._http.post(
            "BusinessObjectNodeType",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return BusinessObjectNodeType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_BUSINESS_OBJECT_TYPE)
    async def delete_business_object_type(
        self, business_object_node_type_unique_id: str
    ) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_business_object_type` — same semantics."""
        await self._http.delete(
            build_business_object_node_type_key_path(
                business_object_node_type_unique_id
            ),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_DOCTYPE_BOTYPE_MAPS)
    async def get_type_mappings(
        self,
        options: ConfigQueryOptions | None = None,
    ) -> list[DocumentTypeBusinessObjectTypeMap]:
        """Async variant of :meth:`_ConfigurationApi.get_type_mappings` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "DocumentTypeBusinessObjectTypeMap",
            params=params,
            service_base=_CONFIG_SERVICE_PATH,
        )
        return [
            DocumentTypeBusinessObjectTypeMap.from_dict(item)
            for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_DOCTYPE_BOTYPE_MAP)
    async def create_type_mapping(
        self, payload: CreateDocumentTypeBoTypeMapInput
    ) -> DocumentTypeBusinessObjectTypeMap:
        """Async variant of :meth:`_ConfigurationApi.create_type_mapping` — same semantics."""
        resp = await self._http.post(
            "DocumentTypeBusinessObjectTypeMap",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentTypeBusinessObjectTypeMap.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCTYPE_BOTYPE_MAP)
    async def delete_type_mapping(self, document_type_bo_type_map_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_type_mapping` — same semantics."""
        await self._http.delete(
            build_doctype_botype_map_key_path(document_type_bo_type_map_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
