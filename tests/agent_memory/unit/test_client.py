"""Unit tests for AgentMemoryClient operations (v1 API)."""

import pytest
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.agent_memory._endpoints import (
    MEMORIES,
    MEMORY_SEARCH,
    MESSAGES,
    RETENTION_CONFIG,
)
from sap_cloud_sdk.agent_memory._http_transport import HttpTransport
from sap_cloud_sdk.agent_memory._models import (
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory import create_client, FilterDefinition
from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryValidationError


def _make_client() -> tuple[AgentMemoryClient, MagicMock]:
    """Return an AgentMemoryClient with a mocked transport layer."""
    transport = MagicMock(spec=HttpTransport)
    client = AgentMemoryClient(transport)
    return client, transport


# ── create_client factory ─────────────────────────────────────────────────────


class TestCreateClient:

    def test_uses_provided_config(self):
        """Factory accepts an explicit config object."""
        config = AgentMemoryConfig(base_url="http://localhost:3000")
        with patch("sap_cloud_sdk.agent_memory.HttpTransport") as MockTransport:
            MockTransport.return_value = MagicMock(spec=HttpTransport)
            client = create_client(config=config)
        assert isinstance(client, AgentMemoryClient)

    def test_reads_env_when_no_config_provided(self, monkeypatch):
        """Factory falls back to environment variables when no config given."""
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL", "http://memory.example.com")
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_URL", "http://auth.example.com")
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_CLIENTID", "client-id")
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_CLIENTSECRET", "client-secret")
        with patch("sap_cloud_sdk.agent_memory.HttpTransport") as MockTransport:
            MockTransport.return_value = MagicMock(spec=HttpTransport)
            client = create_client()
        assert isinstance(client, AgentMemoryClient)


# ── Memory CRUD operations ────────────────────────────────────────────────────


class TestMemoryCRUD:

    def test_add_memory_posts_correct_payload(self):
        """add_memory sends required and optional fields in the POST body."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "mem-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "content": "some memory",
            "createType": "DIRECT",
        }

        memory = client.add_memory("agent-a", "user-b", "some memory")

        assert isinstance(memory, Memory)
        assert memory.id == "mem-1"
        payload = mock_transport.post.call_args[1]["json"]
        assert payload["agentID"] == "agent-a"
        assert payload["invokerID"] == "user-b"
        assert payload["content"] == "some memory"

    def test_add_memory_with_metadata(self):
        """Optional metadata is included in the POST body when provided."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "x",
        }

        client.add_memory("a", "u", "x", metadata={"key": "val"})

        payload = mock_transport.post.call_args[1]["json"]
        assert payload["metadata"] == {"key": "val"}

    def test_add_memory_excludes_none_optionals(self):
        """None-valued optional fields are omitted from the POST body."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "x",
        }

        client.add_memory("a", "u", "x")

        payload = mock_transport.post.call_args[1]["json"]
        assert "metadata" not in payload
        assert "createType" not in payload

    def test_add_memory_posts_to_memories_endpoint(self):
        """add_memory sends the POST to the MEMORIES endpoint."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "x",
        }

        client.add_memory("a", "u", "x")

        call_path = mock_transport.post.call_args[0][0]
        assert call_path == MEMORIES

    def test_get_memory_calls_get_with_memory_id(self):
        """get_memory constructs the correct path with the memory ID."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "hello",
        }

        memory = client.get_memory("mem-1")

        assert memory.id == "mem-1"
        call_path = mock_transport.get.call_args[0][0]
        assert call_path == f"{MEMORIES}(mem-1)"

    def test_update_memory_calls_patch(self):
        """update_memory sends a PATCH with the updated fields."""
        client, mock_transport = _make_client()

        client.update_memory("mem-1", content="updated")

        mock_transport.patch.assert_called_once()
        payload = mock_transport.patch.call_args[1]["json"]
        assert payload["content"] == "updated"

    def test_update_memory_excludes_none_fields(self):
        """update_memory omits None-valued optional fields from the PATCH body."""
        client, mock_transport = _make_client()

        client.update_memory("mem-1", content="x")

        payload = mock_transport.patch.call_args[1]["json"]
        assert "metadata" not in payload

    def test_update_memory_with_metadata_only(self):
        """update_memory supports updating metadata without content."""
        client, mock_transport = _make_client()

        client.update_memory("mem-1", metadata={"key": "new-meta"})

        payload = mock_transport.patch.call_args[1]["json"]
        assert payload["metadata"] == {"key": "new-meta"}
        assert "content" not in payload

    def test_delete_memory_calls_delete(self):
        """delete_memory sends a DELETE to the correct path."""
        client, mock_transport = _make_client()

        client.delete_memory("mem-1")

        mock_transport.delete.assert_called_once()
        call_path = mock_transport.delete.call_args[0][0]
        assert call_path == f"{MEMORIES}(mem-1)"


# ── Memory listing ────────────────────────────────────────────────────────────


class TestListMemories:

    def test_returns_list_of_memories(self):
        """list_memories returns a list of Memory objects."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {
            "value": [
                {"id": "m1", "agentID": "a", "invokerID": "u", "content": "memory 1"},
            ],
        }

        memories = client.list_memories(agent_id="a", invoker_id="u")

        assert len(memories) == 1
        assert isinstance(memories[0], Memory)

    def test_passes_filter_for_agent_and_invoker(self):
        """Convenience agent_id/invoker_id args are converted to $filter."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(agent_id="agent-x", invoker_id="user-y")

        params = mock_transport.get.call_args[1]["params"]
        assert "agentID eq 'agent-x'" in params["$filter"]
        assert "invokerID eq 'user-y'" in params["$filter"]

    def test_default_limit_is_50(self):
        """Default limit is 50 ($top=50)."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories()

        params = mock_transport.get.call_args[1]["params"]
        assert params["$top"] == "50"

    def test_custom_limit(self):
        """Custom limit is forwarded as $top."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(limit=5)

        params = mock_transport.get.call_args[1]["params"]
        assert params["$top"] == "5"

    def test_empty_list(self):
        """list_memories handles empty responses correctly."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        memories = client.list_memories()

        assert len(memories) == 0

    def test_offset_passes_skip_param(self):
        """Non-zero offset is forwarded as $skip."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(offset=50)

        params = mock_transport.get.call_args[1]["params"]
        assert params["$skip"] == "50"

    def test_zero_offset_omits_skip_param(self):
        """Default offset of 0 does not add $skip to the request."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories()

        params = mock_transport.get.call_args[1]["params"]
        assert "$skip" not in params

    def test_filter_metadata_contains_adds_contains_clause(self):
        """A metadata FilterDefinition produces a contains(metadata, ...) expression."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(
            filters=[FilterDefinition(target="metadata", contains="john")],
        )

        params = mock_transport.get.call_args[1]["params"]
        assert "contains(metadata, 'john')" in params["$filter"]

    def test_filter_content_contains_adds_contains_clause(self):
        """A content FilterDefinition produces a contains(content, ...) expression."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(
            filters=[FilterDefinition(target="content", contains="dark mode")],
        )

        params = mock_transport.get.call_args[1]["params"]
        assert "contains(content, 'dark mode')" in params["$filter"]

    def test_filter_multiple_clauses_joined_with_and(self):
        """Multiple FilterDefinitions are joined with 'and' in $filter."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(
            filters=[
                FilterDefinition(target="metadata", contains="john"),
                FilterDefinition(target="content", contains="user prefers"),
            ],
        )

        params = mock_transport.get.call_args[1]["params"]
        f = params["$filter"]
        assert "contains(metadata, 'john')" in f
        assert "contains(content, 'user prefers')" in f
        assert " and " in f

    def test_filter_combines_with_agent_and_invoker_filters(self):
        """FilterDefinitions are combined with agent_id/invoker_id eq predicates."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(
            agent_id="my-agent",
            invoker_id="user-1",
            filters=[FilterDefinition(target="content", contains="dark mode")],
        )

        params = mock_transport.get.call_args[1]["params"]
        f = params["$filter"]
        assert "agentID eq 'my-agent'" in f
        assert "invokerID eq 'user-1'" in f
        assert "contains(content, 'dark mode')" in f

    def test_filter_none_does_not_change_behaviour(self):
        """filter=None produces the same $filter as before (no regression)."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_memories(agent_id="a", invoker_id="u", filters=None)

        params = mock_transport.get.call_args[1]["params"]
        assert params["$filter"] == "agentID eq 'a' and invokerID eq 'u'"


class TestCountMemories:

    def test_returns_count_from_response(self):
        """count_memories returns the @odata.count value."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": [], "@odata.count": 42}

        total = client.count_memories(agent_id="a", invoker_id="u")

        assert total == 42

    def test_sends_top_0_and_count_true(self):
        """count_memories uses $top=0 and $count=true."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": [], "@odata.count": 0}

        client.count_memories()

        params = mock_transport.get.call_args[1]["params"]
        assert params["$top"] == "0"
        assert params["$count"] == "true"

    def test_passes_filter_when_agent_and_invoker_provided(self):
        """count_memories forwards agent_id and invoker_id as $filter."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": [], "@odata.count": 3}

        client.count_memories(agent_id="agt", invoker_id="usr")

        params = mock_transport.get.call_args[1]["params"]
        assert "agentID eq 'agt'" in params["$filter"]
        assert "invokerID eq 'usr'" in params["$filter"]

    def test_returns_zero_when_count_missing(self):
        """count_memories returns 0 when count is absent from response."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        total = client.count_memories()

        assert total == 0


# ── Memory search ─────────────────────────────────────────────────────────────


class TestSearchMemories:

    def test_returns_results_in_api_order(self):
        """search_memories returns results in the order returned by the API."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "value": [
                {"id": "m1", "agentID": "a", "invokerID": "u", "content": "first", "similarity": 0.5},
                {"id": "m2", "agentID": "a", "invokerID": "u", "content": "second", "similarity": 0.9},
            ]
        }

        results = client.search_memories("a", "u", "test query")

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].similarity == 0.5
        assert results[1].similarity == 0.9

    def test_posts_correct_payload(self):
        """search_memories sends the correct payload to the search endpoint."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {"value": []}

        client.search_memories("agent-a", "user-b", "my query", threshold=0.7, limit=5)

        call_path = mock_transport.post.call_args[0][0]
        assert call_path == MEMORY_SEARCH
        payload = mock_transport.post.call_args[1]["json"]
        assert payload["agentID"] == "agent-a"
        assert payload["invokerID"] == "user-b"
        assert payload["query"] == "my query"
        assert payload["threshold"] == 0.7
        assert payload["top"] == 5

    def test_empty_results(self):
        """search_memories handles empty search results."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {"value": []}

        results = client.search_memories("a", "u", "empty query")

        assert len(results) == 0

    def test_uses_default_threshold_and_limit(self):
        """search_memories uses default threshold=0.6 and limit=10."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {"value": []}

        client.search_memories("a", "u", "query")

        payload = mock_transport.post.call_args[1]["json"]
        assert payload["threshold"] == 0.6
        assert payload["top"] == 10
        assert "skip" not in payload


# ── Message operations ────────────────────────────────────────────────────────


class TestMessageCRUD:

    def test_add_message_posts_correct_payload(self):
        """add_message sends required fields in the POST body."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "msg-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "messageGroup": "conv-1",
            "role": "USER",
            "content": "Hello!",
        }

        message = client.add_message(
            "agent-a", "user-b", "conv-1", MessageRole.USER, "Hello!",
        )

        assert isinstance(message, Message)
        assert message.id == "msg-1"
        assert message.role == "USER"
        payload = mock_transport.post.call_args[1]["json"]
        assert payload["agentID"] == "agent-a"
        assert payload["invokerID"] == "user-b"
        assert payload["messageGroup"] == "conv-1"
        assert payload["role"] == "USER"
        assert payload["content"] == "Hello!"

    def test_add_message_posts_to_messages_endpoint(self):
        """add_message sends the POST to the MESSAGES endpoint."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        }

        client.add_message("a", "u", "g", MessageRole.USER, "hi")

        call_path = mock_transport.post.call_args[0][0]
        assert call_path == MESSAGES

    def test_add_message_with_metadata(self):
        """Optional metadata is included when provided."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
            "metadata": {"key": "val"},
        }

        client.add_message("a", "u", "g", MessageRole.USER, "hi", metadata={"key": "val"})

        payload = mock_transport.post.call_args[1]["json"]
        assert payload["metadata"] == {"key": "val"}

    def test_add_message_excludes_none_metadata(self):
        """None-valued metadata is omitted from the POST body."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        }

        client.add_message("a", "u", "g", MessageRole.USER, "hi")

        payload = mock_transport.post.call_args[1]["json"]
        assert "metadata" not in payload

    def test_get_message_calls_get_with_message_id(self):
        """get_message constructs the correct path with the message ID."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        }

        message = client.get_message("msg-1")

        assert message.id == "msg-1"
        call_path = mock_transport.get.call_args[0][0]
        assert call_path == f"{MESSAGES}(msg-1)"

    def test_delete_message_calls_delete(self):
        """delete_message sends a DELETE to the correct path."""
        client, mock_transport = _make_client()

        client.delete_message("msg-1")

        mock_transport.delete.assert_called_once()
        call_path = mock_transport.delete.call_args[0][0]
        assert call_path == f"{MESSAGES}(msg-1)"


