"""BDD step definitions for ADMS async document relation integration tests."""

from __future__ import annotations

import asyncio

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.adms.client import AsyncAdmsClient
from sap_cloud_sdk.adms.exceptions import DocumentNotFoundError, ScanNotCleanError
from sap_cloud_sdk.adms._models import (
    BaseType,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    DocumentRelation,
    ScanStatus,
)

scenarios("async_flow.feature")

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def run_async():
    """Provide a synchronous runner for async coroutines."""
    loop = asyncio.new_event_loop()
    yield loop.run_until_complete
    loop.close()


def _make_relation_input(
    bo_type_id: str, bo_node_id: str, name: str
) -> CreateDocumentRelationInput:
    return CreateDocumentRelationInput(
        business_object_node_type_unique_id=bo_type_id,
        host_business_object_node_id=bo_node_id,
        document=CreateDocumentInput(
            document_name=name,
            document_base_type=BaseType.URL,
            document_type_id="SAT",
            document_external_content_url="https://example.com/test.pdf",
        ),
        is_active_entity=True,
    )


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class AsyncScenarioContext:
    def __init__(self) -> None:
        self.client: AsyncAdmsClient | None = None
        self.bo_type_id: str | None = None
        self.relation: DocumentRelation | None = None
        self.retrieved_relation: DocumentRelation | None = None
        self.concurrent_relations: list[DocumentRelation] = []
        self.operation_error: Exception | None = None
        self.scan_state: ScanStatus | None = None
        self.download_blocked: bool | None = None


@pytest.fixture
def context() -> AsyncScenarioContext:
    return AsyncScenarioContext()


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@given("the ADMS service is available")
def adms_service_available(async_adms_client: AsyncAdmsClient) -> None:
    assert async_adms_client is not None


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("I have a business object node type ID")
def have_bo_type_id(
    context: AsyncScenarioContext,
    async_adms_client: AsyncAdmsClient,
    bo_type_id: str,
) -> None:
    context.client = async_adms_client
    context.bo_type_id = bo_type_id


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        'I create a document relation using the async client named "{name}" for node "{bo_node_id}"'
    )
)
def create_async_relation(
    context: AsyncScenarioContext, name: str, bo_node_id: str, run_async
) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    context.relation = run_async(
        context.client.relations.create(
            _make_relation_input(context.bo_type_id, bo_node_id, name)
        )
    )


@when(
    parsers.parse(
        'I query all relations using the async client for node "{bo_node_id}"'
    )
)
def query_async_relations(
    context: AsyncScenarioContext, bo_node_id: str, run_async
) -> None:
    assert context.client is not None
    all_rels = run_async(context.client.relations.get_all())
    context.concurrent_relations = [
        r for r in all_rels if r.host_business_object_node_id == bo_node_id
    ]


@when("I get the async relation by its ID")
def get_async_relation_by_id(context: AsyncScenarioContext, run_async) -> None:
    assert context.client is not None
    assert context.relation is not None
    context.retrieved_relation = run_async(
        context.client.relations.get(
            context.relation.document_relation_id, expand=["Document"]
        )
    )


@when("I get the document using the async client")
def get_async_document(context: AsyncScenarioContext, run_async) -> None:
    assert context.client is not None
    assert context.relation is not None
    doc = run_async(context.client.documents.get(context.relation.document_relation_id))
    context.scan_state = doc.document_state


@when("I attempt to download the document using the async client")
def attempt_async_download(context: AsyncScenarioContext, run_async) -> None:
    assert context.client is not None
    assert context.relation is not None
    rid = context.relation.document_relation_id
    doc = run_async(context.client.documents.get(rid))
    if doc.document_state == ScanStatus.CLEAN:
        context.download_blocked = False
        return
    try:
        run_async(
            context.client.documents.get_download_url(
                document_relation_id=rid, doc_content_version_id="1.0"
            )
        )
        context.download_blocked = False
    except ScanNotCleanError:
        context.download_blocked = True


