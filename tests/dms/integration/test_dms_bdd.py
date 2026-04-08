"""BDD step definitions for DMS integration tests."""

import io
import logging
import uuid
from typing import List, Optional, Union

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from requests import Response

from sap_cloud_sdk.dms.client import DMSClient
from sap_cloud_sdk.dms.model import (
    Acl,
    ChildrenOptions,
    ChildrenPage,
    CmisObject,
    CreateConfigRequest,
    Document,
    Folder,
    Repository,
    RepositoryConfig,
)
from sap_cloud_sdk.dms.exceptions import (
    DMSError,
    DMSObjectNotFoundException,
)

logger = logging.getLogger(__name__)

# Load scenarios from feature file
scenarios("dms.feature")


# ==================== CONTEXT CLASS ====================


class DMSTestContext:
    """Context to store test state between BDD steps."""

    def __init__(self):
        self.repo: Optional[Repository] = None
        self.repos: List[Repository] = []
        self.repo_id: str = ""
        self.root_folder_id: str = ""
        self.folder: Optional[Folder] = None
        self.document: Optional[Document] = None
        self.pwc: Optional[Document] = None
        self.checked_in_doc: Optional[Document] = None
        self.config: Optional[RepositoryConfig] = None
        self.configs: List[RepositoryConfig] = []
        self.acl: Optional[Acl] = None
        self.children_page: Optional[ChildrenPage] = None
        self.content_response: Optional[Response] = None
        self.retrieved_object: Optional[Union[Folder, Document, CmisObject]] = None
        self.updated_object: Optional[Union[Folder, Document, CmisObject]] = None
        self.content_bytes: Optional[bytes] = None
        self.operation_success: bool = False
        self.operation_error: Optional[Exception] = None
        self.cleanup_configs: List[str] = []  # config IDs
        self.cleanup_objects: List[tuple] = []  # (repo_id, object_id)
        self.child_doc_id: Optional[str] = None
        self._config_request: Optional[CreateConfigRequest] = None
        self._expected_updated_name: str = ""


@pytest.fixture
def context(dms_client: DMSClient):
    """Provide a fresh test context for each scenario."""
    ctx = DMSTestContext()
    yield ctx
    # Always clean up resources, even if the test fails
    if ctx.content_response is not None:
        ctx.content_response.close()
    for config_id in ctx.cleanup_configs:
        try:
            dms_client.delete_config(config_id)
        except Exception as e:
            logger.warning("Cleanup failed for config %s: %s", config_id, e)
    for repo_id, object_id in ctx.cleanup_objects:
        try:
            _delete_cmis_object(dms_client, repo_id, object_id)
        except Exception as e:
            logger.warning("Cleanup failed for object %s: %s", object_id, e)


# ==================== BACKGROUND STEPS ====================


@given("the DMS service is available")
def dms_service_available(dms_client: DMSClient):
    """Verify that the DMS client is available."""
    assert dms_client is not None


@given("I have a valid DMS client")
def have_valid_client(dms_client: DMSClient):
    """Verify the DMS client is properly configured."""
    assert dms_client is not None


# ==================== REPOSITORY: GIVEN ====================


@given("I select the first available repository")
def select_first_repo(context: DMSTestContext, dms_client: DMSClient):
    """Select the first repository from the list."""
    repos = dms_client.get_all_repositories()
    assert len(repos) > 0, "No repositories available for testing"
    context.repo = repos[0]
    # repo.id (UUID) is used in the CMIS browser URL; cmis_repository_id is the root folder objectId
    context.repo_id = repos[0].id


@given("I select a version-enabled repository")
def select_version_repo(context: DMSTestContext, dms_client: DMSClient):
    """Select a repository that has versioning enabled."""
    repos = dms_client.get_all_repositories()
    version_repo = None
    for r in repos:
        if r.get_param("isVersionEnabled") in (True, "true", "True"):
            version_repo = r
            break
    if version_repo is None:
        pytest.skip("No version-enabled repository available")  # ty: ignore[invalid-argument-type, too-many-positional-arguments]
    context.repo = version_repo
    context.repo_id = version_repo.id