# ── Message listing ───────────────────────────────────────────────────────────


class TestListMessages:

    def test_returns_list_of_messages(self):
        """list_messages returns a list of Message objects."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {
            "value": [
                {
                    "id": "msg-1", "agentID": "a", "invokerID": "u",
                    "messageGroup": "g", "role": "USER", "content": "hi",
                },
            ],
        }

        messages = client.list_messages(agent_id="a", invoker_id="u")

        assert len(messages) == 1
        assert isinstance(messages[0], Message)

    def test_passes_convenience_filters(self):
        """Convenience filters are converted to $filter."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(
            agent_id="a", invoker_id="u",
            message_group="conv-1", role="USER",
        )

        params = mock_transport.get.call_args[1]["params"]
        f = params["$filter"]
        assert "agentID eq 'a'" in f
        assert "invokerID eq 'u'" in f
        assert "messageGroup eq 'conv-1'" in f
        assert "role eq 'USER'" in f

    def test_default_limit_is_50(self):
        """Default limit is 50 ($top=50)."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages()

        params = mock_transport.get.call_args[1]["params"]
        assert params["$top"] == "50"

    def test_custom_limit(self):
        """Custom limit is forwarded as $top."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(limit=20)

        params = mock_transport.get.call_args[1]["params"]
        assert params["$top"] == "20"

    def test_empty_list(self):
        """list_messages handles empty responses correctly."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        messages = client.list_messages()

        assert len(messages) == 0

    def test_offset_passes_skip_param(self):
        """Non-zero offset is forwarded as $skip."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(offset=100)

        params = mock_transport.get.call_args[1]["params"]
        assert params["$skip"] == "100"

    def test_zero_offset_omits_skip_param(self):
        """Default offset of 0 does not add $skip to the request."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages()

        params = mock_transport.get.call_args[1]["params"]
        assert "$skip" not in params

    def test_filter_metadata_contains_adds_contains_clause(self):
        """A metadata FilterDefinition produces a contains(metadata, ...) expression."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(
            filters=[FilterDefinition(target="metadata", contains="demo-app")],
        )

        params = mock_transport.get.call_args[1]["params"]
        assert "contains(metadata, 'demo-app')" in params["$filter"]

    def test_filter_content_contains_adds_contains_clause(self):
        """A content FilterDefinition produces a contains(content, ...) expression."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(
            filters=[FilterDefinition(target="content", contains="invoice")],
        )

        params = mock_transport.get.call_args[1]["params"]
        assert "contains(content, 'invoice')" in params["$filter"]

    def test_filter_multiple_clauses_joined_with_and(self):
        """Multiple FilterDefinitions are joined with 'and' in $filter."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(
            filters=[
                FilterDefinition(target="metadata", contains="john"),
                FilterDefinition(target="content", contains="user prefers"),
            ],
        )

        params = mock_transport.get.call_args[1]["params"]
        f = params["$filter"]
        assert "contains(metadata, 'john')" in f
        assert "contains(content, 'user prefers')" in f
        assert " and " in f

    def test_filter_combines_with_convenience_filters(self):
        """FilterDefinitions are combined with all convenience filter predicates."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(
            agent_id="a",
            invoker_id="u",
            message_group="g",
            role="USER",
            filters=[FilterDefinition(target="content", contains="hello")],
        )

        params = mock_transport.get.call_args[1]["params"]
        f = params["$filter"]
        assert "agentID eq 'a'" in f
        assert "invokerID eq 'u'" in f
        assert "messageGroup eq 'g'" in f
        assert "role eq 'USER'" in f
        assert "contains(content, 'hello')" in f

    def test_filter_none_does_not_change_behaviour(self):
        """filter=None produces the same $filter as before (no regression)."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {"value": []}

        client.list_messages(agent_id="a", invoker_id="u", filters=None)

        params = mock_transport.get.call_args[1]["params"]
        assert params["$filter"] == "agentID eq 'a' and invokerID eq 'u'"


