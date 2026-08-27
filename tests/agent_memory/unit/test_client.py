"""Unit tests for AgentMemoryClient operations (v1 API)."""

import pytest
from unittest.mock import Mock, patch
from requests import Response
from urllib.parse import parse_qs, urlparse

from sap_cloud_sdk.agent_memory._endpoints import (
    MEMORIES,
    MEMORY_SEARCH,
    MESSAGES,
    RETENTION_CONFIG,
)
from sap_cloud_sdk.agent_memory._models import (
    AccessStrategy,
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory import create_client, FilterDefinition
from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryConfigError,
    AgentMemoryValidationError,
)
from sap_cloud_sdk.core._http_client import HttpClient


def _parse_call_params(call_args) -> dict:
    """Extract query-string params from the URL path in a mock_http.request call."""
    path = call_args[0][1]
    parsed = urlparse(path)
    if not parsed.query:
        return {}
    return {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}


def _make_response(status=200, json_data=None, text="", content=b"..."):
    resp = Mock(spec=Response)
    resp.status_code = status
    resp.text = text
    resp.content = content if status != 204 else b""
    resp.ok = 200 <= status < 300
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


def _make_client() -> tuple[AgentMemoryClient, Mock]:
    """Return an AgentMemoryClient with a mocked HttpClient (PROVIDER strategy)."""
    http = Mock(spec=HttpClient)
    http.request.return_value = _make_response(200)
    client = AgentMemoryClient(http, access_strategy=AccessStrategy.PROVIDER)
    return client, http


def _make_subscriber_client(
    tenant: str = "default-sub",
) -> tuple[AgentMemoryClient, Mock]:
    """Return a client with SUBSCRIBER strategy and a mocked HttpClient."""
    http = Mock(spec=HttpClient)
    http.request.return_value = _make_response(200)
    client = AgentMemoryClient(
        http,
        access_strategy=AccessStrategy.SUBSCRIBER,
        tenant=tenant,
    )
    return client, http


# ── create_client factory ─────────────────────────────────────────────────────


class TestCreateClient:

    def test_uses_provided_config(self):
        """Factory with explicit config creates a client successfully."""
        config = AgentMemoryConfig(base_url="http://localhost:3000")
        with patch("sap_cloud_sdk.agent_memory._build_agent_memory_http") as mock_build:
            mock_build.return_value = Mock(spec=HttpClient)
            client = create_client(config=config, access_strategy=AccessStrategy.PROVIDER)
        assert isinstance(client, AgentMemoryClient)
        assert client._http is not None

    def test_subscriber_strategy_loads_tenant_binding(self, monkeypatch):
        """Factory with SUBSCRIBER loads the tenant binding."""
        import json
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_APPLICATION_URL",
            "http://acme.memory.example.com",
        )
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_UAA",
            json.dumps({"url": "http://acme.auth.example.com", "clientid": "c", "clientsecret": "s"}),
        )
        with patch("sap_cloud_sdk.agent_memory._build_agent_memory_http") as mock_build:
            mock_build.return_value = Mock(spec=HttpClient)
            client = create_client(
                access_strategy=AccessStrategy.SUBSCRIBER,
                tenant="acme-corp",
            )
        assert isinstance(client, AgentMemoryClient)
        assert client._http is not None

    def test_provider_strategy_loads_default_binding(self, monkeypatch):
        """Factory with PROVIDER loads the default binding."""
        import json
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL",
            "http://memory.example.com",
        )
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA",
            json.dumps({"url": "http://auth.example.com", "clientid": "c", "clientsecret": "s"}),
        )
        with patch("sap_cloud_sdk.agent_memory._build_agent_memory_http") as mock_build:
            mock_build.return_value = Mock(spec=HttpClient)
            client = create_client(access_strategy=AccessStrategy.PROVIDER)
        assert isinstance(client, AgentMemoryClient)
        assert client._http is not None


# ── Access strategy and per-tenant transport routing ─────────────────────────