@given("I use the root folder as parent")
def use_root_folder(context: DMSTestContext, dms_client: DMSClient):
    """Get the root folder ID for the selected repository."""
    # The CMIS root folder objectId is the cmis_repository_id; repo.id (UUID) is used for the URL
    context.root_folder_id = context.repo.cmis_repository_id  # ty: ignore[unresolved-attribute]


# ==================== CONFIG: GIVEN ====================


@given(parsers.parse('I have a config named "{name}" with value "{value}"'))
def have_config(context: DMSTestContext, name: str, value: str):
    """Prepare a configuration request."""
    context.config = None  # Will be set after creation
    context._config_request = CreateConfigRequest(config_name=name, config_value=value)


# ==================== DOCUMENT CONTENT: GIVEN ====================


@given(parsers.parse('I have document content "{content}"'))
def have_document_content(context: DMSTestContext, content: str):
    """Set up content bytes for document upload."""
    context.content_bytes = content.encode("utf-8")


# ==================== SETUP STEPS (Given with side effects) ====================


@given(parsers.parse('I upload a document named "{name}" with mime type "{mime_type}"'))
def given_upload_document(
    context: DMSTestContext, dms_client: DMSClient, name: str, mime_type: str
):
    """Upload a document as a prerequisite step."""
    unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
    doc = dms_client.create_document(
        context.repo_id,
        context.root_folder_id,
        unique_name,
        io.BytesIO(context.content_bytes),  # ty: ignore[invalid-argument-type]
        mime_type=mime_type,
    )
    context.document = doc
    context.cleanup_objects.append((context.repo_id, doc.object_id))


@given(parsers.parse('I create a folder named "{name}"'))
def given_create_folder(context: DMSTestContext, dms_client: DMSClient, name: str):
    """Create a folder as a prerequisite step."""
    unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
    folder = dms_client.create_folder(
        context.repo_id,
        context.root_folder_id,
        unique_name,
    )
    context.folder = folder
    context.cleanup_objects.append((context.repo_id, folder.object_id))


@given(parsers.parse('I create a child document "{name}" in the folder'))
def create_child_document(context: DMSTestContext, dms_client: DMSClient, name: str):
    """Create a child document inside the previously created folder."""
    unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
    doc = dms_client.create_document(
        context.repo_id,
        context.folder.object_id,  # ty: ignore[unresolved-attribute]
        unique_name,
        io.BytesIO(b"child document content"),
        mime_type="text/plain",
    )
    context.child_doc_id = doc.object_id
    # Child will be cleaned up when its parent folder is deleted


# ==================== REPOSITORY: WHEN ====================


@when("I list all repositories")
def list_repos(context: DMSTestContext, dms_client: DMSClient):
    """List all repositories."""
    try:
        context.repos = dms_client.get_all_repositories()
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I get repository details")
def get_repo_details(context: DMSTestContext, dms_client: DMSClient):
    """Get details of the selected repository."""
    try:
        context.repo = dms_client.get_repository(context.repo.id)  # ty: ignore[unresolved-attribute]
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== CONFIG: WHEN ====================


@when("I create the configuration")
def create_config(context: DMSTestContext, dms_client: DMSClient):
    """Create a repository configuration."""
    try:
        context.config = dms_client.create_config(context._config_request)  # ty: ignore[invalid-argument-type]
        context.cleanup_configs.append(context.config.id)
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I delete the created configuration")
def delete_config(context: DMSTestContext, dms_client: DMSClient):
    """Delete the previously created configuration."""
    context.operation_error = None
    try:
        dms_client.delete_config(context.config.id)  # ty: ignore[unresolved-attribute]
        if context.config.id in context.cleanup_configs:  # ty: ignore[unresolved-attribute]
            context.cleanup_configs.remove(context.config.id)  # ty: ignore[unresolved-attribute]
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I list all configurations")
def list_configs(context: DMSTestContext, dms_client: DMSClient):
    """List all configurations."""
    try:
        context.configs = dms_client.get_configs()
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== FOLDER: WHEN ====================


