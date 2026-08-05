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
from pytest_bdd import given, parsers, scenario, then, when

from sap_cloud_sdk.agent_memory import AccessStrategy, FilterDefinition, MessageRole
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient

# -- Scenarios -----------------------------------------------------------------

# ── Provider scenarios ────────────────────────────────────────────────────────


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


# ── Subscriber scenarios ──────────────────────────────────────────────────────


@scenario("agentmemory.feature", "Create a new memory using SUBSCRIBER access strategy")
def test_add_memory_subscriber():
    pass


@scenario("agentmemory.feature", "Get a memory using SUBSCRIBER access strategy")
def test_get_memory_subscriber():
    pass


@scenario("agentmemory.feature", "Update memory content using SUBSCRIBER access strategy")
def test_update_memory_subscriber():
    pass


@scenario("agentmemory.feature", "List memories using SUBSCRIBER access strategy")
def test_list_memories_subscriber():
    pass


@scenario("agentmemory.feature", "Delete a memory using SUBSCRIBER access strategy")
def test_delete_memory_subscriber():
    pass


@scenario("agentmemory.feature", "Search memories using SUBSCRIBER access strategy")
def test_search_memories_subscriber():
    pass


@scenario("agentmemory.feature", "Create and get a message using SUBSCRIBER access strategy")
def test_add_message_subscriber():
    pass


@scenario("agentmemory.feature", "List messages using SUBSCRIBER access strategy")
def test_list_messages_subscriber():
    pass


@scenario("agentmemory.feature", "Delete a message using SUBSCRIBER access strategy")
def test_delete_message_subscriber():
    pass


@scenario("agentmemory.feature", "Count memories using SUBSCRIBER access strategy")
def test_count_memories_subscriber():
    pass


@scenario("agentmemory.feature", "Filter subscriber memories by content substring")
def test_filter_memories_by_content_subscriber():
    pass


@scenario("agentmemory.feature", "Filter subscriber messages by metadata substring")
def test_filter_messages_by_metadata_subscriber():
    pass


# -- Fixtures / state ---------------------------------------------------------


@pytest.fixture
def context():
    return {
        "access_strategy": AccessStrategy.PROVIDER,
        "tenant": None,
    }


# -- Given steps ---------------------------------------------------------------


@given("a configured Agent Memory client")
def configured_client(context, agent_memory_client):
    context["client"] = agent_memory_client


@given("I use the configured subscriber tenant")
def use_configured_subscriber_tenant(context, subscriber_tenant):
    context["access_strategy"] = AccessStrategy.SUBSCRIBER
    context["tenant"] = subscriber_tenant


@given(
    parsers.parse(
        'a memory exists with agent "{agent_id}" and invoker "{invoker_id}" and content "{content}"'
    )
)
def memory_exists(context, agent_memory_client, agent_id, invoker_id, content):
    context["client"] = agent_memory_client
    context["memory"] = agent_memory_client.add_memory(
        agent_id, invoker_id, content,
    )


@given(
    parsers.parse(
        'a message exists with agent "{agent_id}" invoker "{invoker_id}" group "{group}" role "{role}" content "{content}"'
    )
)
def message_exists(context, agent_memory_client, agent_id, invoker_id, group, role, content):
    context["client"] = agent_memory_client
    context["message"] = agent_memory_client.add_message(
        agent_id, invoker_id, group, role, content,
    )


@given(
    parsers.parse(
        'a message exists with agent "{agent_id}" invoker "{invoker_id}" group "{group}" role "{role}" content "{content}" and metadata "{metadata_value}"'
    )
)
def message_exists_with_metadata(context, agent_memory_client, agent_id, invoker_id, group, role, content, metadata_value):
    context["client"] = agent_memory_client
    context["message"] = agent_memory_client.add_message(
        agent_id, invoker_id, group, role, content,
        metadata={"tag": metadata_value},
    )


# -- When steps ----------------------------------------------------------------


@when(
    parsers.parse(
        'I create a memory with agent "{agent_id}" and invoker "{invoker_id}" and content "{content}"'
    )
)
def add_memory(context, agent_id, invoker_id, content):
    client: AgentMemoryClient = context["client"]
    context["memory"] = client.add_memory(
        agent_id, invoker_id, content,
    )


@when("I get the memory by id")
def get_memory(context):
    client: AgentMemoryClient = context["client"]
    context["fetched_memory"] = client.get_memory(
        context["memory"].id,
    )


@when(parsers.parse('I update the memory content to "{content}"'))
def update_memory(context, content):
    client: AgentMemoryClient = context["client"]
    client.update_memory(
        context["memory"].id, content=content,
    )
    context["memory"] = client.get_memory(
        context["memory"].id,
    )


@when(parsers.parse('I list memories filtered by agent "{agent_id}"'))
def list_memories(context, agent_id):
    client: AgentMemoryClient = context["client"]
    context["memories"] = client.list_memories(
        agent_id=agent_id,
    )
    context["total"] = client.count_memories(
        agent_id=agent_id,
    )


