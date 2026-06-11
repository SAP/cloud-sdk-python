"""Unit tests for DMS data models."""

from sap_cloud_sdk.adms._models import (
    AllowedDomain,
    BaseType,
    BusinessObjectNodeType,
    CreateAllowedDomainInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentTypeInput,
    DeleteUserDataJobParameters,
    Document,
    DocumentContentVersion,
    DocumentRelation,
    DocumentType,
    DocumentTypeBusinessObjectTypeMap,
    DraftActivateInput,
    DraftInput,
    JobOutput,
    JobStatus,
    ScanStatus,
    UpdateDocumentInput,
    ZipDownloadJobParameters,
)


# ---------------------------------------------------------------------------
# Enum behaviour
# ---------------------------------------------------------------------------


class TestScanStatus:
    def test_clean_is_downloadable(self):
        assert ScanStatus.CLEAN.is_downloadable() is True

    def test_non_clean_not_downloadable(self):
        for status in (
            ScanStatus.PENDING,
            ScanStatus.FAILED,
            ScanStatus.QUARANTINED,
            ScanStatus.FILE_EXT_RESTRICTED,
        ):
            assert status.is_downloadable() is False, (
                f"{status} should not be downloadable"
            )

    def test_string_values(self):
        assert ScanStatus.PENDING == "PENDING"
        assert ScanStatus.CLEAN == "CLEAN"


class TestJobStatus:
    def test_terminal_states(self):
        assert JobStatus.COMPLETED.is_terminal() is True
        assert JobStatus.FAILED.is_terminal() is True
        assert JobStatus.CANCELLED.is_terminal() is True

    def test_non_terminal_states(self):
        assert JobStatus.NOT_STARTED.is_terminal() is False
        assert JobStatus.IN_PROGRESS.is_terminal() is False
        assert JobStatus.PAUSED.is_terminal() is False


# ---------------------------------------------------------------------------
# Document models
# ---------------------------------------------------------------------------


class TestDocument:
    def test_from_dict_full(self):
        data = {
            "DocumentID": "doc-1",
            "IsActiveEntity": True,
            "DocumentName": "Invoice.pdf",
            "DocumentBaseType": "D",
            "DocumentTypeID": "INVOICE",
            "DocumentState": "CLEAN",
            "DocumentMimeType": "application/pdf",
            "DocumentSizeInByte": 1024,
            "DocumentIsLocked": False,
        }
        doc = Document.from_dict(data)
        assert doc.document_id == "doc-1"
        assert doc.document_state == ScanStatus.CLEAN
        assert doc.document_base_type == BaseType.DOCUMENT
        assert doc.document_mime_type == "application/pdf"

    def test_from_dict_unknown_scan_status_defaults_to_pending(self):
        doc = Document.from_dict({"DocumentID": "x", "DocumentState": "UNKNOWN_STATE"})
        assert doc.document_state == ScanStatus.PENDING

    def test_from_dict_upload_urls_default_empty(self):
        doc = Document.from_dict({"DocumentID": "x"})
        assert doc.document_content_upload_urls == []


class TestCreateDocumentInput:
    def test_to_odata_dict_minimal(self):
        inp = CreateDocumentInput(document_name="test.pdf")
        payload = inp.to_odata_dict()
        assert payload["DocumentName"] == "test.pdf"
        assert payload["DocumentBaseType"] == "D"
        assert "DocumentTypeID" not in payload

    def test_to_odata_dict_with_optional_fields(self):
        inp = CreateDocumentInput(
            document_name="test.pdf",
            document_type_id="INVOICE",
            document_description="An invoice",
            document_is_multipart=True,
            document_no_of_parts=3,
        )
        payload = inp.to_odata_dict()
        assert payload["DocumentTypeID"] == "INVOICE"
        assert payload["DocumentDescription"] == "An invoice"
        assert payload["DocumentIsMultipart"] is True
        assert payload["DocumentNoOfParts"] == 3


class TestUpdateDocumentInput:
    def test_only_set_fields_serialised(self):
        upd = UpdateDocumentInput(document_name="NewName.pdf")
        payload = upd.to_odata_dict()
        assert payload == {"DocumentName": "NewName.pdf"}

    def test_all_none_gives_empty_dict(self):
        upd = UpdateDocumentInput()
        assert upd.to_odata_dict() == {}