@when(parsers.parse('I create a folder named "{name}"'))
def when_create_folder(context: DMSTestContext, dms_client: DMSClient, name: str):
    """Create a folder."""
    try:
        unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
        folder = dms_client.create_folder(
            context.repo_id,
            context.root_folder_id,
            unique_name,
        )
        context.folder = folder
        context.cleanup_objects.append((context.repo_id, folder.object_id))
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when(parsers.parse('I create a folder named "{name}" with description "{desc}"'))
def create_folder_with_desc(
    context: DMSTestContext, dms_client: DMSClient, name: str, desc: str
):
    """Create a folder with a description."""
    try:
        unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
        folder = dms_client.create_folder(
            context.repo_id,
            context.root_folder_id,
            unique_name,
            description=desc,
        )
        context.folder = folder
        context.cleanup_objects.append((context.repo_id, folder.object_id))
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== DOCUMENT: WHEN ====================


@when(parsers.parse('I upload a document named "{name}" with mime type "{mime_type}"'))
def upload_document(
    context: DMSTestContext, dms_client: DMSClient, name: str, mime_type: str
):
    """Upload a document with specified mime type."""
    try:
        unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
        doc = dms_client.create_document(
            context.repo_id,
            context.root_folder_id,
            unique_name,
            io.BytesIO(context.content_bytes),  # ty: ignore[invalid-argument-type]
            mime_type=mime_type,
        )
        context.document = doc
        context.cleanup_objects.append((context.repo_id, doc.object_id))
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when(parsers.parse('I upload a document named "{name}" without specifying mime type'))
def upload_document_no_mime(context: DMSTestContext, dms_client: DMSClient, name: str):
    """Upload a document without explicit mime type."""
    try:
        unique_name = f"{uuid.uuid4().hex[:8]}-{name}"
        doc = dms_client.create_document(
            context.repo_id,
            context.root_folder_id,
            unique_name,
            io.BytesIO(context.content_bytes),  # ty: ignore[invalid-argument-type]
        )
        context.document = doc
        context.cleanup_objects.append((context.repo_id, doc.object_id))
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== READ: WHEN ====================


