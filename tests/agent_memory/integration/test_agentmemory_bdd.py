"""BDD integration tests for the Agent Memory service (v1 API).

Run against a live service:

    AGENT_MEMORY_BASE_URL=http://localhost:3000 pytest tests/agent_memory/integration

Or against the deployed BTP service (with OAuth2):

    AGENT_MEMORY_BASE_URL=https://... \\
    AGENT_MEMORY_TOKEN_URL=https://... \\
    AGENT_MEMORY_CLIENT_ID=... \\
    AGENT_MEMORY_CLIENT_SECRET=... \\
    pytest tests/agent_memory/integration
"""

import pytest
from pytest_bdd import given, scenario, then, when

from sap_cloud_sdk.agent_memory.client import AgentMemoryClient

# -- Scenarios -----------------------------------------------------------------


@scenario("agentmemory.feature", "Create a new memory")
def test_add_memory():
    pass


@scenario("agentmemory.feature", "Get an existing memory")
def test_get_memory():
    pass


@scenario("agentmemory.feature", "Update memory content")
def test_update_memory():
    pass


@scenario("agentmemory.feature", "List memories with filter")
def test_list_memories():
    pass


@scenario("agentmemory.feature", "Delete a memory")
def test_delete_memory():
    pass


@scenario("agentmemory.feature", "Search memories by semantic query")
def test_search_memories():
    pass


@scenario("agentmemory.feature", "Create and get a message")
def test_add_message():
    pass


@scenario("agentmemory.feature", "List messages with filter")
def test_list_messages():
    pass


@scenario("agentmemory.feature", "Delete a message")
def test_delete_message():
    pass


@scenario("agentmemory.feature", "Get retention config")
def test_get_retention_config():
    pass


@scenario("agentmemory.feature", "Update retention config")
def test_update_retention_config():
    pass


@scenario("agentmemory.feature", "Count memories for an agent and invoker")
def test_count_memories():
    pass


@scenario("agentmemory.feature", "Filter memories by content substring")
def test_filter_memories_by_content():
    pass


@scenario("agentmemory.feature", "Filter messages by metadata substring")
def test_filter_messages_by_metadata():
    pass


# -- Fixtures / state ---------------------------------------------------------


@pytest.fixture
def context():
    return {}


# -- Given steps ---------------------------------------------------------------


@given("a configured Agent Memory client")
def configured_client(context, agent_memory_client):
    context["client"] = agent_memory_client


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "Test memory"'
)
def memory_exists_test(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "Test memory",
    )


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "Original content"'
)
def memory_exists_original(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "Original content",
    )


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "Listed memory"'
)
def memory_exists_listed(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "Listed memory",
    )


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "To be deleted"'
)
def memory_exists_delete(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "To be deleted",
    )


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "The user loves dark mode and dark themes"'
)
def memory_exists_search(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "The user loves dark mode and dark themes",
    )