# ---------------------------------------------------------------------------
# DocumentRelation models
# ---------------------------------------------------------------------------


class TestDocumentRelation:
    def test_from_dict_with_expanded_document(self):
        data = {
            "DocumentRelationID": "rel-1",
            "BusinessObjectNodeTypeUniqueID": "PurchaseOrder",
            "HostBusinessObjectNodeID": "PO-001",
            "Document": {
                "DocumentID": "doc-1",
                "DocumentName": "inv.pdf",
                "DocumentBaseType": "D",
                "DocumentTypeID": "INV",
                "DocumentState": "CLEAN",
            },
        }
        rel = DocumentRelation.from_dict(data)
        assert rel.document_relation_id == "rel-1"
        assert rel.document is not None
        assert rel.document.document_id == "doc-1"

    def test_from_dict_without_document(self):
        data = {
            "DocumentRelationID": "rel-2",
            "BusinessObjectNodeTypeUniqueID": "SalesOrder",
            "HostBusinessObjectNodeID": "SO-002",
        }
        rel = DocumentRelation.from_dict(data)
        assert rel.document is None


class TestCreateDocumentRelationInput:
    def test_to_odata_dict(self):
        inp = CreateDocumentRelationInput(
            business_object_node_type_unique_id="PurchaseOrder",
            host_business_object_node_id="PO-001",
            document=CreateDocumentInput(document_name="inv.pdf"),
        )
        payload = inp.to_odata_dict()
        assert payload["BusinessObjectNodeTypeUniqueID"] == "PurchaseOrder"
        assert payload["HostBusinessObjectNodeID"] == "PO-001"
        assert payload["Document"]["DocumentName"] == "inv.pdf"
        assert "HostBusinessObjNodeDisplayID" not in payload

    def test_optional_display_id_included_when_set(self):
        inp = CreateDocumentRelationInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
            document=CreateDocumentInput(document_name="f.pdf"),
            host_business_obj_node_display_id="Display PO-1",
        )
        assert inp.to_odata_dict()["HostBusinessObjNodeDisplayID"] == "Display PO-1"


class TestDraftInput:
    def test_to_odata_dict(self):
        di = DraftInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )
        assert di.to_odata_dict() == {
            "BusinessObjectNodeTypeUniqueID": "PO",
            "HostBusinessObjectNodeID": "PO-1",
        }


class TestDraftActivateInput:
    def test_inherits_fields(self):
        dai = DraftActivateInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
            late_host_business_object_node_id="PO-late",
        )
        d = dai.to_odata_dict()
        assert d["BusinessObjectNodeTypeUniqueID"] == "PO"
        assert d["LateHostBusinessObjectNodeID"] == "PO-late"

    def test_late_id_omitted_when_none(self):
        dai = DraftActivateInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )
        assert "LateHostBusinessObjectNodeID" not in dai.to_odata_dict()


# ---------------------------------------------------------------------------
# Job models
# ---------------------------------------------------------------------------


class TestZipDownloadJobParameters:
    def test_to_odata_dict(self):
        params = ZipDownloadJobParameters(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )
        d = params.to_odata_dict()
        assert d["DocumentRelationIDs"] == []
        assert d["IsActiveEntity"] is True


class TestDeleteUserDataJobParameters:
    def test_to_odata_dict_with_replacement(self):
        params = DeleteUserDataJobParameters(user_id="u1", replacement_user_id="u2")
        d = params.to_odata_dict()
        assert d == {"UserID": "u1", "ReplacementUserID": "u2"}

    def test_to_odata_dict_without_replacement(self):
        params = DeleteUserDataJobParameters(user_id="u1")
        d = params.to_odata_dict()
        assert d == {"UserID": "u1"}
        assert "ReplacementUserID" not in d


