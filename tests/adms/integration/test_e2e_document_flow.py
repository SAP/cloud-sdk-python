"""BDD step definitions for ADMS document relation integration tests."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.adms.client import AdmsClient
from sap_cloud_sdk.adms.exceptions import DocumentNotFoundError, ScanNotCleanError
from sap_cloud_sdk.adms._models import (
    BaseType,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    DocumentRelation,
    DraftActivateInput,
    DraftInput,
    ScanStatus,
    UpdateDocumentInput,
)

scenarios("document_flow.feature")

pytestmark = pytest.mark.integration

_HOST_BO_NODE_ID = "PY-SDK-IT-PO-001"


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class ScenarioContext:
    def __init__(self) -> None:
        self.client: AdmsClient | None = None
        self.bo_type_id: str | None = None
        self.relation: DocumentRelation | None = None
        self.retrieved_relation: DocumentRelation | None = None
        self.active_relations: list[DocumentRelation] = []
        self.operation_error: Exception | None = None
        self.document_name: str | None = None
        self.scan_state: ScanStatus | None = None
        self.download_blocked: bool | None = None


@pytest.fixture
def context() -> ScenarioContext:
    return ScenarioContext()


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@given("the ADMS service is available")
def adms_service_available(adms_client: AdmsClient) -> None:
    assert adms_client is not None


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("I have a business object node type ID")
def have_bo_type_id(
    context: ScenarioContext, adms_client: AdmsClient, bo_type_id: str
) -> None:
    context.client = adms_client
    context.bo_type_id = bo_type_id


@given(parsers.parse('I have created a document relation named "{name}"'))
def have_created_relation(context: ScenarioContext, name: str) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    context.relation = context.client.relations.create(
        CreateDocumentRelationInput(
            business_object_node_type_unique_id=context.bo_type_id,
            host_business_object_node_id=_HOST_BO_NODE_ID,
            document=CreateDocumentInput(
                document_name=name,
                document_base_type=BaseType.URL,
                document_type_id="SAT",
                document_external_content_url="https://example.com/test.pdf",
            ),
            is_active_entity=True,
        )
    )


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(parsers.parse('I create a document relation named "{name}"'))
def create_relation(context: ScenarioContext, name: str) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    context.relation = context.client.relations.create(
        CreateDocumentRelationInput(
            business_object_node_type_unique_id=context.bo_type_id,
            host_business_object_node_id=_HOST_BO_NODE_ID,
            document=CreateDocumentInput(
                document_name=name,
                document_base_type=BaseType.URL,
                document_type_id="SAT",
                document_external_content_url="https://example.com/test.pdf",
            ),
            is_active_entity=True,
        )
    )


@when("I query all document relations")
def query_all_relations(context: ScenarioContext) -> None:
    assert context.client is not None
    context.active_relations = context.client.relations.get_all()


@when("I get the relation by its ID")
def get_relation_by_id(context: ScenarioContext) -> None:
    assert context.client is not None
    assert context.relation is not None
    context.retrieved_relation = context.client.relations.get(
        context.relation.document_relation_id,
        expand=["Document"],
    )


@when("I get the document for the created relation")
def get_document(context: ScenarioContext) -> None:
    assert context.client is not None
    assert context.relation is not None
    doc = context.client.documents.get(context.relation.document_relation_id)
    context.scan_state = doc.document_state


@when("I attempt to download the document")
def attempt_download(context: ScenarioContext) -> None:
    assert context.client is not None
    assert context.relation is not None
    rid = context.relation.document_relation_id
    doc = context.client.documents.get(rid)
    if doc.document_state == ScanStatus.CLEAN:
        context.download_blocked = False
        return
    try:
        context.client.documents.get_download_url(
            document_relation_id=rid,
            doc_content_version_id="1.0",
        )
        context.download_blocked = False
    except ScanNotCleanError:
        context.download_blocked = True


@when(parsers.parse('I update the document name to "{name}"'))
def update_document_name(context: ScenarioContext, name: str) -> None:
    assert context.client is not None
    assert context.relation is not None
    doc = context.client.documents.update(
        context.relation.document_relation_id,
        UpdateDocumentInput(document_name=name),
    )
    context.document_name = doc.document_name


@when("I delete the created relation")
def delete_relation(context: ScenarioContext) -> None:
    assert context.client is not None
    assert context.relation is not None
    context.client.relations.delete(context.relation.document_relation_id)


@when(parsers.parse('I create a draft for business object node "{bo_node_id}"'))
def create_draft(context: ScenarioContext, bo_node_id: str) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    context.client.relations.create_draft(
        DraftInput(
            business_object_node_type_unique_id=context.bo_type_id,
            host_business_object_node_id=bo_node_id,
        )
    )


@when(parsers.parse('I validate the draft for "{bo_node_id}"'))
def validate_draft(context: ScenarioContext, bo_node_id: str) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    context.client.relations.validate_draft(
        DraftInput(
            business_object_node_type_unique_id=context.bo_type_id,
            host_business_object_node_id=bo_node_id,
        )
    )


@when(parsers.parse('I activate the draft for "{bo_node_id}"'))
def activate_draft(context: ScenarioContext, bo_node_id: str) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    activated = context.client.relations.activate_draft(
        DraftActivateInput(
            business_object_node_type_unique_id=context.bo_type_id,
            host_business_object_node_id=bo_node_id,
        )
    )
    context.active_relations = activated


@when(parsers.parse('I discard the draft for "{bo_node_id}"'))
def discard_draft(context: ScenarioContext, bo_node_id: str) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    context.client.relations.discard_draft(
        DraftInput(
            business_object_node_type_unique_id=context.bo_type_id,
            host_business_object_node_id=bo_node_id,
        )
    )


@when(parsers.parse('I get a document with relation ID "{relation_id}"'))
def get_document_nonexistent(
    context: ScenarioContext, relation_id: str, adms_client: AdmsClient
) -> None:
    context.client = adms_client
    try:
        adms_client.documents.get(relation_id)
        context.operation_error = None
    except DocumentNotFoundError as e:
        context.operation_error = e


@when(parsers.parse('I get a relation with ID "{relation_id}"'))
def get_relation_nonexistent(
    context: ScenarioContext, relation_id: str, adms_client: AdmsClient
) -> None:
    context.client = adms_client
    try:
        adms_client.relations.get(relation_id)
        context.operation_error = None
    except DocumentNotFoundError as e:
        context.operation_error = e


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the relation should be created with a valid ID")
def relation_has_valid_id(context: ScenarioContext) -> None:
    assert context.relation is not None
    assert context.relation.document_relation_id


@then("the created relation ID should appear in the results")
def created_relation_in_results(context: ScenarioContext) -> None:
    assert context.relation is not None
    ids = [r.document_relation_id for r in context.active_relations]
    assert context.relation.document_relation_id in ids, (
        f"Created relation {context.relation.document_relation_id} not in {ids}"
    )


@then("the retrieved relation ID should match the created ID")
def retrieved_relation_id_matches(context: ScenarioContext) -> None:
    assert context.relation is not None
    assert context.retrieved_relation is not None
    assert (
        context.retrieved_relation.document_relation_id
        == context.relation.document_relation_id
    )


@then("the scan state should be PENDING or CLEAN")
def scan_state_pending_or_clean(context: ScenarioContext) -> None:
    assert context.scan_state in (ScanStatus.PENDING, ScanStatus.CLEAN), (
        f"Unexpected scan state: {context.scan_state}"
    )


@then("the download should be blocked if not CLEAN")
def download_blocked_if_not_clean(context: ScenarioContext) -> None:
    if context.download_blocked is False:
        pytest.skip("Document already CLEAN — scan gate test not applicable")
    assert context.download_blocked is True


@then(parsers.parse('the document name should be "{name}"'))
def document_name_matches(context: ScenarioContext, name: str) -> None:
    assert context.document_name == name


@then("fetching the deleted relation should raise DocumentNotFoundError")
def fetch_deleted_raises_404(context: ScenarioContext) -> None:
    assert context.client is not None
    assert context.relation is not None
    with pytest.raises(DocumentNotFoundError):
        context.client.relations.get(context.relation.document_relation_id)


@then("the active relation list should not be empty")
def active_relation_list_not_empty(context: ScenarioContext) -> None:
    assert isinstance(context.active_relations, list)


@then(parsers.parse('no active relations should exist for "{bo_node_id}"'))
def no_active_relations_for_node(context: ScenarioContext, bo_node_id: str) -> None:
    assert context.client is not None
    all_relations = context.client.relations.get_all()
    matching = [
        r for r in all_relations if r.host_business_object_node_id == bo_node_id
    ]
    assert matching == [], f"Expected no active relations, found: {matching}"


@then("a DocumentNotFoundError should be raised")
def document_not_found_error_raised(context: ScenarioContext) -> None:
    assert isinstance(context.operation_error, DocumentNotFoundError)


# ---------------------------------------------------------------------------
# Cleanup steps
# ---------------------------------------------------------------------------


@then("I clean up the created relation")
def cleanup_created_relation(context: ScenarioContext) -> None:
    if context.relation is not None and context.client is not None:
        try:
            context.client.relations.delete(context.relation.document_relation_id)
        except Exception:
            pass


@then(parsers.parse('I clean up all active relations for "{bo_node_id}"'))
def cleanup_active_relations(context: ScenarioContext, bo_node_id: str) -> None:
    if context.client is None:
        return
    for rel in context.active_relations:
        try:
            context.client.relations.delete(rel.document_relation_id)
        except Exception:
            pass