# ── Admin: Retention Config ───────────────────────────────────────────────────────


class TestRetentionConfig:

    def test_get_retention_config(self):
        """get_retention_config sends GET to the retentionConfig endpoint."""
        client, mock_transport = _make_client()
        mock_transport.get.return_value = {
            "id": 1, "messageDays": 30, "memoryDays": 90,
            "usageLogDays": 180,
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }

        rc = client.get_retention_config()

        assert isinstance(rc, RetentionConfig)
        assert rc.id == 1
        assert rc.message_days == 30
        assert rc.memory_days == 90
        assert rc.usage_log_days == 180
        call_path = mock_transport.get.call_args[0][0]
        assert call_path == RETENTION_CONFIG

    def test_update_retention_config(self):
        """update_retention_config sends PATCH with updated fields."""
        client, mock_transport = _make_client()

        client.update_retention_config(message_days=60)

        mock_transport.patch.assert_called_once()
        call_path = mock_transport.patch.call_args[0][0]
        assert call_path == RETENTION_CONFIG
        payload = mock_transport.patch.call_args[1]["json"]
        assert payload["messageDays"] == 60
        assert "memoryDays" not in payload

    def test_update_retention_config_excludes_none_fields(self):
        """update_retention_config omits None-valued fields from PATCH body."""
        client, mock_transport = _make_client()

        client.update_retention_config(memory_days=90, usage_log_days=180)

        payload = mock_transport.patch.call_args[1]["json"]
        assert "messageDays" not in payload
        assert payload["memoryDays"] == 90
        assert payload["usageLogDays"] == 180


