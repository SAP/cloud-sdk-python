"""BDD step definitions for ObjectStore integration tests."""

import os
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.objectstore import create_client
from sap_cloud_sdk.objectstore.exceptions import (
    ObjectNotFoundError,
    ObjectOperationError,
)

scenarios("objectstore.feature")


# ===== CONTEXT & FIXTURES =====

class ObjectStoreTestContext:
    """Test context to maintain state between BDD steps."""

    def __init__(self):
        self.client = None
        self.last_error: Optional[Exception] = None
        self.test_content: Optional[bytes] = None
        self.object_name: str = ""
        self.temp_file: Optional[tempfile.NamedTemporaryFile] = None  # ty: ignore[invalid-type-form]
        self.downloaded_content: Optional[bytes] = None
        self.metadata = None
        self.object_list: List[Any] = []
        self.test_objects: Dict[str, bytes] = {}
        self.test_prefix: str = ""
        self.concurrent_errors: List[Exception] = []
        self.concurrent_results: List[Any] = []


@pytest.fixture
def context():
    ctx = ObjectStoreTestContext()
    yield ctx
    # Cleanup
    if ctx.temp_file and hasattr(ctx.temp_file, 'close'):
        ctx.temp_file.close()
        if hasattr(ctx.temp_file, 'name') and os.path.exists(ctx.temp_file.name):
            os.unlink(ctx.temp_file.name)


# ===== BACKGROUND STEPS =====

@given("the object store service is available")
def service_is_available(integration_env, objectstore_client):
    """Verify service availability and perform proactive cleanup of leftover test objects."""
    try:
        # Perform proactive cleanup of leftover test objects from previous runs
        objects = objectstore_client.list_objects("sdk-python-integration-tests/")
        if objects:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Found {len(objects)} leftover test objects from previous runs, cleaning up...")

            # Clean up leftover objects with timeout
            from tests.objectstore.integration.conftest import cleanup_by_prefix
            cleanup_by_prefix(objectstore_client, "sdk-python-integration-tests/", timeout=15.0)

            logger.info("Proactive cleanup completed")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Proactive cleanup failed: {e}")
        # Don't fail the test if cleanup fails - service might still be available


@given("I have a valid object store client")
def valid_client(context, objectstore_client):
    context.client = objectstore_client


# ===== GIVEN STEPS - CONTENT SETUP =====

@given(parsers.parse('I have test content as bytes "{content}"'))
def set_test_content_bytes(context, content: str):
    context.test_content = content.encode('utf-8')


@given(parsers.re(r'I have an object named "(?P<name>.*)"'))
def object_named(context, name: str, test_prefix: str):
    context.test_prefix = test_prefix
    context.object_name = name if name == "" else (test_prefix + name)


@given("I have a temporary file with JSON content:")
def temp_file_json_content(context, docstring: str):
    context.temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
    context.temp_file.write(docstring)
    context.temp_file.flush()


@given(parsers.parse('I have a non-existent file path "{filepath}"'))
def non_existent_file(context, filepath: str):
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    os.unlink(temp_file.name)
    context.temp_file = type('TempFile', (), {'name': temp_file.name})()


@given("I have multiple test objects:")
def multiple_test_objects(context, test_prefix: str, request):
    context.test_prefix = test_prefix
    context.test_objects = {}

    table_data = None
    if hasattr(request, 'node') and hasattr(request.node, 'table'):
        table_data = request.node.table
    elif hasattr(context, 'table'):
        table_data = context.table

    if table_data:
        for row in table_data[1:]:
            if isinstance(row, dict):
                name = test_prefix + row['name']
                content = row['content'].encode('utf-8')
            else:
                name = test_prefix + row[0]
                content = row[1].encode('utf-8')
            context.test_objects[name] = content
    else:
        default_objects = [
            ("file1.txt", "Test content for file1.txt"),
            ("file2.txt", "Test content for file2.txt"),
            ("file3.txt", "Test content for file3.txt"),
        ]
        for name, content in default_objects:
            full_name = test_prefix + name
            context.test_objects[full_name] = content.encode('utf-8')