class TestAccessStrategy:

    # ── Construction-time validation ───────────────────────────────────────────

    def test_subscriber_without_tenant_raises_at_construction(self):
        """SUBSCRIBER without tenant raises AgentMemoryValidationError at construction."""
        http = Mock(spec=HttpClient)
        with pytest.raises(AgentMemoryValidationError, match="tenant"):
            AgentMemoryClient(http, access_strategy=AccessStrategy.SUBSCRIBER)

    def test_subscriber_with_tenant_constructs_successfully(self):
        """SUBSCRIBER with tenant constructs without error."""
        client, _ = _make_subscriber_client("acme")
        assert client._http is not None

    def test_provider_constructs_without_tenant(self):
        """PROVIDER constructs without tenant."""
        client, _ = _make_client()
        assert client._http is not None

    # ── Transport routing ──────────────────────────────────────────────────────

    def test_client_default_subscriber_uses_subscriber_transport(self):
        """Client with SUBSCRIBER default uses the provided HttpClient."""
        client, mock_http = _make_subscriber_client("acme")
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "m1", "agentID": "a", "invokerID": "u", "content": "x",
        })
        client.add_memory("a", "u", "x")
        mock_http.request.assert_called_once()

    def test_provider_only_uses_provider_transport(self):
        """PROVIDER uses the provided HttpClient."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "m1", "agentID": "a", "invokerID": "u", "content": "x",
        })
        client.add_memory("a", "u", "x")
        mock_http.request.assert_called_once()


# ── Memory CRUD operations ────────────────────────────────────────────────────


class TestMemoryCRUD:

    def test_add_memory_posts_correct_payload(self):
        """add_memory sends required and optional fields in the POST body."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "mem-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "content": "some memory",
            "createType": "DIRECT",
        })

        memory = client.add_memory("agent-a", "user-b", "some memory")

        assert isinstance(memory, Memory)
        assert memory.id == "mem-1"
        call = mock_http.request.call_args
        assert call[0][0] == "POST"
        assert call[1]["json"]["agentID"] == "agent-a"
        assert call[1]["json"]["invokerID"] == "user-b"
        assert call[1]["json"]["content"] == "some memory"

    def test_add_memory_with_metadata(self):
        """Optional metadata is included in the POST body when provided."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "x",
        })

        client.add_memory("a", "u", "x", metadata={"key": "val"})

        assert mock_http.request.call_args[1]["json"]["metadata"] == {"key": "val"}

    def test_add_memory_excludes_none_optionals(self):
        """None-valued optional fields are omitted from the POST body."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "x",
        })

        client.add_memory("a", "u", "x")

        payload = mock_http.request.call_args[1]["json"]
        assert "metadata" not in payload
        assert "createType" not in payload

    def test_add_memory_posts_to_memories_endpoint(self):
        """add_memory sends the POST to the MEMORIES endpoint."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "x",
        })

        client.add_memory("a", "u", "x")

        assert mock_http.request.call_args[0][0] == "POST"
        assert mock_http.request.call_args[0][1] == MEMORIES

    def test_get_memory_calls_get_with_memory_id(self):
        """get_memory constructs the correct path with the memory ID."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "mem-1", "agentID": "a", "invokerID": "u", "content": "hello",
        })

        memory = client.get_memory("mem-1")

        assert memory.id == "mem-1"
        assert mock_http.request.call_args[0][0] == "GET"
        assert mock_http.request.call_args[0][1] == f"{MEMORIES}(mem-1)"

    def test_update_memory_calls_patch(self):
        """update_memory sends a PATCH with the updated fields."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.update_memory("mem-1", content="updated")

        assert mock_http.request.call_args[0][0] == "PATCH"
        assert mock_http.request.call_args[1]["json"]["content"] == "updated"

    def test_update_memory_excludes_none_fields(self):
        """update_memory omits None-valued optional fields from the PATCH body."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.update_memory("mem-1", content="x")

        assert "metadata" not in mock_http.request.call_args[1]["json"]

    def test_update_memory_with_metadata_only(self):
        """update_memory supports updating metadata without content."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.update_memory("mem-1", metadata={"key": "new-meta"})

        payload = mock_http.request.call_args[1]["json"]
        assert payload["metadata"] == {"key": "new-meta"}
        assert "content" not in payload

    def test_delete_memory_calls_delete(self):
        """delete_memory sends a DELETE to the correct path."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.delete_memory("mem-1")

        assert mock_http.request.call_args[0][0] == "DELETE"
        assert mock_http.request.call_args[0][1] == f"{MEMORIES}(mem-1)"