@when("I delete the memory")
def delete_memory(context):
    client: AgentMemoryClient = context["client"]
    client.delete_memory(
        context["memory"].id,
    )
    context["deleted_memory_id"] = context["memory"].id


@when(parsers.parse('I search for memories with query "{query}"'))
def search_memories(context, query):
    client: AgentMemoryClient = context["client"]
    context["search_results"] = client.search_memories(
        agent_id="test-agent",
        invoker_id="test-user",
        query=query,
        threshold=0.5,
        limit=10,
    )


@when(
    parsers.parse(
        'I create a message with agent "{agent_id}" invoker "{invoker_id}" group "{group}" role "{role}" content "{content}"'
    )
)
def add_message(context, agent_id, invoker_id, group, role, content):
    client: AgentMemoryClient = context["client"]
    context["message"] = client.add_message(
        agent_id, invoker_id, group, MessageRole(role), content,
    )


@when(
    parsers.parse(
        'I list messages filtered by agent "{agent_id}" and group "{group}"'
    )
)
def list_messages(context, agent_id, group):
    client: AgentMemoryClient = context["client"]
    context["messages"] = client.list_messages(
        agent_id=agent_id,
        message_group=group,
    )
    context["total"] = len(context["messages"])


@when("I delete the message")
def delete_message(context):
    client: AgentMemoryClient = context["client"]
    client.delete_message(
        context["message"].id,
    )
    context["deleted_message_id"] = context["message"].id


@when("I get the retention config")
def get_retention_config(context):
    client: AgentMemoryClient = context["client"]
    context["retention_config"] = client.get_retention_config(
    )


@when("I update the retention config with message_days 30 and memory_days 90")
def update_retention_config(context):
    client: AgentMemoryClient = context["client"]
    client.update_retention_config(
        message_days=30, memory_days=90,
    )
    context["retention_config"] = client.get_retention_config(
    )


@when(
    parsers.parse(
        'I count memories for agent "{agent_id}" and invoker "{invoker_id}"'
    )
)
def count_memories(context, agent_id, invoker_id):
    client: AgentMemoryClient = context["client"]
    context["memory_count"] = client.count_memories(
        agent_id=agent_id,
        invoker_id=invoker_id,
    )


@when(parsers.parse('I list memories filtered by content containing "{substring}"'))
def list_memories_by_content(context, substring):
    client: AgentMemoryClient = context["client"]
    context["memories"] = client.list_memories(
        agent_id="test-agent",
        invoker_id="test-user",
        filters=[FilterDefinition(target="content", contains=substring)],
    )


@when(parsers.parse('I list messages filtered by metadata containing "{substring}"'))
def list_messages_by_metadata(context, substring):
    client: AgentMemoryClient = context["client"]
    context["messages"] = client.list_messages(
        agent_id="test-agent",
        invoker_id="test-user",
        message_group="conv-filter",
        filters=[FilterDefinition(target="metadata", contains=substring)],
    )


# -- Then steps ----------------------------------------------------------------


@then("the memory should have a non-empty id")
def check_memory_id(context):
    assert context["memory"].id != ""


@then(parsers.parse('the memory should have agent_id "{agent_id}"'))
def check_memory_agent_id(context, agent_id):
    assert context["memory"].agent_id == agent_id


@then(parsers.parse('the memory should have invoker_id "{invoker_id}"'))
def check_memory_invoker_id(context, invoker_id):
    assert context["memory"].invoker_id == invoker_id


@then(parsers.parse('the memory should have content "{content}"'))
def check_memory_content(context, content):
    assert context["memory"].content == content


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
        client.get_memory(
            context["deleted_memory_id"],
        )


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


@then(parsers.parse('the message should have content "{content}"'))
def check_message_content(context, content):
    assert context["message"].content == content


@then("the result should contain at least one message")
def check_messages_not_empty(context):
    assert len(context["messages"]) >= 1


@then("the message should no longer exist")
def check_message_deleted(context):
    from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryNotFoundError

    client: AgentMemoryClient = context["client"]
    with pytest.raises(AgentMemoryNotFoundError):
        client.get_message(
            context["deleted_message_id"],
        )


@then("the retention config should have a non-empty id")
def check_retention_config_id(context):
    assert context["retention_config"].id != ""


@then("the retention config should have message_days 30")
def check_retention_message_days(context):
    assert context["retention_config"].message_days == 30


@then("the retention config should have memory_days 90")
def check_retention_memory_days(context):
    assert context["retention_config"].memory_days == 90


@then("the memory count should be a positive number")
def check_memory_count_positive(context):
    assert context["memory_count"] >= 1


@then(parsers.parse('the result should contain the memory with content "{content}"'))
def check_memory_content_in_results(context, content):
    contents = [m.content for m in context["memories"]]
    assert content in contents


@then(parsers.parse('the result should contain the message with content "{content}"'))
def check_message_content_in_results(context, content):
    contents = [m.content for m in context["messages"]]
    assert content in contents
