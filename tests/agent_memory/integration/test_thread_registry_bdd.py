"""BDD integration tests for the Thread Registry.

Run against a live Agent Memory service:

    pytest tests/agent_memory/integration/test_thread_registry_bdd.py

Credentials are loaded from .env_integration_tests (same file as the memory
integration tests). All tests are automatically skipped when credentials are
absent.
"""

import uuid

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryThreadConflictError,
    AgentMemoryThreadNotFoundError,
)
from sap_cloud_sdk.agent_memory.thread_registry import SAPAgentMemoryThreadRegistry

# -- Scenarios -----------------------------------------------------------------


@scenario("thread_registry.feature", "Register and get a thread")
def test_register_and_get_thread():
    pass


@scenario("thread_registry.feature", "Create a thread with server-assigned ID")
def test_create_thread():
    pass


@scenario("thread_registry.feature", "List threads filtered by agent_id")
def test_list_threads():
    pass


@scenario("thread_registry.feature", "Update thread description")
def test_update_thread():
    pass


@scenario("thread_registry.feature", "Delete a thread")
def test_delete_thread():
    pass


@scenario(
    "thread_registry.feature",
    "Re-registering same thread with same owner is idempotent",
)
def test_register_idempotent():
    pass


@scenario(
    "thread_registry.feature",
    "Registering same thread with different owner raises a conflict",
)
def test_register_conflict():
    pass


# -- Fixtures / state ----------------------------------------------------------


@pytest.fixture
def context(run_thread_agent_id):
    return {
        "agent_id": run_thread_agent_id,
        "invoker_id": "test-user",
        "thread": None,
        "fetched_thread": None,
        "threads": None,
        "error": None,
    }


# -- Given steps ---------------------------------------------------------------


@given("a configured Thread Registry")
def configured_thread_registry(context, thread_registry):
    context["registry"] = thread_registry


@given(
    parsers.parse(
        'a thread is registered with agent "{agent_id}" and invoker "{invoker_id}"'
    )
)
def thread_is_registered(context, thread_registry, agent_id, invoker_id):
    context["registry"] = thread_registry
    thread_id = str(uuid.uuid4())
    context["thread"] = thread_registry.create_or_register_thread(
        context["agent_id"], context["invoker_id"], thread_id=thread_id
    )


# -- When steps ----------------------------------------------------------------


@when(
    parsers.parse(
        'I register a thread with agent "{agent_id}" and invoker "{invoker_id}"'
    )
)
def register_thread(context, agent_id, invoker_id):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    thread_id = str(uuid.uuid4())
    context["thread"] = registry.create_or_register_thread(
        context["agent_id"], context["invoker_id"], thread_id=thread_id
    )


@when(
    parsers.parse(
        'I register the same thread again with agent "{agent_id}" and invoker "{invoker_id}"'
    )
)
def register_same_thread_again(context, agent_id, invoker_id):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    try:
        context["thread"] = registry.create_or_register_thread(
            context["agent_id"],
            context["invoker_id"],
            thread_id=context["thread"]["threadId"],
        )
        context["error"] = None
    except Exception as exc:
        context["error"] = exc


@when(
    parsers.parse(
        'I register the same thread with agent "{agent_id}" and invoker "{invoker_id}"'
    )
)
def register_same_thread_different_owner(context, agent_id, invoker_id):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    try:
        registry.create_or_register_thread(
            agent_id, invoker_id, thread_id=context["thread"]["threadId"]
        )
        context["error"] = None
    except AgentMemoryThreadConflictError as exc:
        context["error"] = exc


@when(
    parsers.parse(
        'I create a thread with agent "{agent_id}" and invoker "{invoker_id}"'
    )
)
def create_thread(context, agent_id, invoker_id):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    context["thread"] = registry.create_or_register_thread(
        context["agent_id"], context["invoker_id"]
    )


@when("I get the thread by id")
def get_thread(context):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    context["fetched_thread"] = registry.get_thread(context["thread"]["threadId"])


@when(parsers.parse('I list threads filtered by agent "{agent_id}"'))
def list_threads(context, agent_id):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    context["threads"] = registry.list_threads(agent_id=context["agent_id"])


@when(parsers.parse('I update the thread description to "{description}"'))
def update_thread(context, description):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    context["thread"] = registry.update_thread(
        context["thread"]["threadId"], description=description
    )


@when("I delete the thread")
def delete_thread(context):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    registry.delete_thread(context["thread"]["threadId"])


# -- Then steps ----------------------------------------------------------------


@then("the thread should have a non-empty threadId")
def check_thread_id(context):
    assert context["thread"]["threadId"] != ""


@then(parsers.parse('the thread should have agentId "{agent_id}"'))
def check_thread_agent_id(context, agent_id):
    assert context["thread"]["agentId"] == context["agent_id"]


@then(parsers.parse('the thread should have invokerId "{invoker_id}"'))
def check_thread_invoker_id(context, invoker_id):
    assert context["thread"]["invokerId"] == context["invoker_id"]


@then("the fetched thread should match the registered thread")
def check_fetched_thread(context):
    assert context["fetched_thread"]["threadId"] == context["thread"]["threadId"]
    assert context["fetched_thread"]["agentId"] == context["thread"]["agentId"]


@then("the result should contain at least one thread")
def check_threads_not_empty(context):
    assert len(context["threads"]["entries"]) >= 1


@then(parsers.parse('all returned threads should have agentId "{agent_id}"'))
def check_all_threads_agent_id(context, agent_id):
    assert all(
        t["agentId"] == context["agent_id"] for t in context["threads"]["entries"]
    )


@then(parsers.parse('the thread should have description "{description}"'))
def check_thread_description(context, description):
    assert context["thread"]["description"] == description


@then("getting the thread should raise AgentMemoryThreadNotFoundError")
def check_thread_deleted(context):
    registry: SAPAgentMemoryThreadRegistry = context["registry"]
    with pytest.raises(AgentMemoryThreadNotFoundError):
        registry.get_thread(context["thread"]["threadId"])


@then("no error should be raised")
def check_no_error(context):
    assert context["error"] is None


@then("a AgentMemoryThreadConflictError should be raised")
def check_ownership_conflict(context):
    assert isinstance(context["error"], AgentMemoryThreadConflictError)