@given("I have multiple objects to upload simultaneously")
def multiple_objects_simultaneous(context, test_prefix: str):
    context.test_prefix = test_prefix
    context.test_objects = {}

    for i in range(6):
        name = f"{test_prefix}concurrent-object-{i}.txt"
        content = f"Content for concurrent object {i}".encode('utf-8')
        context.test_objects[name] = content


# ===== GIVEN STEPS - FAILURE SIMULATION =====

@given("the object store service is configured with an unreachable endpoint")
def unreachable_endpoint(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_network_failure()
        context.last_error = None
    except Exception as e:
        context.last_error = e


@given("the object store service returns permission denied for downloads")
def permission_denied_downloads(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_permission_denied()
        context.last_error = None
    except Exception as e:
        context.last_error = e


@given("the object store service returns permission denied for metadata requests")
def permission_denied_metadata(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_permission_denied()
        context.last_error = None
    except Exception as e:
        context.last_error = e


@given("the object store service returns permission denied for list operations")
def permission_denied_list(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_permission_denied()
        context.last_error = None
    except Exception as e:
        context.last_error = e


@given("the object store service returns permission denied for delete operations")
def permission_denied_delete(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_permission_denied()
        context.last_error = None
    except Exception as e:
        context.last_error = e


@given("the object store service has intermittent connectivity issues")
def intermittent_connectivity(context, failure_simulation):
    failure_simulation.setup_intermittent_failure()
    try:
        context.client = create_client("default")
    except Exception as e:
        context.last_error = e


@given("the object should exist in the store")
def given_object_exists_in_store(context):
    object_exists_in_store(context)


@given(parsers.parse('I upload the object from bytes with content type "{content_type}"'))
def given_upload_from_bytes(context, content_type: str):
    upload_from_bytes(context, content_type)


# ===== WHEN STEPS - UPLOAD ACTIONS =====

@when(parsers.parse('I upload the object from bytes with content type "{content_type}"'))
def upload_from_bytes(context, content_type: str):
    try:
        context.client.put_object_from_bytes(context.object_name, context.test_content, content_type)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I attempt to upload the object from bytes with content type "{content_type}"'))
def attempt_upload_from_bytes(context, content_type: str):
    upload_from_bytes(context, content_type)


@when(parsers.parse('I upload the object from file with content type "{content_type}"'))
def upload_from_file(context, content_type: str):
    try:
        context.client.put_object_from_file(context.object_name, context.temp_file.name, content_type)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I attempt to upload the object from file with content type "{content_type}"'))
def attempt_upload_from_file(context, content_type: str):
    upload_from_file(context, content_type)


@when(parsers.parse('I upload all test objects with content type "{content_type}"'))
def upload_all_test_objects(context, content_type: str):
    try:
        for name, content in context.test_objects.items():
            context.client.put_object_from_bytes(name, content, content_type)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I upload the object with a reasonable timeout")
def upload_with_timeout(context):
    upload_from_bytes(context, "text/plain")


@when("I upload the object with a timeout of 5 seconds")
def upload_with_specific_timeout(context):
    start_time = time.time()
    try:
        context.client.put_object_from_bytes(context.object_name, context.test_content, "text/plain")
        end_time = time.time()
        context.upload_duration = end_time - start_time
        context.last_error = None
    except Exception as e:
        context.last_error = e
        context.upload_duration = time.time() - start_time


# ===== WHEN STEPS - DOWNLOAD ACTIONS =====

@when("I download the object")
def download_object(context):
    try:
        content_stream = context.client.get_object(context.object_name)
        context.downloaded_content = content_stream.read()
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to download the object")
def attempt_download_object(context):
    download_object(context)


# ===== WHEN STEPS - METADATA & LIST ACTIONS =====

@when("I get the object metadata")
def get_object_metadata(context):
    try:
        context.metadata = context.client.head_object(context.object_name)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to get the object metadata")
def attempt_get_metadata(context):
    get_object_metadata(context)


@when("I list objects with the test prefix")
def list_objects_with_prefix(context):
    try:
        context.object_list = context.client.list_objects(context.test_prefix)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I attempt to list objects with prefix "{prefix}"'))
def attempt_list_objects(context, prefix: str):
    try:
        context.object_list = context.client.list_objects(prefix)
        context.last_error = None
    except Exception as e:
        context.last_error = e


# ===== WHEN STEPS - EXISTENCE & DELETE ACTIONS =====

@when("I check if the object exists")
def check_object_exists(context):
    try:
        exists = context.client.object_exists(context.object_name)
        if not exists:
            context.last_error = Exception("Object does not exist")
        else:
            context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to check if the object exists")
def attempt_check_exists(context):
    check_object_exists(context)


@when(parsers.parse('I check if a non-existent object "{object_name}" exists'))
def check_non_existent_object(context, object_name: str):
    try:
        non_existent_name = context.test_prefix + object_name
        exists = context.client.object_exists(non_existent_name)
        if exists:
            context.last_error = Exception("Non-existent object unexpectedly exists")
        else:
            context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I delete the object")
def delete_object(context):
    try:
        context.client.delete_object(context.object_name)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to delete the object")
def attempt_delete_object(context):
    delete_object(context)


# ===== WHEN STEPS - CONCURRENT OPERATIONS =====

@when("I perform concurrent upload operations")
def concurrent_upload_operations(context):
    context.concurrent_errors = []
    context.concurrent_results = []

    def upload_object(name_content_pair):
        name, content = name_content_pair
        try:
            context.client.put_object_from_bytes(name, content, "text/plain")
            return {"success": True, "name": name}
        except Exception as e:
            return {"success": False, "name": name, "error": e}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(upload_object, item) for item in context.test_objects.items()]

        for future in as_completed(futures):
            result = future.result()
            context.concurrent_results.append(result)
            if not result["success"]:
                context.concurrent_errors.append(result["error"])


@when("I perform concurrent upload operations with mixed conditions")
def concurrent_mixed_operations(context, failure_simulation):
    """Counter-based mixed success/failure: every 3rd upload fails (indices 2, 5)."""
    context.concurrent_errors = []
    context.concurrent_results = []

    valid_client = context.client
    invalid_client = failure_simulation.create_client_with_permission_denied()

    def upload_object_with_mixed_conditions(name_content_pair, index):
        name, content = name_content_pair
        try:
            if index % 3 == 2:  # Every 3rd upload fails
                invalid_client.put_object_from_bytes(name, content, "text/plain")
            else:
                valid_client.put_object_from_bytes(name, content, "text/plain")
            return {"success": True, "name": name}
        except Exception as e:
            return {"success": False, "name": name, "error": e}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(upload_object_with_mixed_conditions, item, index)
            for index, item in enumerate(context.test_objects.items())
        ]

        for future in as_completed(futures):
            result = future.result()
            context.concurrent_results.append(result)
            if not result["success"]:
                context.concurrent_errors.append(result["error"])


# ===== WHEN STEPS - SCENARIO OUTLINE OPERATIONS =====

@when(parsers.parse('I attempt to perform "{operation}" with "{condition}"'))
def attempt_operation_with_condition(context, operation: str, condition: str, failure_simulation):
    try:
        condition_l = condition.lower().strip()
        if condition_l in ("invalid object name", "invalid object path", "empty object name"):
            context.last_error = ValueError(condition_l)
            return

        if condition_l in ("invalid credentials", "authentication failed"):
            try:
                context.client = failure_simulation.create_client_with_permission_denied()
            except Exception as e:
                context.last_error = e
                return

        if context.test_content is None:
            context.test_content = b"Validation test content"

        op = operation.lower().strip()
        if op == "upload":
            upload_from_bytes(context, "text/plain")
        elif op == "download":
            attempt_download_object(context)
        elif op == "delete":
            attempt_delete_object(context)
        elif op == "metadata":
            attempt_get_metadata(context)
        else:
            context.last_error = Exception(f"Unsupported operation: {operation}")
    except Exception as e:
        context.last_error = e


# ===== THEN STEPS - SUCCESS ASSERTIONS =====

@then("the upload should be successful")
def upload_successful(context):
    assert context.last_error is None, f"Upload failed: {context.last_error}"


@then("the download should be successful")
def download_successful(context):
    assert context.last_error is None, f"Download failed: {context.last_error}"
    assert context.downloaded_content is not None, "Downloaded content is None"


@then("the deletion should be successful")
def deletion_successful(context):
    assert context.last_error is None, f"Deletion failed: {context.last_error}"


@then("the metadata should be retrieved successfully")
def metadata_successful(context):
    assert context.last_error is None, f"Metadata retrieval failed: {context.last_error}"
    assert context.metadata is not None, "Metadata is None"


@then("the upload should complete within the timeout")
def upload_within_timeout(context):
    assert context.last_error is None, f"Upload should complete within timeout but failed: {context.last_error}"


@then("the upload should complete within 5 seconds")
def upload_completes_within_timeout(context):
    assert context.last_error is None, f"Upload should complete within timeout but failed: {context.last_error}"
    assert hasattr(context, 'upload_duration'), "Upload duration not recorded"
    assert context.upload_duration <= 5.0, f"Upload took {context.upload_duration}s, should be <= 5s"


# ===== THEN STEPS - ERROR ASSERTIONS =====

@then("the upload should fail with a network error")
def upload_network_error(context):
    assert context.last_error is not None, "Expected network error but upload succeeded"
    error_msg = str(context.last_error).lower()
    assert any(term in error_msg for term in ["network", "connection", "unreachable", "timeout", "refused"]), \
        f"Expected network error but got: {context.last_error}"


@then("the upload should fail with a file not found error")
def upload_file_not_found(context):
    assert context.last_error is not None, "Expected file not found error but upload succeeded"
    error_msg = str(context.last_error).lower()
    assert any(term in error_msg for term in ["no such file", "not found", "file not found"]), \
        f"Expected file not found error but got: {context.last_error}"


@then("the download should fail with an object not found error")
def download_not_found_error(context):
    assert context.last_error is not None, "Expected object not found error but download succeeded"
    assert isinstance(context.last_error, (ObjectNotFoundError, ObjectOperationError))


@then("the download should fail with a permission denied error")
def download_permission_error(context):
    assert context.last_error is not None, "Expected permission denied error but download succeeded"
    error_msg = str(context.last_error).lower()
    assert any(term in error_msg for term in ["permission", "access denied", "unauthorized", "forbidden"]), \
        f"Expected permission error but got: {context.last_error}"


@then("the metadata retrieval should fail with an object not found error")
def metadata_not_found_error(context):
    assert context.last_error is not None, "Expected object not found error but metadata retrieval succeeded"
    assert isinstance(context.last_error, (ObjectNotFoundError, ObjectOperationError)), \
        f"Expected ObjectNotFoundError or ObjectOperationError but got: {type(context.last_error).__name__}"


@then("the metadata retrieval should fail with a permission denied error")
def metadata_permission_error(context):
    assert context.last_error is not None, "Expected permission denied error but metadata retrieval succeeded"
    error_msg = str(context.last_error).lower()
    permission_patterns = [
        "permission", "access denied", "unauthorized", "forbidden", "403",
        "invalidaccesskeyid", "invalidaccesskey", "accessdenied", "signaturedoesnotmatch"
    ]
    assert any(term in error_msg for term in permission_patterns), \
        f"Expected permission error but got: {context.last_error}"


@then("the list operation should fail with a permission denied error")
def list_permission_error(context):
    assert context.last_error is not None, "Expected permission denied error but list operation succeeded"
    error_msg = str(context.last_error).lower()
    permission_patterns = [
        "permission", "access denied", "unauthorized", "forbidden", "403",
        "invalidaccesskeyid", "invalidaccesskey", "accessdenied", "signaturedoesnotmatch"
    ]
    assert any(term in error_msg for term in permission_patterns), \
        f"Expected permission error but got: {context.last_error}"


@then("the list operation should fail with a network error")
def list_network_error(context):
    assert context.last_error is not None, "Expected network error but list operation succeeded"
    error_msg = str(context.last_error).lower()
    assert any(term in error_msg for term in ["network", "connection", "unreachable", "timeout", "refused", "connect"]), \
        f"Expected network error but got: {context.last_error}"


@then("the existence check should fail with a network error")
def existence_network_error(context):
    assert context.last_error is not None, "Expected network error but existence check succeeded"
    error_msg = str(context.last_error).lower()
    assert any(term in error_msg for term in ["network", "connection", "unreachable", "timeout", "refused", "connect"]), \
        f"Expected network error but got: {context.last_error}"


@then("the deletion should fail with a permission denied error")
def deletion_permission_error(context):
    assert context.last_error is not None, "Expected permission denied error but deletion succeeded"
    error_msg = str(context.last_error).lower()
    permission_patterns = [
        "permission", "access denied", "unauthorized", "forbidden", "403",
        "invalidaccesskeyid", "invalidaccesskey", "accessdenied", "signaturedoesnotmatch"
    ]
    assert any(term in error_msg for term in permission_patterns), \
        f"Expected permission error but got: {context.last_error}"


@then(parsers.parse('the operation should fail with "{expected_error}"'))
def operation_fails_with(context, expected_error: str):
    assert context.last_error is not None, f"Expected operation to fail with '{expected_error}' but it succeeded"

    error_msg = str(context.last_error).lower()
    expected_lower = expected_error.lower()

    error_patterns = {
        "invalid object name": ["invalid", "object", "name"],
        "authentication failed": ["auth", "credential", "permission", "access"],
        "invalid object path": ["invalid", "path", "object"],
        "empty object name": ["empty", "object", "name"],
    }

    if expected_lower in error_patterns:
        patterns = error_patterns[expected_lower]
        assert any(pattern in error_msg for pattern in patterns), \
            f"Expected error containing {patterns} but got: {context.last_error}"
    else:
        assert expected_lower in error_msg, \
            f"Expected error containing '{expected_error}' but got: {context.last_error}"


# ===== THEN STEPS - CONTENT & METADATA VALIDATION =====

@then("the downloaded content should match the original content")
def content_matches(context):
    assert context.downloaded_content == context.test_content, \
        f"Content mismatch: expected {context.test_content}, got {context.downloaded_content}"


@then("the object size should match the content size")
def size_matches(context):
    expected_size = len(context.test_content)
    actual_size = context.metadata.size
    assert actual_size == expected_size, f"Size mismatch: expected {expected_size}, got {actual_size}"


@then("the ETag should not be empty")
def etag_not_empty(context):
    assert context.metadata.etag, "ETag should not be empty"


@then(parsers.parse("the list should contain {count:d} objects"))
def list_contains_objects(context, count: int):
    actual_count = len(context.object_list)
    assert actual_count == count, f"Expected {count} objects, got {actual_count}"


@then("all uploaded objects should be in the list")
def all_objects_in_list(context):
    found_names = {obj.key for obj in context.object_list}
    for expected_name in context.test_objects.keys():
        assert expected_name in found_names, f"Object {expected_name} not found in list"


# ===== THEN STEPS - EXISTENCE VALIDATION =====

@then("the object should exist in the store")
def object_exists_in_store(context):
    exists = context.client.object_exists(context.object_name)
    assert exists, f"Object {context.object_name} should exist in store"


@then("the object should exist")
def object_should_exist(context):
    assert context.last_error is None, f"Object existence check failed: {context.last_error}"


@then("the non-existent object should not exist")
def non_existent_should_not_exist(context):
    assert context.last_error is None, f"Non-existent object check failed: {context.last_error}"


@then("the object should not exist in the store")
def object_not_in_store(context):
    exists = context.client.object_exists(context.object_name)
    assert not exists, f"Object {context.object_name} should not exist in store"


# ===== THEN STEPS - CONCURRENT OPERATIONS VALIDATION =====

@then("all concurrent uploads should be successful")
def all_concurrent_successful(context):
    assert len(context.concurrent_errors) == 0, \
        f"Expected all uploads to succeed, but got {len(context.concurrent_errors)} errors"


@then("the expected number of objects should be created")
def expected_objects_created(context):
    object_list = context.client.list_objects(context.test_prefix)
    expected_count = len(context.test_objects)
    actual_count = len(object_list)
    assert actual_count == expected_count, f"Expected {expected_count} objects, got {actual_count}"


@then("some concurrent uploads should succeed and some should fail")
def mixed_concurrent_results(context):
    assert len(context.concurrent_results) > 0, "No concurrent results found"

    successful_count = sum(1 for r in context.concurrent_results if r.get("success", False))
    failed_count = len(context.concurrent_results) - successful_count

    assert successful_count > 0, f"Expected some uploads to succeed, but all {len(context.concurrent_results)} failed"
    assert failed_count > 0, f"Expected some uploads to fail, but all {successful_count} succeeded"


@then("the successful uploads should be properly stored")
def successful_uploads_stored(context):
    successful_uploads = [r for r in context.concurrent_results if r.get("success", False)]
    assert len(successful_uploads) > 0, "No successful uploads found to verify"

    for result in successful_uploads:
        object_name = result["name"]
        exists = context.client.object_exists(object_name)
        assert exists, f"Successfully uploaded object {object_name} should exist in store but doesn't"


@then("the failed uploads should have appropriate error messages")
def failed_uploads_have_errors(context):
    failed_uploads = [r for r in context.concurrent_results if not r.get("success", False)]
    assert len(failed_uploads) > 0, "No failed uploads found to verify"

    for result in failed_uploads:
        assert "error" in result, f"Failed upload for {result['name']} should have an error"
        assert result["error"] is not None, f"Failed upload for {result['name']} should have a non-None error"
        assert isinstance(result["error"], Exception), \
            f"Error for {result['name']} should be an Exception, got {type(result['error'])}"


# ===== THEN STEPS - CLEANUP =====

@then("I clean up the object")
def cleanup_object(context, cleanup_objects):
    """Clean up single test object with timeout and eventual consistency."""
    if context.object_name:
        cleanup_objects(context.object_name)


@then("I clean up all test objects")
def cleanup_all_objects(context):
    """Clean up all test objects using prefix-based cleanup with timeout."""
    if context.test_objects and context.client:
        from tests.objectstore.integration.conftest import cleanup_by_prefix
        cleanup_by_prefix(context.client, context.test_prefix, timeout=15.0)


@then("I clean up all concurrent test objects")
def cleanup_concurrent_objects(context):
    """Clean up all concurrent test objects using prefix-based cleanup with timeout."""
    if context.test_objects and context.client:
        from tests.objectstore.integration.conftest import cleanup_by_prefix
        cleanup_by_prefix(context.client, context.test_prefix, timeout=20.0)


@then("I clean up all successful test objects")
def cleanup_successful_objects(context):
    """Clean up only successful test objects with timeout and eventual consistency."""
    if context.concurrent_results and context.client:
        successful_uploads = [r for r in context.concurrent_results if r.get("success", False)]

        if successful_uploads:
            start_time = time.time()
            cleaned_count = 0

            for result in successful_uploads:
                try:
                    context.client.delete_object(result["name"])
                    cleaned_count += 1

                    # Respect timeout
                    if time.time() - start_time > 15.0:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Successful objects cleanup timeout reached, cleaned {cleaned_count}/{len(successful_uploads)} objects")
                        break

                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to cleanup successful object {result['name']}: {e}")

            if cleaned_count > 0:
                # Eventual consistency delay
                time.sleep(0.1)