class TestJobOutput:
    def test_from_dict_with_value_wrapper(self):
        data = {
            "value": {
                "JobID": "job-1",
                "JobStatus": "IN_PROGRESS",
                "JobProgressPercentage": 50,
            }
        }
        out = JobOutput.from_dict(data)
        assert out.job_id == "job-1"
        assert out.job_status == JobStatus.IN_PROGRESS
        assert out.job_progress_percentage == 50

    def test_from_dict_without_value_wrapper(self):
        data = {"JobID": "job-2", "JobStatus": "COMPLETED"}
        out = JobOutput.from_dict(data)
        assert out.job_id == "job-2"
        assert out.job_status == JobStatus.COMPLETED

    def test_from_dict_unknown_status_is_none(self):
        out = JobOutput.from_dict({"JobStatus": "UNKNOWN_STATE"})
        assert out.job_status is None


class TestDocumentContentVersion:
    def test_from_dict(self):
        data = {
            "DocumentID": "doc-1",
            "IsActiveEntity": True,
            "DocContentVersionID": "1.0",
            "DocContentVersionState": "CLEAN",
            "DocContentVersionIsLatest": True,
        }
        v = DocumentContentVersion.from_dict(data)
        assert v.document_id == "doc-1"
        assert v.doc_content_version_id == "1.0"
        assert v.doc_content_version_state == ScanStatus.CLEAN
        assert v.doc_content_version_is_latest is True


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


class TestAllowedDomain:
    def test_from_dict(self):
        data = {
            "AllowedDomainID": "ad-1",
            "AllowedDomainHostName": "storage.example.com",
            "AllowedDomainProtocol": "https",
        }
        ad = AllowedDomain.from_dict(data)
        assert ad.allowed_domain_id == "ad-1"
        assert ad.allowed_domain_host_name == "storage.example.com"
        assert ad.allowed_domain_protocol == "https"

    def test_from_dict_missing_keys_default_to_empty_string(self):
        ad = AllowedDomain.from_dict({})
        assert ad.allowed_domain_id == ""
        assert ad.allowed_domain_host_name == ""
        assert ad.allowed_domain_protocol == ""

    def test_to_odata_dict_excludes_id(self):
        ad = AllowedDomain(
            allowed_domain_id="ad-1",
            allowed_domain_host_name="storage.example.com",
            allowed_domain_protocol="https",
        )
        d = ad.to_odata_dict()
        assert "AllowedDomainID" not in d
        assert d["AllowedDomainHostName"] == "storage.example.com"
        assert d["AllowedDomainProtocol"] == "https"


class TestCreateAllowedDomainInput:
    def test_to_odata_dict(self):
        inp = CreateAllowedDomainInput(host_name="example.com", protocol="https")
        d = inp.to_odata_dict()
        assert d == {
            "AllowedDomainHostName": "example.com",
            "AllowedDomainProtocol": "https",
        }


class TestDocumentType:
    def test_from_dict(self):
        data = {
            "DocumentTypeID": "INVOICE",
            "DocumentTypeName": "Invoice",
            "DocumentTypeDescription": "Vendor invoices",
        }
        dt = DocumentType.from_dict(data)
        assert dt.document_type_id == "INVOICE"
        assert dt.document_type_name == "Invoice"
        assert dt.document_type_description == "Vendor invoices"

    def test_from_dict_no_description(self):
        data = {"DocumentTypeID": "INVOICE", "DocumentTypeName": "Invoice"}
        dt = DocumentType.from_dict(data)
        assert dt.document_type_description is None

    def test_to_odata_dict_includes_description_when_set(self):
        dt = DocumentType(
            document_type_id="INVOICE",
            document_type_name="Invoice",
            document_type_description="Vendor invoices",
        )
        d = dt.to_odata_dict()
        assert d["DocumentTypeID"] == "INVOICE"
        assert d["DocumentTypeName"] == "Invoice"
        assert d["DocumentTypeDescription"] == "Vendor invoices"

    def test_to_odata_dict_omits_description_when_none(self):
        dt = DocumentType(document_type_id="INVOICE", document_type_name="Invoice")
        d = dt.to_odata_dict()
        assert "DocumentTypeDescription" not in d


class TestCreateDocumentTypeInput:
    def test_to_odata_dict_with_description(self):
        inp = CreateDocumentTypeInput(
            document_type_id="CONTRACT",
            document_type_name="Contract",
            document_type_description="Legal contracts",
        )
        d = inp.to_odata_dict()
        assert d == {
            "DocumentTypeID": "CONTRACT",
            "DocumentTypeName": "Contract",
            "DocumentTypeDescription": "Legal contracts",
        }

    def test_to_odata_dict_without_description(self):
        inp = CreateDocumentTypeInput(
            document_type_id="CONTRACT", document_type_name="Contract"
        )
        d = inp.to_odata_dict()
        assert "DocumentTypeDescription" not in d