# ── Memory listing ────────────────────────────────────────────────────────────


class TestListMemories:

    def test_returns_list_of_memories(self):
        """list_memories returns a list of Memory objects."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "value": [
                {"id": "m1", "agentID": "a", "invokerID": "u", "content": "memory 1"},
            ],
        })

        memories = client.list_memories(agent_id="a", invoker_id="u")

        assert len(memories) == 1
        assert isinstance(memories[0], Memory)

    def test_passes_filter_for_agent_and_invoker(self):
        """Convenience agent_id/invoker_id args are converted to $filter."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(agent_id="agent-x", invoker_id="user-y")

        params = _parse_call_params(mock_http.request.call_args)
        assert "agentID eq 'agent-x'" in params["$filter"]
        assert "invokerID eq 'user-y'" in params["$filter"]

    def test_default_limit_is_50(self):
        """Default limit is 50 ($top=50)."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories()

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$top"] == "50"

    def test_custom_limit(self):
        """Custom limit is forwarded as $top."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(limit=5)

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$top"] == "5"

    def test_empty_list(self):
        """list_memories handles empty responses correctly."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        memories = client.list_memories()

        assert len(memories) == 0

    def test_offset_passes_skip_param(self):
        """Non-zero offset is forwarded as $skip."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(offset=50)

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$skip"] == "50"

    def test_zero_offset_omits_skip_param(self):
        """Default offset of 0 does not add $skip to the request."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories()

        params = _parse_call_params(mock_http.request.call_args)
        assert "$skip" not in params

    def test_filter_metadata_contains_adds_contains_clause(self):
        """A metadata FilterDefinition produces a contains(metadata, ...) expression."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(
            filters=[FilterDefinition(target="metadata", contains="john")],
        )

        params = _parse_call_params(mock_http.request.call_args)
        assert "contains(metadata, 'john')" in params["$filter"]

    def test_filter_content_contains_adds_contains_clause(self):
        """A content FilterDefinition produces a contains(content, ...) expression."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(
            filters=[FilterDefinition(target="content", contains="dark mode")],
        )

        params = _parse_call_params(mock_http.request.call_args)
        assert "contains(content, 'dark mode')" in params["$filter"]

    def test_filter_multiple_clauses_joined_with_and(self):
        """Multiple FilterDefinitions are joined with 'and' in $filter."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(
            filters=[
                FilterDefinition(target="metadata", contains="john"),
                FilterDefinition(target="content", contains="user prefers"),
            ],
        )

        params = _parse_call_params(mock_http.request.call_args)
        f = params["$filter"]
        assert "contains(metadata, 'john')" in f
        assert "contains(content, 'user prefers')" in f
        assert " and " in f

    def test_filter_combines_with_agent_and_invoker_filters(self):
        """FilterDefinitions are combined with agent_id/invoker_id eq predicates."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(
            agent_id="my-agent",
            invoker_id="user-1",
            filters=[FilterDefinition(target="content", contains="dark mode")],
        )

        params = _parse_call_params(mock_http.request.call_args)
        f = params["$filter"]
        assert "agentID eq 'my-agent'" in f
        assert "invokerID eq 'user-1'" in f
        assert "contains(content, 'dark mode')" in f

    def test_filter_none_does_not_change_behaviour(self):
        """filter=None produces the same $filter as before (no regression)."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_memories(agent_id="a", invoker_id="u", filters=None)

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$filter"] == "agentID eq 'a' and invokerID eq 'u'"


