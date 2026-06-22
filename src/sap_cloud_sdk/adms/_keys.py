"""OData V4 entity-key path builders for ADMS entity sets."""

from sap_cloud_sdk.core.odata._filter import quote_odata_guid_key, quote_odata_string_key


def build_relation_key_path(document_relation_id: str, is_active_entity: bool) -> str:
    """Return ``DocumentRelation(DocumentRelationID=<guid>,IsActiveEntity=<bool>)``."""
    return (
        f"DocumentRelation("
        f"DocumentRelationID={quote_odata_guid_key(document_relation_id)},"
        f"IsActiveEntity={str(is_active_entity).lower()})"
    )


def build_allowed_domain_key_path(allowed_domain_id: str) -> str:
    """Return ``AllowedDomain(AllowedDomainID=<guid>)``."""
    return f"AllowedDomain(AllowedDomainID={quote_odata_guid_key(allowed_domain_id)})"


def build_document_type_key_path(document_type_id: str) -> str:
    """Return ``DocumentType(DocumentTypeID=<string>)`` (Edm.String key)."""
    return f"DocumentType(DocumentTypeID={quote_odata_string_key(document_type_id)})"


def build_business_object_node_type_key_path(unique_id: str) -> str:
    """Return ``BusinessObjectNodeType(BusinessObjectNodeTypeUniqueID=<string>)``."""
    return (
        f"BusinessObjectNodeType("
        f"BusinessObjectNodeTypeUniqueID={quote_odata_string_key(unique_id)})"
    )


def build_doctype_botype_map_key_path(map_id: str) -> str:
    """Return ``DocumentTypeBusinessObjectTypeMap(DocumentTypeBOTypeMapID=<guid>)``."""
    return (
        f"DocumentTypeBusinessObjectTypeMap("
        f"DocumentTypeBOTypeMapID={quote_odata_guid_key(map_id)})"
    )


def build_job_status_key_path(job_id: str) -> str:
    """Return ``JobStatus(JobID=<string>)`` (Edm.String key)."""
    return f"JobStatus(JobID={quote_odata_string_key(job_id)})"