class TestBusinessObjectNodeType:
    def test_from_dict(self):
        data = {
            "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
            "BusinessObjectNodeType": "PurchaseOrder",
            "BusinessObjectNodeTypeName": "Purchase Order",
            "ApplicationTenantID": "tenant-1",
        }
        bo = BusinessObjectNodeType.from_dict(data)
        assert bo.business_object_node_type_unique_id == "bo-uuid-1"
        assert bo.business_object_node_type == "PurchaseOrder"
        assert bo.business_object_node_type_name == "Purchase Order"
        assert bo.application_tenant_id == "tenant-1"

    def test_from_dict_optional_fields(self):
        data = {
            "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
            "BusinessObjectNodeType": "PurchaseOrder",
            "BusinessObjectNodeTypeName": "Purchase Order",
        }
        bo = BusinessObjectNodeType.from_dict(data)
        assert bo.application_tenant_id is None
        assert bo.odm_entity_name is None

    def test_to_odata_dict(self):
        bo = BusinessObjectNodeType(
            business_object_node_type_unique_id="bo-uuid-1",
            business_object_node_type="PurchaseOrder",
            business_object_node_type_name="Purchase Order",
        )
        d = bo.to_odata_dict()
        assert d["BusinessObjectNodeType"] == "PurchaseOrder"
        assert d["BusinessObjectNodeTypeName"] == "Purchase Order"
        assert "BusinessObjectNodeTypeID" not in d


class TestCreateBusinessObjectNodeTypeInput:
    def test_to_odata_dict(self):
        inp = CreateBusinessObjectNodeTypeInput(
            business_object_node_type="SalesOrder",
            business_object_node_type_name="Sales Order",
            application_tenant_id="tenant-uuid",
        )
        d = inp.to_odata_dict()
        assert d == {
            "BusinessObjectNodeType": "SalesOrder",
            "BusinessObjectNodeTypeName": "Sales Order",
            "ApplicationTenantID": "tenant-uuid",
        }

    def test_to_odata_dict_required_fields(self):
        inp = CreateBusinessObjectNodeTypeInput(
            business_object_node_type="PO",
            business_object_node_type_name="Purchase Order",
            application_tenant_id="tenant-uuid",
        )
        d = inp.to_odata_dict()
        assert "BusinessObjectNodeType" in d
        assert "ApplicationTenantID" in d
        assert "BusinessObjectNodeTypeID" not in d


class TestDocumentTypeBusinessObjectTypeMap:
    def test_from_dict(self):
        data = {
            "DocumentTypeBOTypeMapID": "map-uuid-1",
            "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
            "DocumentTypeID": "INVOICE",
            "IsDefault": True,
        }
        m = DocumentTypeBusinessObjectTypeMap.from_dict(data)
        assert m.document_type_bo_type_map_id == "map-uuid-1"
        assert m.business_object_node_type_unique_id == "bo-uuid-1"
        assert m.document_type_id == "INVOICE"
        assert m.is_default is True

    def test_from_dict_default_is_false(self):
        data = {
            "DocumentTypeBOTypeMapID": "map-uuid-2",
            "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
            "DocumentTypeID": "CONTRACT",
        }
        m = DocumentTypeBusinessObjectTypeMap.from_dict(data)
        assert m.is_default is False


class TestCreateDocumentTypeBoTypeMapInput:
    def test_to_odata_dict(self):
        inp = CreateDocumentTypeBoTypeMapInput(
            business_object_node_type_unique_id="bo-uuid-1",
            document_type_id="INVOICE",
            is_default=True,
        )
        d = inp.to_odata_dict()
        assert d == {
            "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
            "DocumentTypeID": "INVOICE",
            "IsDefault": True,
        }

    def test_is_default_defaults_to_false(self):
        inp = CreateDocumentTypeBoTypeMapInput(
            business_object_node_type_unique_id="bo-uuid-1",
            document_type_id="INVOICE",
        )
        assert inp.is_default is False