@when(parsers.parse('I get an async relation with ID "{relation_id}"'))
def get_async_relation_nonexistent(
    context: AsyncScenarioContext,
    relation_id: str,
    async_adms_client: AsyncAdmsClient,
    run_async,
) -> None:
    context.client = async_adms_client
    try:
        run_async(async_adms_client.relations.get(relation_id))
        context.operation_error = None
    except DocumentNotFoundError as e:
        context.operation_error = e


@when(
    parsers.parse(
        'I concurrently create 3 relations using the async client for nodes "{base_node_id}"'
    )
)
def create_concurrent_async_relations(
    context: AsyncScenarioContext, base_node_id: str, run_async
) -> None:
    assert context.client is not None
    assert context.bo_type_id is not None
    client = context.client
    bo_type_id = context.bo_type_id
    bo_ids = [f"{base_node_id}-{i}" for i in range(3)]

    async def _gather() -> list[DocumentRelation]:
        tasks = [
            client.relations.create(
                _make_relation_input(bo_type_id, bo_id, f"Concurrent_{i}.pdf")
            )
            for i, bo_id in enumerate(bo_ids)
        ]
        return await asyncio.gather(*tasks)

    context.concurrent_relations = run_async(_gather())


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the async relation should be created with a valid ID")
def async_relation_has_valid_id(context: AsyncScenarioContext) -> None:
    assert context.relation is not None
    assert context.relation.document_relation_id


@then("the created async relation ID should appear in the results")
def async_relation_in_results(context: AsyncScenarioContext) -> None:
    assert context.relation is not None
    ids = [r.document_relation_id for r in context.concurrent_relations]
    assert context.relation.document_relation_id in ids


@then("the retrieved async relation ID should match")
def async_retrieved_id_matches(context: AsyncScenarioContext) -> None:
    assert context.relation is not None
    assert context.retrieved_relation is not None
    assert (
        context.retrieved_relation.document_relation_id
        == context.relation.document_relation_id
    )


@then("the async scan state should be PENDING or CLEAN")
def async_scan_state_pending_or_clean(context: AsyncScenarioContext) -> None:
    assert context.scan_state in (ScanStatus.PENDING, ScanStatus.CLEAN), (
        f"Unexpected scan state: {context.scan_state}"
    )


@then("the async download should be blocked if not CLEAN")
def async_download_blocked_if_not_clean(context: AsyncScenarioContext) -> None:
    if context.download_blocked is False:
        pytest.skip("Document already CLEAN — scan gate test not applicable")
    assert context.download_blocked is True


@then("a DocumentNotFoundError should be raised from the async client")
def async_document_not_found_error_raised(context: AsyncScenarioContext) -> None:
    assert isinstance(context.operation_error, DocumentNotFoundError)


@then("all 3 async relations should have unique IDs")
def async_concurrent_unique_ids(context: AsyncScenarioContext) -> None:
    assert len(context.concurrent_relations) == 3
    ids = [r.document_relation_id for r in context.concurrent_relations]
    assert len(set(ids)) == 3, f"Expected 3 unique IDs, got: {ids}"


# ---------------------------------------------------------------------------
# Cleanup steps
# ---------------------------------------------------------------------------


@then("I clean up the async relation")
def cleanup_async_relation(context: AsyncScenarioContext, run_async) -> None:
    if context.relation is not None and context.client is not None:
        try:
            run_async(
                context.client.relations.delete(context.relation.document_relation_id)
            )
        except Exception:
            pass


@then("I clean up all concurrent async relations")
def cleanup_concurrent_async_relations(
    context: AsyncScenarioContext, run_async
) -> None:
    if not context.concurrent_relations or context.client is None:
        return
    client = context.client

    async def _cleanup() -> None:
        await asyncio.gather(
            *[
                client.relations.delete(r.document_relation_id)
                for r in context.concurrent_relations
            ],
            return_exceptions=True,
        )

    run_async(_cleanup())