# ── Context manager ───────────────────────────────────────────────────────────


class TestContextManager:

    def test_close_delegates_to_transport(self):
        """close() delegates to the transport's close method."""
        client, mock_transport = _make_client()

        client.close()

        mock_transport.close.assert_called_once()

    def test_context_manager_closes_on_exit(self):
        """Using the client as a context manager closes it on __exit__."""
        transport = MagicMock(spec=HttpTransport)
        client = AgentMemoryClient(transport)

        with client:
            pass

        transport.close.assert_called_once()


# ── Validation ────────────────────────────────────────────────────────────────


class TestMemoryValidation:

    def test_add_memory_raises_for_empty_agent_id(self):
        """add_memory raises AgentMemoryValidationError when agent_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="agent_id"):
            client.add_memory("", "user-1", "content")

    def test_add_memory_raises_for_empty_invoker_id(self):
        """add_memory raises AgentMemoryValidationError when invoker_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="invoker_id"):
            client.add_memory("agent-1", "", "content")

    def test_add_memory_raises_for_empty_content(self):
        """add_memory raises AgentMemoryValidationError when content is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="content"):
            client.add_memory("agent-1", "user-1", "")

    def test_get_memory_raises_for_empty_id(self):
        """get_memory raises AgentMemoryValidationError when memory_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_id"):
            client.get_memory("")

    def test_update_memory_raises_for_empty_id(self):
        """update_memory raises AgentMemoryValidationError when memory_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_id"):
            client.update_memory("", content="new content")

    def test_update_memory_raises_when_no_fields_provided(self):
        """update_memory raises AgentMemoryValidationError when neither content nor metadata is provided."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="At least one"):
            client.update_memory("uuid-123")

    def test_delete_memory_raises_for_empty_id(self):
        """delete_memory raises AgentMemoryValidationError when memory_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_id"):
            client.delete_memory("")

    def test_list_memories_raises_for_zero_limit(self):
        """list_memories raises AgentMemoryValidationError when limit is 0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.list_memories(limit=0)

    def test_list_memories_raises_for_negative_offset(self):
        """list_memories raises AgentMemoryValidationError when offset is negative."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="offset"):
            client.list_memories(offset=-1)


class TestSearchMemoriesValidation:

    def test_raises_for_empty_agent_id(self):
        """search_memories raises AgentMemoryValidationError when agent_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="agent_id"):
            client.search_memories("", "user-1", "what do I know about Python?")

    def test_raises_for_empty_invoker_id(self):
        """search_memories raises AgentMemoryValidationError when invoker_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="invoker_id"):
            client.search_memories("agent-1", "", "what do I know about Python?")

    def test_raises_for_query_too_short(self):
        """search_memories raises AgentMemoryValidationError when query has fewer than 5 chars."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="query"):
            client.search_memories("agent-1", "user-1", "hi")

    def test_raises_for_query_too_long(self):
        """search_memories raises AgentMemoryValidationError when query exceeds 5000 chars."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="query"):
            client.search_memories("agent-1", "user-1", "x" * 5001)

    def test_raises_for_threshold_below_zero(self):
        """search_memories raises AgentMemoryValidationError when threshold < 0.0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="threshold"):
            client.search_memories("a", "u", "valid query here", threshold=-0.1)

    def test_raises_for_threshold_above_one(self):
        """search_memories raises AgentMemoryValidationError when threshold > 1.0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="threshold"):
            client.search_memories("a", "u", "valid query here", threshold=1.1)

    def test_raises_for_limit_zero(self):
        """search_memories raises AgentMemoryValidationError when limit is 0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.search_memories("a", "u", "valid query here", limit=0)

    def test_raises_for_limit_above_fifty(self):
        """search_memories raises AgentMemoryValidationError when limit exceeds 50."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.search_memories("a", "u", "valid query here", limit=51)

    def test_boundary_values_are_accepted(self):
        """search_memories accepts boundary values: 5-char query, threshold 0.0/1.0, limit 1/50."""
        client, mock_transport = _make_client()
        mock_transport.post.return_value = {"value": []}

        client.search_memories("a", "u", "hello", threshold=0.0, limit=1)
        client.search_memories("a", "u", "x" * 5000, threshold=1.0, limit=50)

        assert mock_transport.post.call_count == 2


class TestMessageValidation:

    def test_add_message_raises_for_empty_agent_id(self):
        """add_message raises AgentMemoryValidationError when agent_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="agent_id"):
            client.add_message("", "u", "grp", MessageRole.USER, "hi")

    def test_add_message_raises_for_empty_invoker_id(self):
        """add_message raises AgentMemoryValidationError when invoker_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="invoker_id"):
            client.add_message("a", "", "grp", MessageRole.USER, "hi")

    def test_add_message_raises_for_empty_message_group(self):
        """add_message raises AgentMemoryValidationError when message_group is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_group"):
            client.add_message("a", "u", "", MessageRole.USER, "hi")

    def test_add_message_raises_for_empty_content(self):
        """add_message raises AgentMemoryValidationError when content is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="content"):
            client.add_message("a", "u", "grp", MessageRole.USER, "")

    def test_get_message_raises_for_empty_id(self):
        """get_message raises AgentMemoryValidationError when message_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_id"):
            client.get_message("")

    def test_delete_message_raises_for_empty_id(self):
        """delete_message raises AgentMemoryValidationError when message_id is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_id"):
            client.delete_message("")

    def test_list_messages_raises_for_zero_limit(self):
        """list_messages raises AgentMemoryValidationError when limit is 0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.list_messages(limit=0)

    def test_list_messages_raises_for_negative_offset(self):
        """list_messages raises AgentMemoryValidationError when offset is negative."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="offset"):
            client.list_messages(offset=-1)


class TestRetentionConfigValidation:

    def test_update_raises_when_no_fields_provided(self):
        """update_retention_config raises AgentMemoryValidationError when no fields are provided."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="At least one"):
            client.update_retention_config()

    def test_update_raises_for_negative_message_days(self):
        """update_retention_config raises AgentMemoryValidationError when message_days < 0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_days"):
            client.update_retention_config(message_days=-1)

    def test_update_raises_for_negative_memory_days(self):
        """update_retention_config raises AgentMemoryValidationError when memory_days < 0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_days"):
            client.update_retention_config(memory_days=-1)

    def test_update_raises_for_negative_usage_log_days(self):
        """update_retention_config raises AgentMemoryValidationError when usage_log_days < 0."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="usage_log_days"):
            client.update_retention_config(usage_log_days=-1)

    def test_update_accepts_zero_values(self):
        """update_retention_config accepts 0 as a valid value (disables cleanup)."""
        client, mock_transport = _make_client()

        client.update_retention_config(memory_days=0)

        mock_transport.patch.assert_called_once()


# ── FilterDefinition validation ───────────────────────────────────────────────────


class TestFilterDefinitionValidation:

    def test_list_memories_raises_for_unsupported_target(self):
        """list_memories raises AgentMemoryValidationError for an unknown target."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="target"):
            client.list_memories(
                filters=[FilterDefinition(target="agentID", contains="x")],
            )

    def test_list_memories_raises_for_empty_contains(self):
        """list_memories raises AgentMemoryValidationError when contains is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="contains"):
            client.list_memories(
                filters=[FilterDefinition(target="content", contains="")],
            )

    def test_list_messages_raises_for_unsupported_target(self):
        """list_messages raises AgentMemoryValidationError for an unknown target."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="target"):
            client.list_messages(
                filters=[FilterDefinition(target="role", contains="x")],
            )

    def test_list_messages_raises_for_empty_contains(self):
        """list_messages raises AgentMemoryValidationError when contains is empty."""
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="contains"):
            client.list_messages(
                filters=[FilterDefinition(target="metadata", contains="")],
            )