class TestCountMemories:

    def test_returns_count_from_response(self):
        """count_memories returns the @odata.count value."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": [], "@odata.count": 42})

        total = client.count_memories(agent_id="a", invoker_id="u")

        assert total == 42

    def test_sends_top_0_and_count_true(self):
        """count_memories uses $top=0 and $count=true."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": [], "@odata.count": 0})

        client.count_memories()

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$top"] == "0"
        assert params["$count"] == "true"

    def test_passes_filter_when_agent_and_invoker_provided(self):
        """count_memories forwards agent_id and invoker_id as $filter."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": [], "@odata.count": 3})

        client.count_memories(agent_id="agt", invoker_id="usr")

        params = _parse_call_params(mock_http.request.call_args)
        assert "agentID eq 'agt'" in params["$filter"]
        assert "invokerID eq 'usr'" in params["$filter"]

    def test_returns_zero_when_count_missing(self):
        """count_memories returns 0 when count is absent from response."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        total = client.count_memories()

        assert total == 0


# ── Memory search ─────────────────────────────────────────────────────────────


class TestSearchMemories:

    def test_returns_results_in_api_order(self):
        """search_memories returns results in the order returned by the API."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "value": [
                {"id": "m1", "agentID": "a", "invokerID": "u", "content": "first", "similarity": 0.5},
                {"id": "m2", "agentID": "a", "invokerID": "u", "content": "second", "similarity": 0.9},
            ]
        })

        results = client.search_memories("a", "u", "test query")

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].similarity == 0.5
        assert results[1].similarity == 0.9

    def test_posts_correct_payload(self):
        """search_memories sends the correct payload to the search endpoint."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.search_memories("agent-a", "user-b", "my query", threshold=0.7, limit=5)

        assert mock_http.request.call_args[0][0] == "POST"
        assert mock_http.request.call_args[0][1] == MEMORY_SEARCH
        payload = mock_http.request.call_args[1]["json"]
        assert payload["agentID"] == "agent-a"
        assert payload["invokerID"] == "user-b"
        assert payload["query"] == "my query"
        assert payload["threshold"] == 0.7
        assert payload["top"] == 5

    def test_empty_results(self):
        """search_memories handles empty search results."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        results = client.search_memories("a", "u", "empty query")

        assert len(results) == 0

    def test_uses_default_threshold_and_limit(self):
        """search_memories uses default threshold=0.6 and limit=10."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.search_memories("a", "u", "query")

        payload = mock_http.request.call_args[1]["json"]
        assert payload["threshold"] == 0.6
        assert payload["top"] == 10
        assert "skip" not in payload


# ── Message operations ────────────────────────────────────────────────────────


class TestMessageCRUD:

    def test_add_message_posts_correct_payload(self):
        """add_message sends required fields in the POST body."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "msg-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "messageGroup": "conv-1",
            "role": "USER",
            "content": "Hello!",
        })

        message = client.add_message(
            "agent-a", "user-b", "conv-1", MessageRole.USER, "Hello!",
        )

        assert isinstance(message, Message)
        assert message.id == "msg-1"
        assert message.role == "USER"
        payload = mock_http.request.call_args[1]["json"]
        assert payload["agentID"] == "agent-a"
        assert payload["invokerID"] == "user-b"
        assert payload["messageGroup"] == "conv-1"
        assert payload["role"] == "USER"
        assert payload["content"] == "Hello!"

    def test_add_message_posts_to_messages_endpoint(self):
        """add_message sends the POST to the MESSAGES endpoint."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        })

        client.add_message("a", "u", "g", MessageRole.USER, "hi")

        assert mock_http.request.call_args[0][0] == "POST"
        assert mock_http.request.call_args[0][1] == MESSAGES

    def test_add_message_with_metadata(self):
        """Optional metadata is included when provided."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
            "metadata": {"key": "val"},
        })

        client.add_message("a", "u", "g", MessageRole.USER, "hi", metadata={"key": "val"})

        assert mock_http.request.call_args[1]["json"]["metadata"] == {"key": "val"}

    def test_add_message_excludes_none_metadata(self):
        """None-valued metadata is omitted from the POST body."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        })

        client.add_message("a", "u", "g", MessageRole.USER, "hi")

        assert "metadata" not in mock_http.request.call_args[1]["json"]

    def test_get_message_calls_get_with_message_id(self):
        """get_message constructs the correct path with the message ID."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        })

        message = client.get_message("msg-1")

        assert message.id == "msg-1"
        assert mock_http.request.call_args[0][0] == "GET"
        assert mock_http.request.call_args[0][1] == f"{MESSAGES}(msg-1)"

    def test_delete_message_calls_delete(self):
        """delete_message sends a DELETE to the correct path."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.delete_message("msg-1")

        assert mock_http.request.call_args[0][0] == "DELETE"
        assert mock_http.request.call_args[0][1] == f"{MESSAGES}(msg-1)"