@when("I get the object by its ID")
def get_object_by_id(context: DMSTestContext, dms_client: DMSClient):
    """Get an object by its ID (document context)."""
    try:
        context.retrieved_object = dms_client.get_object(
            context.repo_id,
            context.document.object_id,  # ty: ignore[unresolved-attribute]
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I get the folder object by its ID")
def get_folder_by_id(context: DMSTestContext, dms_client: DMSClient):
    """Get a folder by its ID."""
    try:
        context.retrieved_object = dms_client.get_object(
            context.repo_id,
            context.folder.object_id,  # ty: ignore[unresolved-attribute]
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I get the object by its ID with ACL included")
def get_object_with_acl(context: DMSTestContext, dms_client: DMSClient):
    """Get an object with ACL data included."""
    try:
        context.retrieved_object = dms_client.get_object(
            context.repo_id,
            context.document.object_id,  # ty: ignore[unresolved-attribute]
            include_acl=True,
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I download the document content")
def download_content(context: DMSTestContext, dms_client: DMSClient):
    """Download the content of a document."""
    try:
        context.content_response = dms_client.get_content(
            context.repo_id,
            context.document.object_id,  # ty: ignore[unresolved-attribute]
            download="attachment",
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I list children of the folder")
def list_children(context: DMSTestContext, dms_client: DMSClient):
    """List children of the created folder."""
    try:
        context.children_page = dms_client.get_children(
            context.repo_id,
            context.folder.object_id,  # ty: ignore[unresolved-attribute]
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when(parsers.parse("I list children of the root folder with max items {max_items:d}"))
def list_children_paginated(
    context: DMSTestContext, dms_client: DMSClient, max_items: int
):
    """List children with pagination."""
    try:
        opts = ChildrenOptions(max_items=max_items)
        context.children_page = dms_client.get_children(
            context.repo_id, context.root_folder_id, options=opts
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== UPDATE: WHEN ====================


@when(parsers.parse('I update the object name to "{new_name}"'))
def update_object_name(context: DMSTestContext, dms_client: DMSClient, new_name: str):
    """Update the name of a document."""
    try:
        unique_name = f"{uuid.uuid4().hex[:8]}-{new_name}"
        context.updated_object = dms_client.update_properties(
            context.repo_id,
            context.document.object_id,  # ty: ignore[unresolved-attribute]
            {"cmis:name": unique_name},
        )
        context._expected_updated_name = unique_name
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== VERSIONING: WHEN ====================


@when("I check out the document")
def check_out_document(context: DMSTestContext, dms_client: DMSClient):
    """Check out a document."""
    try:
        context.pwc = dms_client.check_out(
            context.repo_id,
            context.document.object_id,  # ty: ignore[unresolved-attribute]
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when("I cancel the check out")
def cancel_check_out(context: DMSTestContext, dms_client: DMSClient):
    """Cancel a check out."""
    try:
        dms_client.cancel_check_out(
            context.repo_id,
            context.pwc.object_id,  # ty: ignore[unresolved-attribute]
        )
        context.pwc = None
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


@when(parsers.parse('I check in with content "{content}" and comment "{comment}"'))
def check_in_document(
    context: DMSTestContext, dms_client: DMSClient, content: str, comment: str
):
    """Check in the PWC with new content."""
    try:
        context.checked_in_doc = dms_client.check_in(
            context.repo_id,
            context.pwc.object_id,  # ty: ignore[unresolved-attribute]
            major=True,
            file=io.BytesIO(content.encode("utf-8")),
            file_name=context.document.name,  # ty: ignore[unresolved-attribute]
            mime_type="text/plain",
            checkin_comment=comment,
        )
        context.pwc = None
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== ACL: WHEN ====================


@when("I get the ACL for the document")
def get_acl(context: DMSTestContext, dms_client: DMSClient):
    """Get ACL for a document."""
    try:
        context.acl = dms_client.apply_acl(
            context.repo_id,
            context.document.object_id,  # ty: ignore[unresolved-attribute]
        )
        context.operation_success = True
    except Exception as e:
        context.operation_error = e


# ==================== ERROR: WHEN ====================


@when("I attempt to get a non-existent object")
def get_nonexistent_object(context: DMSTestContext, dms_client: DMSClient):
    """Try to get an object that does not exist."""
    try:
        dms_client.get_object(context.repo_id, "nonexistent-object-id-12345")
        context.operation_success = True
    except DMSObjectNotFoundException as e:
        context.operation_error = e
    except DMSError as e:
        context.operation_error = e


@when("I attempt to download a non-existent document")
def download_nonexistent(context: DMSTestContext, dms_client: DMSClient):
    """Try to download content of a non-existent document."""
    try:
        resp = dms_client.get_content(context.repo_id, "nonexistent-doc-id-12345")
        resp.close()
        context.operation_success = True
    except DMSObjectNotFoundException as e:
        context.operation_error = e
    except DMSError as e:
        context.operation_error = e


# ==================== REPOSITORY: THEN ====================


@then("the repository list should be retrieved successfully")
def repo_list_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.operation_success is True


@then(parsers.parse("the list should contain at least {count:d} repository"))
def repo_list_count(context: DMSTestContext, count: int):
    assert len(context.repos) >= count


@then("the repository details should be retrieved successfully")
def repo_details_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.repo is not None


@then("the repository should have a CMIS repository ID")
def repo_has_cmis_id(context: DMSTestContext):
    assert context.repo.cmis_repository_id  # ty: ignore[unresolved-attribute]


@then("the repository should have a name")
def repo_has_name(context: DMSTestContext):
    assert context.repo.name  # ty: ignore[unresolved-attribute]


# ==================== CONFIG: THEN ====================


@then("the configuration creation should be successful")
def config_created(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.config is not None


@then("the configuration should have the expected name and value")
def config_values_match(context: DMSTestContext):
    assert context.config.config_name == context._config_request.config_name  # ty: ignore[unresolved-attribute]
    assert str(context.config.config_value) == str(context._config_request.config_value)  # ty: ignore[unresolved-attribute]


@then("the configuration deletion should be successful")
def config_deleted(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.operation_success is True


@then("the configuration list should be retrieved successfully")
def config_list_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert isinstance(context.configs, list)


# ==================== FOLDER: THEN ====================


@then("the folder creation should be successful")
def folder_created(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.folder is not None
    assert isinstance(context.folder, Folder)


@then("the created folder should have the correct name")
def folder_name_correct(context: DMSTestContext):
    assert context.folder.name  # ty: ignore[unresolved-attribute]
    # Name starts with UUID prefix, just verify it's set
    assert len(context.folder.name) > 0  # ty: ignore[unresolved-attribute]


# ==================== DOCUMENT: THEN ====================


@then("the document upload should be successful")
def doc_uploaded(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.document is not None
    assert isinstance(context.document, Document)


@then("the uploaded document should have the correct name")
def doc_name_correct(context: DMSTestContext):
    assert context.document.name  # ty: ignore[unresolved-attribute]
    assert len(context.document.name) > 0  # ty: ignore[unresolved-attribute]


@then(parsers.parse('the document should have mime type "{expected_mime}"'))
def doc_mime_type(context: DMSTestContext, expected_mime: str):
    assert context.document.content_stream_mime_type == expected_mime  # ty: ignore[unresolved-attribute]


@then("the document should have a mime type assigned by the server")
def doc_has_any_mime_type(context: DMSTestContext):
    assert context.document.content_stream_mime_type is not None  # ty: ignore[unresolved-attribute]


# ==================== READ: THEN ====================


@then("the object should be retrieved successfully")
def object_retrieved(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.retrieved_object is not None


@then("the object should be a Document")
def object_is_document(context: DMSTestContext):
    assert isinstance(context.retrieved_object, Document)


@then("the object should be a Folder")
def object_is_folder(context: DMSTestContext):
    assert isinstance(context.retrieved_object, Folder)


@then(parsers.parse('the object name should be "{expected_name}"'))
def object_name_matches(context: DMSTestContext, expected_name: str):
    # Name has UUID prefix, so check suffix
    assert context.retrieved_object.name.endswith(expected_name)  # ty: ignore[unresolved-attribute]


@then("the download should be successful")
def download_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.content_response is not None


@then(parsers.parse('the downloaded content should match "{expected}"'))
def download_content_match(context: DMSTestContext, expected: str):
    actual = context.content_response.content.decode("utf-8")  # ty: ignore[unresolved-attribute]
    assert actual == expected


@then("the children list should be retrieved successfully")
def children_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.children_page is not None
    assert isinstance(context.children_page, ChildrenPage)


@then(parsers.parse("the children should contain at least {count:d} item"))
def children_count(context: DMSTestContext, count: int):
    assert len(context.children_page.objects) >= count  # ty: ignore[unresolved-attribute]


# ==================== UPDATE: THEN ====================


@then("the update should be successful")
def update_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.updated_object is not None


@then(parsers.parse('the updated object name should be "{expected_name}"'))
def updated_name_matches(context: DMSTestContext, expected_name: str):
    # Actual name has UUID prefix
    assert context.updated_object.name == context._expected_updated_name  # ty: ignore[unresolved-attribute]


# ==================== VERSIONING: THEN ====================


@then("the check out should be successful")
def checkout_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.pwc is not None


@then("the PWC should be a private working copy")
def pwc_is_private(context: DMSTestContext):
    assert context.pwc.is_private_working_copy is True  # ty: ignore[unresolved-attribute]


@then("the cancel check out should be successful")
def cancel_checkout_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.pwc is None


@then("the check in should be successful")
def checkin_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.checked_in_doc is not None


@then("the new version label should not be empty")
def version_label_set(context: DMSTestContext):
    assert context.checked_in_doc.version_label  # ty: ignore[unresolved-attribute]


# ==================== ACL: THEN ====================


@then("the ACL should be retrieved successfully")
def acl_success(context: DMSTestContext):
    assert context.operation_error is None, f"Failed: {context.operation_error}"
    assert context.acl is not None
    assert isinstance(context.acl, Acl)


# ==================== ERROR: THEN ====================


@then("the operation should fail with a not found error")
def not_found_error(context: DMSTestContext):
    assert context.operation_error is not None, "Expected an error but none occurred"
    assert isinstance(context.operation_error, (DMSObjectNotFoundException, DMSError))


# ==================== CLEANUP STEPS ====================


@then("I clean up the created folder")
def cleanup_folder(context: DMSTestContext, dms_client: DMSClient):
    """Delete the folder created during the test."""
    if context.folder:
        try:
            _delete_cmis_object(dms_client, context.repo_id, context.folder.object_id)
            _remove_from_cleanup(context, context.folder.object_id)
        except Exception as e:
            logger.warning(
                "Cleanup failed for folder %s: %s", context.folder.object_id, e
            )


@then("I clean up the created document")
def cleanup_document(context: DMSTestContext, dms_client: DMSClient):
    """Delete the document created during the test."""
    if context.document:
        try:
            _delete_cmis_object(dms_client, context.repo_id, context.document.object_id)
            _remove_from_cleanup(context, context.document.object_id)
        except Exception as e:
            logger.warning(
                "Cleanup failed for document %s: %s", context.document.object_id, e
            )


@then("I clean up the updated document")
def cleanup_updated_document(context: DMSTestContext, dms_client: DMSClient):
    """Delete the updated document."""
    obj_id = (
        context.updated_object.object_id
        if context.updated_object
        else (context.document.object_id if context.document else None)
    )
    if obj_id:
        try:
            _delete_cmis_object(dms_client, context.repo_id, obj_id)
            _remove_from_cleanup(context, obj_id)
        except Exception as e:
            logger.warning("Cleanup failed for document %s: %s", obj_id, e)


@then("I clean up the children folder")
def cleanup_children_folder(context: DMSTestContext, dms_client: DMSClient):
    """Delete the folder and its children."""
    # Delete child document first
    if context.child_doc_id:
        try:
            _delete_cmis_object(dms_client, context.repo_id, context.child_doc_id)
        except Exception as e:
            logger.warning(
                "Cleanup failed for child doc %s: %s", context.child_doc_id, e
            )
    # Then delete the parent folder
    if context.folder:
        try:
            _delete_cmis_object(dms_client, context.repo_id, context.folder.object_id)
            _remove_from_cleanup(context, context.folder.object_id)
        except Exception as e:
            logger.warning(
                "Cleanup failed for folder %s: %s", context.folder.object_id, e
            )


# ==================== HELPERS ====================


def _delete_cmis_object(client: DMSClient, repo_id: str, object_id: str):
    """Delete a CMIS object using the update properties endpoint (CMIS delete action)."""
    # Use the HTTP invoker directly to perform a CMIS delete
    form_data = {
        "cmisaction": "delete",
        "objectId": object_id,
        "_charset_": "UTF-8",
    }
    client._http.post_form(
        client._browser_url(repo_id),
        data=form_data,
    )


def _remove_from_cleanup(context: DMSTestContext, object_id: str):
    """Remove an object from the cleanup list after successful deletion."""
    context.cleanup_objects = [
        (r, o) for r, o in context.cleanup_objects if o != object_id
    ]