@given(
    'a message exists with agent "test-agent" invoker "test-user" group "conv-list" role "USER" content "Listed message"'
)
def message_exists_list(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["message"] = agent_memory_client.add_message(
        "test-agent",
        "test-user",
        "conv-list",
        "USER",
        "Listed message",
    )


@given(
    'a message exists with agent "test-agent" invoker "test-user" group "conv-del" role "USER" content "To be deleted"'
)
def message_exists_delete(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["message"] = agent_memory_client.add_message(
        "test-agent",
        "test-user",
        "conv-del",
        "USER",
        "To be deleted",
    )


# -- When steps ----------------------------------------------------------------


@when(
    'I create a memory with agent "test-agent" and invoker "test-user" and content "User prefers dark mode"'
)
def add_memory(context):
    client: AgentMemoryClient = context["client"]
    context["memory"] = client.add_memory(
        "test-agent",
        "test-user",
        "User prefers dark mode",
    )


@when("I get the memory by id")
def get_memory(context):
    client: AgentMemoryClient = context["client"]
    context["fetched_memory"] = client.get_memory(context["memory"].id)


@when('I update the memory content to "Updated content"')
def update_memory(context):
    client: AgentMemoryClient = context["client"]
    client.update_memory(context["memory"].id, content="Updated content")
    context["memory"] = client.get_memory(context["memory"].id)


@when('I list memories filtered by agent "test-agent"')
def list_memories(context):
    client: AgentMemoryClient = context["client"]
    context["memories"] = client.list_memories(agent_id="test-agent")
    context["total"] = client.count_memories(agent_id="test-agent")


@when("I delete the memory")
def delete_memory(context):
    client: AgentMemoryClient = context["client"]
    client.delete_memory(context["memory"].id)
    context["deleted_memory_id"] = context["memory"].id


@when('I search for memories with query "dark mode preference"')
def search_memories(context):
    client: AgentMemoryClient = context["client"]
    context["search_results"] = client.search_memories(
        agent_id="test-agent",
        invoker_id="test-user",
        query="dark mode preference",
        threshold=0.5,
        limit=10,
    )


@when(
    'I create a message with agent "test-agent" invoker "test-user" group "conv-1" role "USER" content "Hello!"'
)
def add_message(context):
    client: AgentMemoryClient = context["client"]
    context["message"] = client.add_message(
        "test-agent",
        "test-user",
        "conv-1",
        "USER",
        "Hello!",
    )


@when('I list messages filtered by agent "test-agent" and group "conv-list"')
def list_messages(context):
    client: AgentMemoryClient = context["client"]
    context["messages"] = client.list_messages(
        agent_id="test-agent",
        message_group="conv-list",
    )
    context["total"] = len(context["messages"])


@when("I delete the message")
def delete_message(context):
    client: AgentMemoryClient = context["client"]
    client.delete_message(context["message"].id)
    context["deleted_message_id"] = context["message"].id


# -- Then steps ----------------------------------------------------------------


@then("the memory should have a non-empty id")
def check_memory_id(context):
    assert context["memory"].id != ""


@then('the memory should have agent_id "test-agent"')
def check_memory_agent_id(context):
    assert context["memory"].agent_id == "test-agent"


@then('the memory should have invoker_id "test-user"')
def check_memory_invoker_id(context):
    assert context["memory"].invoker_id == "test-user"


@then('the memory should have content "User prefers dark mode"')
def check_memory_content_dark(context):
    assert context["memory"].content == "User prefers dark mode"


@then('the memory should have content "Updated content"')
def check_memory_content_updated(context):
    assert context["memory"].content == "Updated content"


@then("the returned memory should match the created memory")
def check_fetched_memory(context):
    assert context["fetched_memory"].id == context["memory"].id
    assert context["fetched_memory"].content == context["memory"].content


@then("the result should contain at least one memory")
def check_memories_not_empty(context):
    assert len(context["memories"]) >= 1


@then("the total count should be a positive number")
def check_total_positive(context):
    assert context["total"] is not None
    assert context["total"] >= 1


@then("the memory should no longer exist")
def check_memory_deleted(context):
    from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryNotFoundError

    client: AgentMemoryClient = context["client"]
    with pytest.raises(AgentMemoryNotFoundError):
        client.get_memory(context["deleted_memory_id"])


@then("the search result should contain at least one result")
def check_search_not_empty(context):
    assert len(context["search_results"]) >= 1


@then("each result should have a non-empty content")
def check_result_content(context):
    for result in context["search_results"]:
        assert result.content != ""


@then("the message should have a non-empty id")
def check_message_id(context):
    assert context["message"].id != ""


@then('the message should have role "USER"')
def check_message_role(context):
    assert context["message"].role == "USER"


@then('the message should have content "Hello!"')
def check_message_content(context):
    assert context["message"].content == "Hello!"


@then("the result should contain at least one message")
def check_messages_not_empty(context):
    assert len(context["messages"]) >= 1


@then("the message should no longer exist")
def check_message_deleted(context):
    from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryNotFoundError

    client: AgentMemoryClient = context["client"]
    with pytest.raises(AgentMemoryNotFoundError):
        client.get_message(context["deleted_message_id"])


# -- Admin: Retention Config steps ---------------------------------------------


@when("I get the retention config")
def get_retention_config(context):
    client: AgentMemoryClient = context["client"]
    context["retention_config"] = client.get_retention_config()


@when("I update the retention config with message_days 30 and memory_days 90")
def update_retention_config(context):
    client: AgentMemoryClient = context["client"]
    client.update_retention_config(message_days=30, memory_days=90)
    context["retention_config"] = client.get_retention_config()


@then("the retention config should have a non-empty id")
def check_retention_config_id(context):
    assert context["retention_config"].id != ""


@then("the retention config should have message_days 30")
def check_retention_message_days(context):
    assert context["retention_config"].message_days == 30


@then("the retention config should have memory_days 90")
def check_retention_memory_days(context):
    assert context["retention_config"].memory_days == 90


# -- Bulk / utility steps -------------------------------------------------------


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "Count test memory"'
)
def memory_exists_count(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "Count test memory",
    )


@when('I count memories for agent "test-agent" and invoker "test-user"')
def count_memories(context):
    client: AgentMemoryClient = context["client"]
    context["memory_count"] = client.count_memories(
        agent_id="test-agent",
        invoker_id="test-user",
    )


@then("the memory count should be a positive number")
def check_memory_count_positive(context):
    assert context["memory_count"] >= 1


# -- Filter steps ---------------------------------------------------------------


@given(
    'a memory exists with agent "test-agent" and invoker "test-user" and content "The user prefers dark mode"'
)
def memory_exists_dark_mode(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        "test-agent",
        "test-user",
        "The user prefers dark mode",
    )


@given(
    'a message exists with agent "test-agent" invoker "test-user" group "conv-filter" role "USER" content "filter-test-message" and metadata "filter-marker"'
)
def message_exists_filter(context, agent_memory_client):
    context["client"] = agent_memory_client
    context["message"] = agent_memory_client.add_message(
        "test-agent",
        "test-user",
        "conv-filter",
        "USER",
        "filter-test-message",
        metadata={"tag": "filter-marker"},
    )


@when('I list memories filtered by content containing "dark mode"')
def list_memories_by_content(context):
    from sap_cloud_sdk.agent_memory import FilterDefinition

    client: AgentMemoryClient = context["client"]
    context["memories"] = client.list_memories(
        agent_id="test-agent",
        invoker_id="test-user",
        filters=[FilterDefinition(target="content", contains="dark mode")],
    )


@when('I list messages filtered by metadata containing "filter-marker"')
def list_messages_by_metadata(context):
    from sap_cloud_sdk.agent_memory import FilterDefinition

    client: AgentMemoryClient = context["client"]
    context["messages"] = client.list_messages(
        agent_id="test-agent",
        invoker_id="test-user",
        message_group="conv-filter",
        filters=[FilterDefinition(target="metadata", contains="filter-marker")],
    )


@then('the result should contain the memory with content "The user prefers dark mode"')
def check_memory_content_in_results(context):
    contents = [m.content for m in context["memories"]]
    assert "The user prefers dark mode" in contents


@then('the result should contain the message with content "filter-test-message"')
def check_message_content_in_results(context):
    contents = [m.content for m in context["messages"]]
    assert "filter-test-message" in contents