# ── Message listing ───────────────────────────────────────────────────────────


class TestListMessages:

    def test_returns_list_of_messages(self):
        """list_messages returns a list of Message objects."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "value": [
                {
                    "id": "msg-1", "agentID": "a", "invokerID": "u",
                    "messageGroup": "g", "role": "USER", "content": "hi",
                },
            ],
        })

        messages = client.list_messages(agent_id="a", invoker_id="u")

        assert len(messages) == 1
        assert isinstance(messages[0], Message)

    def test_passes_convenience_filters(self):
        """Convenience filters are converted to $filter."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(
            agent_id="a", invoker_id="u",
            message_group="conv-1", role="USER",
        )

        params = _parse_call_params(mock_http.request.call_args)
        f = params["$filter"]
        assert "agentID eq 'a'" in f
        assert "invokerID eq 'u'" in f
        assert "messageGroup eq 'conv-1'" in f
        assert "role eq 'USER'" in f

    def test_default_limit_is_50(self):
        """Default limit is 50 ($top=50)."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages()

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$top"] == "50"

    def test_custom_limit(self):
        """Custom limit is forwarded as $top."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(limit=20)

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$top"] == "20"

    def test_empty_list(self):
        """list_messages handles empty responses correctly."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        messages = client.list_messages()

        assert len(messages) == 0

    def test_offset_passes_skip_param(self):
        """Non-zero offset is forwarded as $skip."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(offset=100)

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$skip"] == "100"

    def test_zero_offset_omits_skip_param(self):
        """Default offset of 0 does not add $skip to the request."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages()

        params = _parse_call_params(mock_http.request.call_args)
        assert "$skip" not in params

    def test_filter_metadata_contains_adds_contains_clause(self):
        """A metadata FilterDefinition produces a contains(metadata, ...) expression."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(
            filters=[FilterDefinition(target="metadata", contains="demo-app")],
        )

        params = _parse_call_params(mock_http.request.call_args)
        assert "contains(metadata, 'demo-app')" in params["$filter"]

    def test_filter_content_contains_adds_contains_clause(self):
        """A content FilterDefinition produces a contains(content, ...) expression."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(
            filters=[FilterDefinition(target="content", contains="invoice")],
        )

        params = _parse_call_params(mock_http.request.call_args)
        assert "contains(content, 'invoice')" in params["$filter"]

    def test_filter_multiple_clauses_joined_with_and(self):
        """Multiple FilterDefinitions are joined with 'and' in $filter."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(
            filters=[
                FilterDefinition(target="metadata", contains="john"),
                FilterDefinition(target="content", contains="user prefers"),
            ],
        )

        params = _parse_call_params(mock_http.request.call_args)
        f = params["$filter"]
        assert "contains(metadata, 'john')" in f
        assert "contains(content, 'user prefers')" in f
        assert " and " in f

    def test_filter_combines_with_convenience_filters(self):
        """FilterDefinitions are combined with all convenience filter predicates."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(
            agent_id="a",
            invoker_id="u",
            message_group="g",
            role="USER",
            filters=[FilterDefinition(target="content", contains="hello")],
        )

        params = _parse_call_params(mock_http.request.call_args)
        f = params["$filter"]
        assert "agentID eq 'a'" in f
        assert "invokerID eq 'u'" in f
        assert "messageGroup eq 'g'" in f
        assert "role eq 'USER'" in f
        assert "contains(content, 'hello')" in f

    def test_filter_none_does_not_change_behaviour(self):
        """filter=None produces the same $filter as before (no regression)."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.list_messages(agent_id="a", invoker_id="u", filters=None)

        params = _parse_call_params(mock_http.request.call_args)
        assert params["$filter"] == "agentID eq 'a' and invokerID eq 'u'"


