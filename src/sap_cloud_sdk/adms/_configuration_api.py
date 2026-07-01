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
    quote_odata_string_key,
)
from sap_cloud_sdk.adms._models import (
    AllowedDomain,
    ApplicationTenant,
    BusinessObjectNodeType,
    CreateAllowedDomainInput,
    CreateApplicationTenantInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentTypeInput,
    CreateFileExtensionPolicyInput,
    DocumentType,
    DocumentTypeBusinessObjectTypeMap,
    FileExtensionPolicy,
    UpdateAllowedDomainInput,
    UpdateBusinessObjectNodeTypeInput,
    UpdateDocumentTypeInput,
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALLOWED_DOMAIN)
    def get_allowed_domain(self, allowed_domain_id: str) -> AllowedDomain:
        """Fetch a single AllowedDomain by its UUID."""
        resp = self._http.get(
            build_allowed_domain_key_path(allowed_domain_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return AllowedDomain.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_UPDATE_ALLOWED_DOMAIN)
    def update_allowed_domain(
        self, allowed_domain_id: str, payload: UpdateAllowedDomainInput
    ) -> AllowedDomain:
        """Update an existing AllowedDomain entry (PATCH — only sent fields change)."""
        resp = self._http.patch(
            build_allowed_domain_key_path(allowed_domain_id),
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_DOCUMENT_TYPE)
    def get_document_type(self, document_type_id: str) -> DocumentType:
        """Fetch a single DocumentType by its ID."""
        resp = self._http.get(
            build_document_type_key_path(document_type_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_UPDATE_DOCUMENT_TYPE)
    def update_document_type(
        self, document_type_id: str, payload: UpdateDocumentTypeInput
    ) -> DocumentType:
        """Update an existing DocumentType (PATCH — only sent fields change)."""
        resp = self._http.patch(
            build_document_type_key_path(document_type_id),
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_BUSINESS_OBJECT_TYPE)
    def get_business_object_type(
        self, business_object_node_type_unique_id: str
    ) -> BusinessObjectNodeType:
        """Fetch a single BusinessObjectNodeType by its unique ID."""
        resp = self._http.get(
            build_business_object_node_type_key_path(
                business_object_node_type_unique_id
            ),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return BusinessObjectNodeType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_UPDATE_BUSINESS_OBJECT_TYPE)
    def update_business_object_type(
        self,
        business_object_node_type_unique_id: str,
        payload: UpdateBusinessObjectNodeTypeInput,
    ) -> BusinessObjectNodeType:
        """Update an existing BusinessObjectNodeType (PATCH)."""
        resp = self._http.patch(
            build_business_object_node_type_key_path(
                business_object_node_type_unique_id
            ),
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_DOCTYPE_BOTYPE_MAP)
    def get_type_mapping(
        self, document_type_id: str, business_object_node_type_unique_id: str
    ) -> DocumentTypeBusinessObjectTypeMap:
        """Fetch a single DocumentType ↔ BusinessObjectNodeType mapping by its composite key."""
        resp = self._http.get(
            build_doctype_botype_map_key_path(document_type_id, business_object_node_type_unique_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentTypeBusinessObjectTypeMap.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCTYPE_BOTYPE_MAP)
    def delete_type_mapping(self, document_type_id: str, business_object_node_type_unique_id: str) -> None:
        """Delete a DocumentType ↔ BusinessObjectNodeType mapping."""
        self._http.delete(
            build_doctype_botype_map_key_path(document_type_id, business_object_node_type_unique_id),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_MARK_DEFAULT)
    def mark_default(self, document_type_id: str, business_object_node_type_unique_id: str) -> None:
        """Mark a DocumentType ↔ BusinessObjectNodeType mapping as the default."""
        self._http.post(
            f"{build_doctype_botype_map_key_path(document_type_id, business_object_node_type_unique_id)}/com.sap.adm.ConfigurationService.markDefault",
            json={},
            service_base=_CONFIG_SERVICE_PATH,
        )

    # ── DocumentTypeFileExtensionPolicy ───────────────────────────────────────

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_FILE_EXT_POLICIES)
    def get_all_file_extension_policies(
        self, options: ConfigQueryOptions | None = None
    ) -> list[FileExtensionPolicy]:
        """Return all document-type file extension policies."""
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "DocumentTypeFileExtensionPolicy", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [
            FileExtensionPolicy.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_FILE_EXT_POLICY)
    def create_file_extension_policy(
        self, payload: CreateFileExtensionPolicyInput
    ) -> FileExtensionPolicy:
        """Create a document-type file extension policy."""
        resp = self._http.post(
            "DocumentTypeFileExtensionPolicy",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return FileExtensionPolicy.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_FILE_EXT_POLICY)
    def delete_file_extension_policy(self, document_type_id: str, file_extension: str) -> None:
        """Delete a document-type file extension policy by composite key."""
        self._http.delete(
            f"DocumentTypeFileExtensionPolicy(DocumentTypeID={quote_odata_string_key(document_type_id)},FileExtension={quote_odata_string_key(file_extension)})",
            service_base=_CONFIG_SERVICE_PATH,
        )

    # ── ApplicationTenant ─────────────────────────────────────────────────────

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_APP_TENANTS)
    def get_all_application_tenants(
        self,
        options: ConfigQueryOptions | None = None,
        *,
        subaccount_id: str | None = None,
    ) -> list[ApplicationTenant]:
        """Return all application tenant configurations.

        Args:
            options: Optional OData query parameters.
            subaccount_id: BTP subaccount ID. ADM requires this header
                (``x-subaccount-id``) on ApplicationTenant operations.
        """
        params = options.to_query_params() if options else {}
        resp = self._http.get(
            "ApplicationTenant",
            params=params,
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )
        return [
            ApplicationTenant.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_APP_TENANT)
    def create_application_tenant(
        self,
        payload: CreateApplicationTenantInput,
        *,
        subaccount_id: str | None = None,
    ) -> ApplicationTenant:
        """Create an application tenant configuration.

        Args:
            payload: Tenant fields.
            subaccount_id: BTP subaccount ID. ADM requires this header
                (``x-subaccount-id``) on ApplicationTenant operations.
        """
        resp = self._http.post(
            "ApplicationTenant",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )
        return ApplicationTenant.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_APP_TENANT)
    def get_application_tenant(
        self,
        application_tenant_id: str,
        *,
        subaccount_id: str | None = None,
    ) -> ApplicationTenant:
        """Fetch a single ApplicationTenant by its ID."""
        resp = self._http.get(
            f"ApplicationTenant(ApplicationTenantID='{application_tenant_id}')",
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )
        return ApplicationTenant.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_APP_TENANT)
    def delete_application_tenant(
        self,
        application_tenant_id: str,
        *,
        subaccount_id: str | None = None,
    ) -> None:
        """Delete an application tenant configuration."""
        self._http.delete(
            f"ApplicationTenant(ApplicationTenantID='{application_tenant_id}')",
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )


def _subaccount_header(subaccount_id: str | None) -> dict[str, str] | None:
    """Build the X-SubaccountId header dict, or None if not provided."""
    return {"X-SubaccountId": subaccount_id} if subaccount_id else None


def _quote_guid(value: str) -> str:
    """Wrap a UUID value in the OData Edm.Guid format for key segments."""
    from sap_cloud_sdk.adms._http import quote_odata_guid_key

    return quote_odata_guid_key(value)


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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALLOWED_DOMAIN)
    async def get_allowed_domain(self, allowed_domain_id: str) -> AllowedDomain:
        """Async variant of :meth:`_ConfigurationApi.get_allowed_domain` — same semantics."""
        resp = await self._http.get(
            build_allowed_domain_key_path(allowed_domain_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return AllowedDomain.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_UPDATE_ALLOWED_DOMAIN)
    async def update_allowed_domain(
        self, allowed_domain_id: str, payload: UpdateAllowedDomainInput
    ) -> AllowedDomain:
        """Async variant of :meth:`_ConfigurationApi.update_allowed_domain` — same semantics."""
        resp = await self._http.patch(
            build_allowed_domain_key_path(allowed_domain_id),
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_DOCUMENT_TYPE)
    async def get_document_type(self, document_type_id: str) -> DocumentType:
        """Async variant of :meth:`_ConfigurationApi.get_document_type` — same semantics."""
        resp = await self._http.get(
            build_document_type_key_path(document_type_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_UPDATE_DOCUMENT_TYPE)
    async def update_document_type(
        self, document_type_id: str, payload: UpdateDocumentTypeInput
    ) -> DocumentType:
        """Async variant of :meth:`_ConfigurationApi.update_document_type` — same semantics."""
        resp = await self._http.patch(
            build_document_type_key_path(document_type_id),
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_BUSINESS_OBJECT_TYPE)
    async def get_business_object_type(
        self, business_object_node_type_unique_id: str
    ) -> BusinessObjectNodeType:
        """Async variant of :meth:`_ConfigurationApi.get_business_object_type` — same semantics."""
        resp = await self._http.get(
            build_business_object_node_type_key_path(
                business_object_node_type_unique_id
            ),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return BusinessObjectNodeType.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_UPDATE_BUSINESS_OBJECT_TYPE)
    async def update_business_object_type(
        self,
        business_object_node_type_unique_id: str,
        payload: UpdateBusinessObjectNodeTypeInput,
    ) -> BusinessObjectNodeType:
        """Async variant of :meth:`_ConfigurationApi.update_business_object_type` — same semantics."""
        resp = await self._http.patch(
            build_business_object_node_type_key_path(
                business_object_node_type_unique_id
            ),
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

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_DOCTYPE_BOTYPE_MAP)
    async def get_type_mapping(
        self, document_type_id: str, business_object_node_type_unique_id: str
    ) -> DocumentTypeBusinessObjectTypeMap:
        """Async variant of :meth:`_ConfigurationApi.get_type_mapping` — same semantics."""
        resp = await self._http.get(
            build_doctype_botype_map_key_path(document_type_id, business_object_node_type_unique_id),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return DocumentTypeBusinessObjectTypeMap.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_DOCTYPE_BOTYPE_MAP)
    async def delete_type_mapping(self, document_type_id: str, business_object_node_type_unique_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_type_mapping` — same semantics."""
        await self._http.delete(
            build_doctype_botype_map_key_path(document_type_id, business_object_node_type_unique_id),
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_MARK_DEFAULT)
    async def mark_default(self, document_type_id: str, business_object_node_type_unique_id: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.mark_default` — same semantics."""
        await self._http.post(
            f"{build_doctype_botype_map_key_path(document_type_id, business_object_node_type_unique_id)}/com.sap.adm.ConfigurationService.markDefault",
            json={},
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_FILE_EXT_POLICIES)
    async def get_all_file_extension_policies(
        self, options: ConfigQueryOptions | None = None
    ) -> list[FileExtensionPolicy]:
        """Async variant of :meth:`_ConfigurationApi.get_all_file_extension_policies` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "DocumentTypeFileExtensionPolicy", params=params, service_base=_CONFIG_SERVICE_PATH
        )
        return [
            FileExtensionPolicy.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_FILE_EXT_POLICY)
    async def create_file_extension_policy(
        self, payload: CreateFileExtensionPolicyInput
    ) -> FileExtensionPolicy:
        """Async variant of :meth:`_ConfigurationApi.create_file_extension_policy` — same semantics."""
        resp = await self._http.post(
            "DocumentTypeFileExtensionPolicy",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
        )
        return FileExtensionPolicy.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_FILE_EXT_POLICY)
    async def delete_file_extension_policy(self, document_type_id: str, file_extension: str) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_file_extension_policy` — same semantics."""
        await self._http.delete(
            f"DocumentTypeFileExtensionPolicy(DocumentTypeID={quote_odata_string_key(document_type_id)},FileExtension={quote_odata_string_key(file_extension)})",
            service_base=_CONFIG_SERVICE_PATH,
        )

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_ALL_APP_TENANTS)
    async def get_all_application_tenants(
        self,
        options: ConfigQueryOptions | None = None,
        *,
        subaccount_id: str | None = None,
    ) -> list[ApplicationTenant]:
        """Async variant of :meth:`_ConfigurationApi.get_all_application_tenants` — same semantics."""
        params = options.to_query_params() if options else {}
        resp = await self._http.get(
            "ApplicationTenant",
            params=params,
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )
        return [
            ApplicationTenant.from_dict(item) for item in resp.json().get("value", [])
        ]

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_CREATE_APP_TENANT)
    async def create_application_tenant(
        self,
        payload: CreateApplicationTenantInput,
        *,
        subaccount_id: str | None = None,
    ) -> ApplicationTenant:
        """Async variant of :meth:`_ConfigurationApi.create_application_tenant` — same semantics."""
        resp = await self._http.post(
            "ApplicationTenant",
            json=payload.to_odata_dict(),
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )
        return ApplicationTenant.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_GET_APP_TENANT)
    async def get_application_tenant(
        self,
        application_tenant_id: str,
        *,
        subaccount_id: str | None = None,
    ) -> ApplicationTenant:
        """Async variant of :meth:`_ConfigurationApi.get_application_tenant` — same semantics."""
        resp = await self._http.get(
            f"ApplicationTenant(ApplicationTenantID='{application_tenant_id}')",
            service_base=_CONFIG_SERVICE_PATH,
            extra_headers=_subaccount_header(subaccount_id),
        )
        return ApplicationTenant.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_CONFIG_DELETE_APP_TENANT)
    async def delete_application_tenant(
        self,
        application_tenant_id: str,
        *,
        subaccount_id: str | None = None,
    ) -> None:
        """Async variant of :meth:`_ConfigurationApi.delete_application_tenant` — same semantics."""
        await self._http.delete(
            f"ApplicationTenant(ApplicationTenantID='{application_tenant_id}')",
            service_base=_CONFIG_SERVICE_PATH,
        )
