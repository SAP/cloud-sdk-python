"""Unit tests for ADMS entity-key path builders and OData quoters."""

import pytest

from sap_cloud_sdk.adms._keys import (
    build_allowed_domain_key_path,
    build_business_object_node_type_key_path,
    build_doctype_botype_map_key_path,
    build_document_type_key_path,
    build_job_status_key_path,
    build_relation_key_path,
)
from sap_cloud_sdk.core.odata._filter import quote_odata_guid_key, quote_odata_string_key


_GUID = "a1b2c3d4-e5f6-4789-ab12-fedcba987654"


class TestQuoteOdataStringKey:
    def test_plain_string_is_quoted(self):
        assert quote_odata_string_key("job-123") == "'job-123'"

    def test_single_quote_is_doubled(self):
        assert quote_odata_string_key("O'Brien") == "'O''Brien'"

    def test_injection_attempt_is_escaped(self):
        out = quote_odata_string_key("x'); DROP TABLE--")
        assert "'" not in out[1:-1].replace("''", "")

    def test_empty_string(self):
        assert quote_odata_string_key("") == "''"


class TestQuoteOdataGuidKey:
    def test_valid_guid_is_normalised(self):
        out = quote_odata_guid_key(_GUID)
        assert out == _GUID

    def test_uppercase_guid_is_lowercased(self):
        out = quote_odata_guid_key(_GUID.upper())
        assert out == _GUID

    def test_invalid_guid_raises(self):
        with pytest.raises(ValueError, match="invalid OData Edm.Guid key"):
            quote_odata_guid_key("not-a-guid")

    def test_guid_with_injected_path_raises(self):
        with pytest.raises(ValueError):
            quote_odata_guid_key(f"{_GUID})/Documents")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            quote_odata_guid_key("")

    def test_none_raises(self):
        with pytest.raises((ValueError, AttributeError, TypeError)):
            quote_odata_guid_key(None)  # type: ignore[arg-type]


class TestEntityKeyPathBuilders:
    def test_relation_key_active(self):
        path = build_relation_key_path(_GUID, True)
        assert path == f"DocumentRelation(DocumentRelationID={_GUID},IsActiveEntity=true)"

    def test_relation_key_draft(self):
        path = build_relation_key_path(_GUID, False)
        assert "IsActiveEntity=false" in path

    def test_allowed_domain_key(self):
        path = build_allowed_domain_key_path(_GUID)
        assert path == f"AllowedDomain(AllowedDomainID={_GUID})"

    def test_document_type_key_quotes_string(self):
        path = build_document_type_key_path("INVOICE")
        assert path == "DocumentType(DocumentTypeID='INVOICE')"

    def test_document_type_key_escapes_quotes(self):
        path = build_document_type_key_path("O'Brien")
        assert "'O''Brien'" in path

    def test_business_object_node_type_key(self):
        path = build_business_object_node_type_key_path("PurchaseOrder")
        assert "BusinessObjectNodeType" in path
        assert "'PurchaseOrder'" in path

    def test_doctype_botype_map_key(self):
        path = build_doctype_botype_map_key_path(_GUID)
        assert "DocumentTypeBusinessObjectTypeMap" in path
        assert _GUID in path

    def test_job_status_key(self):
        path = build_job_status_key_path("job-123")
        assert path == "JobStatus(JobID='job-123')"

    def test_guid_key_is_not_quoted(self):
        # Edm.Guid keys must NOT have single quotes per OData V4 spec
        path = build_relation_key_path(_GUID, True)
        assert f"DocumentRelationID='{_GUID}'" not in path
        assert f"DocumentRelationID={_GUID}" in path