# ── Admin: Retention Config ───────────────────────────────────────────────────────


class TestRetentionConfig:

    def test_get_retention_config(self):
        """get_retention_config sends GET to the retentionConfig endpoint."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={
            "id": 1, "messageDays": 30, "memoryDays": 90,
            "usageLogDays": 180,
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        })

        rc = client.get_retention_config()

        assert isinstance(rc, RetentionConfig)
        assert rc.id == 1
        assert rc.message_days == 30
        assert rc.memory_days == 90
        assert rc.usage_log_days == 180
        assert mock_http.request.call_args[0][0] == "GET"
        assert mock_http.request.call_args[0][1] == RETENTION_CONFIG

    def test_update_retention_config(self):
        """update_retention_config sends PATCH with updated fields."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.update_retention_config(message_days=60)

        assert mock_http.request.call_args[0][0] == "PATCH"
        assert mock_http.request.call_args[0][1] == RETENTION_CONFIG
        payload = mock_http.request.call_args[1]["json"]
        assert payload["messageDays"] == 60
        assert "memoryDays" not in payload

    def test_update_retention_config_excludes_none_fields(self):
        """update_retention_config omits None-valued fields from PATCH body."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.update_retention_config(memory_days=90, usage_log_days=180)

        payload = mock_http.request.call_args[1]["json"]
        assert "messageDays" not in payload
        assert payload["memoryDays"] == 90
        assert payload["usageLogDays"] == 180


# ── Context manager ───────────────────────────────────────────────────────────


class TestContextManager:

    def test_close_delegates_to_http(self):
        """close() delegates to the HttpClient's close method."""
        client, mock_http = _make_client()

        client.close()

        mock_http.close.assert_called_once()

    def test_context_manager_closes_on_exit(self):
        """Using the client as a context manager closes it on __exit__."""
        http = Mock(spec=HttpClient)
        http.request.return_value = _make_response(200)
        client = AgentMemoryClient(http, access_strategy=AccessStrategy.PROVIDER)

        with client:
            pass

        http.close.assert_called_once()


# ── Validation ────────────────────────────────────────────────────────────────


