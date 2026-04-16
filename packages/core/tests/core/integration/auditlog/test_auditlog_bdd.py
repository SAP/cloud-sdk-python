"""BDD step definitions for AuditLog integration tests."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.auditlog import (
    create_client,
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
    Tenant,
    SecurityEventAttribute,
    DataAccessAttribute,
    ChangeAttribute,
    DeletedAttribute
)
from sap_cloud_sdk.auditlog.exceptions import (
    ClientCreationError,
    TransportError,
    AuthenticationError
)

scenarios("auditlog.feature")


# ===== CONTEXT & FIXTURES =====

class AuditLogTestContext:
    def __init__(self):
        self.client = None
        self.last_error: Optional[Exception] = None
        self.current_event = None
        self.user: str = "$USER"
        self.tenant: Tenant = Tenant.PROVIDER
        self.attributes: List[Any] = []
        self.data_object: Dict[str, str] = {}
        self.data_subject: Dict[str, str] = {}
        self.config_id: Optional[str] = None
        self.ip_address: Optional[str] = None
        self.custom_details: Optional[Dict[str, Any]] = None
        self.concurrent_events: List[Any] = []
        self.concurrent_errors: List[Exception] = []
        self.concurrent_results: List[Any] = []
        self.multiple_users: List[str] = []
        self.individual_attempts: List[Dict[str, Any]] = []


@pytest.fixture
def context():
    return AuditLogTestContext()


# ===== BACKGROUND STEPS =====

@given("the audit log service is available")
def service_is_available(auditlog_client):
    assert auditlog_client is not None


@given("I have a valid audit logger")
def valid_audit_logger(context, auditlog_client):
    context.client = auditlog_client


# ===== GIVEN STEPS - USER AND TENANT SETUP =====

@given(parsers.parse('I have a user "{username}"'))
def set_user(context, username: str):
    context.user = username


@given("I have a tenant subscriber")
def set_tenant_subscriber(context):
    context.tenant = Tenant.SUBSCRIBER


@given("I have a tenant provider")
def set_tenant_provider(context):
    context.tenant = Tenant.PROVIDER


@given("I have multiple users for concurrent testing")
def setup_multiple_users(context):
    context.multiple_users = [
        "concurrent-user-1",
        "concurrent-user-2",
        "concurrent-user-3",
        "concurrent-user-4",
        "concurrent-user-5",
        "concurrent-user-6"
    ]


# ===== GIVEN STEPS - FAILURE SIMULATION =====

@given("the audit log service is configured with an unreachable endpoint")
def unreachable_endpoint(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_network_failure()
        context.last_error = None
    except Exception as e:
        context.client = None
        context.last_error = e


@given("the audit log service returns Service Unavailable")
def service_unavailable(context, failure_simulation):
    try:
        context.client = failure_simulation.create_client_with_service_unavailable()
        context.last_error = None
    except Exception as e:
        context.client = None
        context.last_error = e


@given("the audit log service has intermittent connectivity issues")
def intermittent_connectivity(context, failure_simulation):
    failure_simulation.setup_intermittent_failure()
    try:
        # Store the failure simulator for use during individual attempts
        context.failure_simulation = failure_simulation
        # Start with a working client, failures will occur per-operation
        context.client = create_client()
    except Exception as e:
        context.last_error = e


@given("the audit log service has network connectivity issues")
def network_connectivity_issues(context, failure_simulation):
    intermittent_connectivity(context, failure_simulation)


# ===== WHEN STEPS - SECURITY EVENT ACTIONS =====

@when(parsers.parse('I create a security event with message "{message}"'))
def create_security_event(context, message: str):
    try:
        context.current_event = SecurityEvent(
            data=message,
            user=context.user,
            tenant=context.tenant
        )
        if context.client is not None:
            context.last_error = None
    except Exception as e:
        context.last_error = e


@when('I create a security event with message ""')
def create_security_event_empty(context):
    try:
        context.current_event = SecurityEvent(
            data="",
            user=context.user,
            tenant=context.tenant
        )
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I add user information to the event")
def add_user_information(context):
    pass


@when("I add tenant information to the event")
def add_tenant_information(context):
    pass


@when(parsers.parse('I add IP address "{ip_address}"'))
def add_ip_address(context, ip_address: str):
    if hasattr(context.current_event, 'ip'):
        context.current_event.ip = ip_address
    context.ip_address = ip_address


@when(parsers.parse('I add attribute "{name}" with value "{value}"'))
def add_security_attribute(context, name: str, value: str):
    attr = SecurityEventAttribute(name=name, value=value)
    context.attributes.append(attr)


@when(parsers.parse('I add attribute "{name}" with boolean value {value}'))
def add_attribute_boolean(context, name: str, value: str):
    bool_value = value.lower() == "true"
    if isinstance(context.current_event, DataAccessEvent):
        attr = DataAccessAttribute(name=name, successful=bool_value)
        context.attributes.append(attr)
    else:
        add_security_attribute(context, name, str(bool_value))


@when("I log the security event")
def log_security_event(context):
    try:
        if context.attributes and hasattr(context.current_event, 'attributes'):
            context.current_event.attributes = context.attributes

        if context.ip_address and hasattr(context.current_event, 'ip'):
            context.current_event.ip = context.ip_address

        context.client.log(context.current_event)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to log the security event")
def attempt_log_security_event(context):
    log_security_event(context)


# ===== WHEN STEPS - DATA ACCESS EVENT ACTIONS =====

@when("I create a data access event")
def create_data_access_event(context):
    try:
        context.current_event = DataAccessEvent(
            user=context.user,
            tenant=context.tenant
        )
        context.attributes = []
        if context.client is not None:
            context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I add data object "{object_type}" with properties:'))
def add_data_object_with_table(context, object_type: str, datatable):
    context.data_object = {"type": object_type}

    for row in datatable:
        if len(row) >= 2:
            context.data_object[row[0]] = row[1]

    if hasattr(context.current_event, 'object_type'):
        context.current_event.object_type = object_type
        context.current_event.object_id = {k: v for k, v in context.data_object.items() if k != "type"}


@when(parsers.parse('I add data subject "{subject_type}" with properties:'))
def add_data_subject_with_table(context, subject_type: str, datatable):
    context.data_subject = {"type": subject_type}

    for row in datatable:
        if len(row) >= 2:
            context.data_subject[row[0]] = row[1]

    if hasattr(context.current_event, 'subject_type'):
        context.current_event.subject_type = subject_type
        context.current_event.subject_id = {k: v for k, v in context.data_subject.items() if k != "type"}


@when("I log the data access event")
def log_data_access_event(context):
    try:
        if context.attributes and hasattr(context.current_event, 'attributes'):
            context.current_event.attributes = context.attributes

        context.client.log(context.current_event)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to log the data access event")
def attempt_log_data_access_event(context):
    if context.client is None:
        return
    log_data_access_event(context)


# ===== WHEN STEPS - DATA MODIFICATION EVENT ACTIONS =====

@when("I create a data modification event")
def create_data_modification_event(context):
    try:
        context.current_event = DataModificationEvent(
            user=context.user,
            tenant=context.tenant
        )
        context.attributes = []
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I add attribute change from "{old_value}" to "{new_value}" for "{name}"'))
def add_attribute_change(context, old_value: str, new_value: str, name: str):
    attr = ChangeAttribute(name=name, old=old_value, new=new_value)
    context.attributes.append(attr)


@when("I log the data modification event")
def log_data_modification_event(context):
    try:
        if context.attributes and hasattr(context.current_event, 'attributes'):
            context.current_event.attributes = context.attributes

        context.client.log(context.current_event)
        context.last_error = None
    except Exception as e:
        context.last_error = e


# ===== WHEN STEPS - CONFIGURATION CHANGE EVENT ACTIONS =====

@when("I create a configuration change event")
def create_configuration_change_event(context):
    try:
        context.current_event = ConfigurationChangeEvent(
            user=context.user,
            tenant=context.tenant
        )
        context.attributes = []
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I set configuration ID "{config_id}"'))
def set_configuration_id(context, config_id: str):
    context.config_id = config_id
    if hasattr(context.current_event, 'id'):
        context.current_event.id = config_id


@when("I log the configuration change event")
def log_configuration_change_event(context):
    try:
        if context.attributes and hasattr(context.current_event, 'attributes'):
            context.current_event.attributes = context.attributes

        context.client.log(context.current_event)
        context.last_error = None
    except Exception as e:
        context.last_error = e


# ===== WHEN STEPS - DATA DELETION EVENT ACTIONS =====

@when("I create a data deletion event")
def create_data_deletion_event(context):
    try:
        context.current_event = DataDeletionEvent(
            user=context.user,
            tenant=context.tenant
        )
        context.attributes = []
        if context.client is not None:
            context.last_error = None
    except Exception as e:
        context.last_error = e


@when(parsers.parse('I delete attribute "{name}" with previous value "{old_value}"'))
def add_deleted_attribute(context, name: str, old_value: str):
    attr = DeletedAttribute(name=name, old=old_value)
    context.attributes.append(attr)


@when("I log the data deletion event")
def log_data_deletion_event(context):
    try:
        if context.attributes and hasattr(context.current_event, 'attributes'):
            context.current_event.attributes = context.attributes

        context.client.log(context.current_event)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to log the data deletion event")
def attempt_log_data_deletion_event(context):
    if context.client is None:
        return
    log_data_deletion_event(context)


# ===== WHEN STEPS - CONFIGURATION DELETION EVENT ACTIONS =====

@when("I create a configuration deletion event")
def create_configuration_deletion_event(context):
    try:
        context.current_event = ConfigurationDeletionEvent(
            user=context.user,
            tenant=context.tenant
        )
        context.attributes = []
        if context.client is not None:
            context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I log the configuration deletion event")
def log_configuration_deletion_event(context):
    try:
        if context.attributes and hasattr(context.current_event, 'attributes'):
            context.current_event.attributes = context.attributes

        context.client.log(context.current_event)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when("I attempt to log the configuration deletion event")
def attempt_log_configuration_deletion_event(context):
    if context.client is None:
        return
    log_configuration_deletion_event(context)


# ===== WHEN STEPS - COMPLEX AND BATCH OPERATIONS =====

@when("I add complex custom details with nested objects and arrays")
def add_complex_custom_details(context):
    context.custom_details = {
        "nested_object": {
            "key1": "value1",
            "key2": {
                "nested_key": "nested_value"
            }
        },
        "array_data": [
            {"item": 1, "name": "first"},
            {"item": 2, "name": "second"}
        ],
        "simple_string": "test_value",
        "numeric_value": 42
    }

    if hasattr(context.current_event, 'custom_details'):
        context.current_event.custom_details = context.custom_details


@when(parsers.parse('I attempt to log a security event with message "{message}"'))
def attempt_log_security_event_with_message(context, message: str):
    # Use intermittent failure pattern if available
    if hasattr(context, 'failure_simulation'):
        try:
            intermittent_client = context.failure_simulation.get_intermittent_client()
            event = SecurityEvent(
                data=message,
                user=context.user,
                tenant=context.tenant
            )
            intermittent_client.log(event)
            context.last_error = None
        except Exception as e:
            context.last_error = e
    else:
        create_security_event(context, message)
        if context.current_event and not context.last_error:
            attempt_log_security_event(context)

    result = {
        "event_type": "security",
        "message": message,
        "success": context.last_error is None,
        "error": context.last_error
    }
    context.individual_attempts.append(result)


@when(parsers.parse('I attempt to log a data access event for object "{object_name}"'))
def attempt_log_data_access_for_object(context, object_name: str):
    # Use intermittent failure pattern if available
    if hasattr(context, 'failure_simulation'):
        try:
            intermittent_client = context.failure_simulation.get_intermittent_client()
            event = DataAccessEvent(
                user=context.user,
                tenant=context.tenant,
                object_type="test_object",
                object_id={"name": object_name},
                subject_type="user",
                subject_id={"username": context.user},
                attributes=[DataAccessAttribute("data", successful=True)]
            )
            intermittent_client.log(event)
            context.last_error = None
        except Exception as e:
            context.last_error = e
    else:
        create_data_access_event(context)
        if context.current_event and not context.last_error:
            context.current_event.object_type = "test_object"
            context.current_event.object_id = {"name": object_name}
            context.current_event.subject_type = "user"
            context.current_event.subject_id = {"username": context.user}
            context.current_event.attributes = [DataAccessAttribute("data", successful=True)]
            attempt_log_data_access_event(context)

    result = {
        "event_type": "data_access",
        "object_name": object_name,
        "success": context.last_error is None,
        "error": context.last_error
    }
    context.individual_attempts.append(result)


@when(parsers.parse('I attempt to log a data modification event for object "{object_name}"'))
def attempt_log_data_modification_for_object(context, object_name: str):
    # Use intermittent failure pattern if available
    if hasattr(context, 'failure_simulation'):
        try:
            intermittent_client = context.failure_simulation.get_intermittent_client()
            event = DataModificationEvent(
                user=context.user,
                tenant=context.tenant,
                object_type="test_object",
                object_id={"name": object_name},
                subject_type="user",
                subject_id={"username": context.user},
                attributes=[ChangeAttribute("status", "old", "new")]
            )
            intermittent_client.log(event)
            context.last_error = None
        except Exception as e:
            context.last_error = e
    else:
        create_data_modification_event(context)
        if context.current_event and not context.last_error:
            context.current_event.object_type = "test_object"
            context.current_event.object_id = {"name": object_name}
            context.current_event.subject_type = "user"
            context.current_event.subject_id = {"username": context.user}
            context.current_event.attributes = [ChangeAttribute("status", "new", "old")]
            log_data_modification_event(context)

    result = {
        "event_type": "data_modification",
        "object_name": object_name,
        "success": context.last_error is None,
        "error": context.last_error
    }
    context.individual_attempts.append(result)


@when(parsers.parse('I attempt to log a configuration change event with ID "{config_id}"'))
def attempt_log_config_change_with_id(context, config_id: str):
    # Use intermittent failure pattern if available
    if hasattr(context, 'failure_simulation'):
        try:
            intermittent_client = context.failure_simulation.get_intermittent_client()
            event = ConfigurationChangeEvent(
                user=context.user,
                tenant=context.tenant,
                object_type="test_config",
                object_id={"config_id": config_id},
                attributes=[ChangeAttribute("setting", "old", "new")],
                id=config_id
            )
            intermittent_client.log(event)
            context.last_error = None
        except Exception as e:
            context.last_error = e
    else:
        create_configuration_change_event(context)
        if context.current_event and not context.last_error:
            context.current_event.object_type = "test_config"
            context.current_event.object_id = {"config_id": config_id}
            context.current_event.attributes = [ChangeAttribute("setting", "new", "old")]
            context.current_event.id = config_id
            log_configuration_change_event(context)

    result = {
        "event_type": "configuration_change",
        "config_id": config_id,
        "success": context.last_error is None,
        "error": context.last_error
    }
    context.individual_attempts.append(result)


# ===== WHEN STEPS - CONCURRENT OPERATIONS =====

@when("I log events simultaneously from multiple operations")
def log_events_simultaneously(context):
    context.concurrent_errors = []
    context.concurrent_results = []

    def log_event(user_index):
        try:
            user = context.multiple_users[user_index] if user_index < len(context.multiple_users) else f"user-{user_index}"
            event = SecurityEvent(
                data=f"Concurrent test event from {user}",
                user=user,
                tenant=context.tenant
            )

            # Use failure simulator if available (like individual attempts do)
            if hasattr(context, 'failure_simulation'):
                intermittent_client = context.failure_simulation.get_intermittent_client()
                intermittent_client.log(event)
            else:
                context.client.log(event)

            return {"success": True, "user": user}
        except Exception as e:
            return {"success": False, "user": user, "error": e}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(log_event, i) for i in range(6)]

        for future in as_completed(futures):
            result = future.result()
            context.concurrent_results.append(result)
            if not result["success"]:
                context.concurrent_errors.append(result["error"])


@when("I attempt to log events simultaneously from multiple operations")
def attempt_log_events_simultaneously(context):
    log_events_simultaneously(context)


@when("I attempt to log events simultaneously with mixed valid and invalid events")
def attempt_log_mixed_events_simultaneously(context):
    context.concurrent_errors = []
    context.concurrent_results = []

    def log_mixed_event(user_index):
        try:
            user = context.multiple_users[user_index] if user_index < len(context.multiple_users) else f"user-{user_index}"

            if user_index % 3 == 2:
                event = SecurityEvent(
                    data="",
                    user=user,
                    tenant=context.tenant
                )
            else:
                event = SecurityEvent(
                    data=f"Valid concurrent test event from {user}",
                    user=user,
                    tenant=context.tenant
                )

            context.client.log(event)
            return {"success": True, "user": user, "valid": user_index % 3 != 2}
        except Exception as e:
            return {"success": False, "user": user, "error": e, "valid": user_index % 3 != 2}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(log_mixed_event, i) for i in range(6)]

        for future in as_completed(futures):
            result = future.result()
            context.concurrent_results.append(result)
            if not result["success"]:
                context.concurrent_errors.append(result["error"])


# ===== WHEN STEPS - ADDITIONAL SCENARIOS =====

@when(parsers.parse('I log a configuration change event with ID "{config_id}"'))
def log_config_change_with_id(context, config_id: str):
    attempt_log_config_change_with_id(context, config_id)


@then(parsers.parse('I log a configuration change event with ID "{config_id}"'))
def then_log_config_change_with_id(context, config_id: str):
    log_config_change_with_id(context, config_id)


# ===== THEN STEPS - SUCCESS ASSERTIONS =====

@then("the event should be logged successfully")
def event_logged_successfully(context):
    assert context.last_error is None, f"Event logging failed: {context.last_error}"


@then("all events should be logged successfully")
def all_events_logged_successfully(context):
    assert context.last_error is None, f"Event logging failed: {context.last_error}"


@then("all concurrent events should be logged successfully")
def all_concurrent_events_successful(context):
    assert len(context.concurrent_errors) == 0, \
        f"Expected all events to succeed, but got {len(context.concurrent_errors)} errors: {context.concurrent_errors}"


@then("no errors should occur during concurrent logging")
def no_concurrent_errors(context):
    all_concurrent_events_successful(context)


# ===== THEN STEPS - FAILURE ASSERTIONS =====

@then("the logging should fail with a network error")
def logging_fails_network_error(context):
    assert context.last_error is not None, "Expected network error but logging succeeded"

    if isinstance(context.last_error, (ClientCreationError, AttributeError)):
        return

    error_msg = str(context.last_error).lower()
    network_terms = ["network", "connection", "unreachable", "timeout", "refused", "500", "503", "502", "504", "internal server error"]
    assert any(term in error_msg for term in network_terms), \
        f"Expected network error but got: {context.last_error}"


@then("the logging should fail with a transport error")
def logging_fails_transport_error(context):
    assert context.last_error is not None, "Expected transport error but logging succeeded"
    assert isinstance(context.last_error, (TransportError, AuthenticationError, ClientCreationError, AttributeError)), \
        f"Expected transport-related error but got: {type(context.last_error).__name__}: {context.last_error}"


@then("the operation should fail with the following errors:")
def operation_fails_with_errors(context):
    assert context.last_error is not None, "Expected validation errors but operation succeeded"

    assert isinstance(context.last_error, ValueError), \
        f"Expected ValueError but got: {type(context.last_error).__name__}: {context.last_error}"


# ===== THEN STEPS - MIXED RESULTS ASSERTIONS =====

@then("some events should succeed and some should fail")
def some_events_succeed_some_fail(context):
    if len(context.concurrent_results) == 0 and len(context.individual_attempts) > 0:
        successful_count = sum(1 for r in context.individual_attempts if r.get("success", False))
        failed_count = len(context.individual_attempts) - successful_count

        assert len(context.individual_attempts) > 0, "No individual attempts found"
        assert successful_count > 0, f"Expected some events to succeed, but all {len(context.individual_attempts)} failed"
        assert failed_count > 0, f"Expected some events to fail, but all {successful_count} succeeded"
        return

    if len(context.concurrent_results) == 0 and len(context.individual_attempts) == 0:
        pytest.fail("Expected mixed success and failures, but no failures were simulated. Check intermittent connectivity setup.")  # ty: ignore[invalid-argument-type]

    successful_count = sum(1 for r in context.concurrent_results if r.get("success", False))
    failed_count = len(context.concurrent_results) - successful_count

    assert successful_count > 0, f"Expected some events to succeed, but all {len(context.concurrent_results)} failed"
    assert failed_count > 0, f"Expected some events to fail, but all {successful_count} succeeded"


@then("the failed events should have error messages")
def failed_events_have_error_messages(context):
    if len(context.concurrent_results) == 0 and len(context.individual_attempts) > 0:
        failed_events = [r for r in context.individual_attempts if not r.get("success", False)]
        assert len(failed_events) > 0, "No failed individual attempts found to verify"

        for result in failed_events:
            assert "error" in result, f"Failed event should have an error: {result}"
            assert result["error"] is not None, f"Failed event should have a non-None error: {result}"
        return

    failed_events = [r for r in context.concurrent_results if not r.get("success", False)]
    assert len(failed_events) > 0, "No failed events found to verify"

    for result in failed_events:
        assert "error" in result, f"Failed event for {result.get('user', 'unknown')} should have an error"
        assert result["error"] is not None, f"Failed event for {result.get('user', 'unknown')} should have a non-None error"


@then("some concurrent events should fail with network errors")
def some_concurrent_network_errors(context):
    assert len(context.concurrent_errors) > 0, "Expected some network errors but all events succeeded"

    network_errors = []
    network_terms = ["network", "connection", "unreachable", "timeout", "refused", "500", "503", "502", "504", "internal server error"]
    for error in context.concurrent_errors:
        error_msg = str(error).lower()
        if any(term in error_msg for term in network_terms):
            network_errors.append(error)

    assert len(network_errors) > 0, f"Expected network errors but got: {context.concurrent_errors}"


@then("the successful events should be logged correctly")
def successful_events_logged_correctly(context):
    successful_events = [r for r in context.concurrent_results if r.get("success", False)]
    assert len(successful_events) > 0, "No successful events found to verify"


@then("no data corruption should occur")
def no_data_corruption(context):
    for result in context.concurrent_results:
        assert "success" in result, f"Result should have success field: {result}"
        assert isinstance(result["success"], bool), f"Success field should be boolean: {result}"


@then("the valid events should be logged successfully")
def valid_events_logged_successfully(context):
    valid_successful_events = [
        r for r in context.concurrent_results
        if r.get("success", False) and r.get("valid", True)
    ]
    valid_total_events = [r for r in context.concurrent_results if r.get("valid", True)]

    assert len(valid_successful_events) == len(valid_total_events), \
        f"Expected all {len(valid_total_events)} valid events to succeed, but only {len(valid_successful_events)} did"


@then("the invalid events should fail with validation errors")
def invalid_events_fail_validation(context):
    invalid_failed_events = [
        r for r in context.concurrent_results
        if not r.get("success", False) and not r.get("valid", True)
    ]
    invalid_total_events = [r for r in context.concurrent_results if not r.get("valid", True)]

    assert len(invalid_failed_events) == len(invalid_total_events), \
        f"Expected all {len(invalid_total_events)} invalid events to fail, but only {len(invalid_failed_events)} did"

    for result in invalid_failed_events:
        error = result.get("error")
        assert error is not None, f"Invalid event should have an error: {result}"
        assert isinstance(error, ValueError), \
            f"Invalid event should have validation error, got: {type(error).__name__}: {error}"


@then("no data inconsistencies should occur during validation")
def no_validation_inconsistencies(context):
    """Verify that no data corruption or inconsistencies occurred during concurrent validation."""
    for result in context.concurrent_results:
        assert "success" in result, f"Result missing success field: {result}"
        assert "user" in result, f"Result missing user field: {result}"
        assert isinstance(result["success"], bool), f"Success field should be boolean: {result}"

        # If the event failed, it should have an error
        if not result["success"]:
            assert "error" in result, f"Failed result should have error field: {result}"
            assert result["error"] is not None, f"Failed result should have non-None error: {result}"