class TestMemoryValidation:

    def test_add_memory_raises_for_empty_agent_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="agent_id"):
            client.add_memory("", "user-1", "content")

    def test_add_memory_raises_for_empty_invoker_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="invoker_id"):
            client.add_memory("agent-1", "", "content")

    def test_add_memory_raises_for_empty_content(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="content"):
            client.add_memory("agent-1", "user-1", "")

    def test_get_memory_raises_for_empty_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_id"):
            client.get_memory("")

    def test_update_memory_raises_for_empty_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_id"):
            client.update_memory("", content="new content")

    def test_update_memory_raises_when_no_fields_provided(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="At least one"):
            client.update_memory("uuid-123")

    def test_delete_memory_raises_for_empty_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_id"):
            client.delete_memory("")

    def test_list_memories_raises_for_zero_limit(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.list_memories(limit=0)

    def test_list_memories_raises_for_negative_offset(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="offset"):
            client.list_memories(offset=-1)


class TestSearchMemoriesValidation:

    def test_raises_for_empty_agent_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="agent_id"):
            client.search_memories("", "user-1", "what do I know about Python?")

    def test_raises_for_empty_invoker_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="invoker_id"):
            client.search_memories("agent-1", "", "what do I know about Python?")

    def test_raises_for_query_too_short(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="query"):
            client.search_memories("agent-1", "user-1", "hi")

    def test_raises_for_query_too_long(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="query"):
            client.search_memories("agent-1", "user-1", "x" * 5001)

    def test_raises_for_threshold_below_zero(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="threshold"):
            client.search_memories("a", "u", "valid query here", threshold=-0.1)

    def test_raises_for_threshold_above_one(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="threshold"):
            client.search_memories("a", "u", "valid query here", threshold=1.1)

    def test_raises_for_limit_zero(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.search_memories("a", "u", "valid query here", limit=0)

    def test_raises_for_limit_above_fifty(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.search_memories("a", "u", "valid query here", limit=51)

    def test_boundary_values_are_accepted(self):
        """search_memories accepts boundary values: 5-char query, threshold 0.0/1.0, limit 1/50."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(200, json_data={"value": []})

        client.search_memories("a", "u", "hello", threshold=0.0, limit=1)
        client.search_memories("a", "u", "x" * 5000, threshold=1.0, limit=50)

        assert mock_http.request.call_count == 2


class TestMessageValidation:

    def test_add_message_raises_for_empty_agent_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="agent_id"):
            client.add_message("", "u", "grp", MessageRole.USER, "hi")

    def test_add_message_raises_for_empty_invoker_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="invoker_id"):
            client.add_message("a", "", "grp", MessageRole.USER, "hi")

    def test_add_message_raises_for_empty_message_group(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_group"):
            client.add_message("a", "u", "", MessageRole.USER, "hi")

    def test_add_message_raises_for_empty_content(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="content"):
            client.add_message("a", "u", "grp", MessageRole.USER, "")

    def test_get_message_raises_for_empty_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_id"):
            client.get_message("")

    def test_delete_message_raises_for_empty_id(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_id"):
            client.delete_message("")

    def test_list_messages_raises_for_zero_limit(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="limit"):
            client.list_messages(limit=0)

    def test_list_messages_raises_for_negative_offset(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="offset"):
            client.list_messages(offset=-1)


class TestRetentionConfigValidation:

    def test_update_raises_when_no_fields_provided(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="At least one"):
            client.update_retention_config()

    def test_update_raises_for_negative_message_days(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="message_days"):
            client.update_retention_config(message_days=-1)

    def test_update_raises_for_negative_memory_days(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="memory_days"):
            client.update_retention_config(memory_days=-1)

    def test_update_raises_for_negative_usage_log_days(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="usage_log_days"):
            client.update_retention_config(usage_log_days=-1)

    def test_update_accepts_zero_values(self):
        """update_retention_config accepts 0 as a valid value (disables cleanup)."""
        client, mock_http = _make_client()
        mock_http.request.return_value = _make_response(204, content=b"")

        client.update_retention_config(memory_days=0)

        mock_http.request.assert_called_once()


# ── FilterDefinition validation ───────────────────────────────────────────────────


class TestFilterDefinitionValidation:

    def test_list_memories_raises_for_unsupported_target(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="target"):
            client.list_memories(
                filters=[FilterDefinition(target="agentID", contains="x")],
            )

    def test_list_memories_raises_for_empty_contains(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="contains"):
            client.list_memories(
                filters=[FilterDefinition(target="content", contains="")],
            )

    def test_list_messages_raises_for_unsupported_target(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="target"):
            client.list_messages(
                filters=[FilterDefinition(target="role", contains="x")],
            )

    def test_list_messages_raises_for_empty_contains(self):
        client, _ = _make_client()
        with pytest.raises(AgentMemoryValidationError, match="contains"):
            client.list_messages(
                filters=[FilterDefinition(target="metadata", contains="")],
            )
