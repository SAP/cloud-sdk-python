"""Unit tests for Agent Memory data models (v1 API)."""

from sap_cloud_sdk.agent_memory._models import (
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)


# ── Memory ────────────────────────────────────────────────────────────────────


class TestMemory:

    def test_from_dict_maps_known_fields(self):
        """All known API fields are mapped to model attributes."""
        data = {
            "id": "mem-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "content": "The user prefers dark mode.",
            "metadata": {"key": "val"},
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }
        memory = Memory.from_dict(data)

        assert memory.id == "mem-1"
        assert memory.agent_id == "agent-a"
        assert memory.invoker_id == "user-b"
        assert memory.content == "The user prefers dark mode."
        assert memory.metadata == {"key": "val"}
        assert memory.create_timestamp == "2025-01-01T00:00:00Z"
        assert memory.update_timestamp == "2025-01-02T00:00:00Z"

    def test_from_dict_optional_fields_default_to_none(self):
        """Optional fields default to None when absent."""
        data = {"id": "m1", "agentID": "a", "invokerID": "u", "content": "hello"}
        memory = Memory.from_dict(data)
        assert memory.metadata is None
        assert memory.create_timestamp is None
        assert memory.update_timestamp is None

    def test_from_dict_parses_string_metadata(self):
        """String metadata is parsed as JSON."""
        data = {"id": "m1", "agentID": "a", "invokerID": "u", "content": "x",
                "metadata": '{"key": "val"}'}
        memory = Memory.from_dict(data)
        assert memory.metadata == {"key": "val"}

    def test_from_dict_handles_invalid_json_metadata(self):
        """Invalid JSON metadata is wrapped in a raw dict."""
        data = {"id": "m1", "agentID": "a", "invokerID": "u", "content": "x",
                "metadata": "not-json"}
        memory = Memory.from_dict(data)
        assert memory.metadata == {"raw": "not-json"}

    def test_from_dict_empty_dict_uses_defaults(self):
        """An empty dict produces safe defaults."""
        memory = Memory.from_dict({})
        assert memory.id == ""
        assert memory.content == ""
        assert memory.metadata is None

    def test_to_dict_shape(self):
        """to_dict outputs all fields with camelCase keys."""
        memory = Memory(
            id="m1", agent_id="a", invoker_id="u", content="hello",
            create_timestamp="2025-01-01T00:00:00Z",
            update_timestamp="2025-01-02T00:00:00Z",
        )
        d = memory.to_dict()
        assert d == {
            "id": "m1",
            "agentID": "a",
            "invokerID": "u",
            "content": "hello",
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }

    def test_to_dict_includes_metadata_when_set(self):
        """to_dict includes metadata when set."""
        memory = Memory(
            id="m1", agent_id="a", invoker_id="u", content="hello",
            metadata={"k": "v"},
        )
        d = memory.to_dict()
        assert d["metadata"] == {"k": "v"}

    def test_to_dict_omits_metadata_when_none(self):
        """to_dict omits metadata when None."""
        memory = Memory(id="m1", agent_id="a", invoker_id="u", content="hello")
        d = memory.to_dict()
        assert "metadata" not in d

    def test_round_trip(self):
        """from_dict(to_dict(m)) reproduces the original object."""
        data = {
            "id": "m1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "content": "The user prefers dark mode.",
            "metadata": {"key": "val"},
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }
        memory = Memory.from_dict(data)
        assert Memory.from_dict(memory.to_dict()) == memory


# ── SearchResult ──────────────────────────────────────────────────────────────


class TestSearchResult:

    def test_from_dict_maps_all_fields(self):
        """All known fields including similarity score are mapped correctly."""
        data = {
            "id": "m1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "content": "user preference",
            "similarity": 0.92,
            "metadata": {"source": "meta"},
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }
        result = SearchResult.from_dict(data)

        assert result.id == "m1"
        assert result.agent_id == "agent-a"
        assert result.similarity == 0.92
        assert result.metadata == {"source": "meta"}
        assert result.create_timestamp == "2025-01-01T00:00:00Z"
        assert result.update_timestamp == "2025-01-02T00:00:00Z"

    def test_from_dict_similarity_defaults_to_none(self):
        """Similarity defaults to None when absent."""
        data = {"id": "m1", "agentID": "a", "invokerID": "u", "content": "x"}
        result = SearchResult.from_dict(data)
        assert result.similarity is None

    def test_to_dict_includes_similarity(self):
        """to_dict includes the similarity score."""
        result = SearchResult(
            id="m1", agent_id="a", invoker_id="u", content="x",
            similarity=0.85,
        )
        d = result.to_dict()
        assert d["similarity"] == 0.85

    def test_round_trip(self):
        """from_dict(to_dict(r)) reproduces the original object."""
        data = {
            "id": "m1",
            "agentID": "a",
            "invokerID": "u",
            "content": "user preference",
            "similarity": 0.92,
            "metadata": {"source": "meta"},
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }
        result = SearchResult.from_dict(data)
        assert SearchResult.from_dict(result.to_dict()) == result


# ── Message ───────────────────────────────────────────────────────────────────


class TestMessage:

    def test_from_dict_maps_known_fields(self):
        """All known message fields are mapped correctly."""
        data = {
            "id": "msg-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "messageGroup": "conv-1",
            "role": "USER",
            "content": "Hello!",
            "metadata": {"key": "val"},
            "createTimestamp": "2025-01-01T00:00:00Z",
        }
        msg = Message.from_dict(data)

        assert msg.id == "msg-1"
        assert msg.agent_id == "agent-a"
        assert msg.invoker_id == "user-b"
        assert msg.message_group == "conv-1"
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello!"
        assert msg.metadata == {"key": "val"}
        assert msg.create_timestamp == "2025-01-01T00:00:00Z"

    def test_from_dict_parses_string_metadata(self):
        """String metadata is parsed as JSON."""
        data = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
            "metadata": '{"key": "val"}',
        }
        msg = Message.from_dict(data)
        assert msg.metadata == {"key": "val"}

    def test_from_dict_handles_invalid_json_metadata(self):
        """Invalid JSON metadata is wrapped in a raw dict."""
        data = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
            "metadata": "not-json",
        }
        msg = Message.from_dict(data)
        assert msg.metadata == {"raw": "not-json"}

    def test_from_dict_handles_missing_metadata(self):
        """Missing metadata defaults to None."""
        data = {
            "id": "msg-1", "agentID": "a", "invokerID": "u",
            "messageGroup": "g", "role": "USER", "content": "hi",
        }
        msg = Message.from_dict(data)
        assert msg.metadata is None

    def test_from_dict_empty_dict_uses_defaults(self):
        """An empty dict produces safe defaults."""
        msg = Message.from_dict({})
        assert msg.id == ""
        assert msg.message_group == ""
        assert msg.role is None
        assert msg.metadata is None

    def test_to_dict_shape(self):
        """to_dict outputs all fields with camelCase keys."""
        msg = Message(
            id="msg-1", agent_id="a", invoker_id="u",
            message_group="g", role=MessageRole.USER, content="hi",
            create_timestamp="2025-01-01T00:00:00Z",
        )
        d = msg.to_dict()
        assert d == {
            "id": "msg-1",
            "agentID": "a",
            "invokerID": "u",
            "messageGroup": "g",
            "role": "USER",
            "content": "hi",
            "createTimestamp": "2025-01-01T00:00:00Z",
        }

    def test_to_dict_includes_metadata_when_set(self):
        """to_dict includes metadata when set."""
        msg = Message(
            id="msg-1", agent_id="a", invoker_id="u",
            message_group="g", role=MessageRole.USER, content="hi",
            metadata={"key": "val"},
        )
        d = msg.to_dict()
        assert d["metadata"] == {"key": "val"}

    def test_to_dict_omits_none_role_and_metadata(self):
        """to_dict omits role and metadata when None."""
        msg = Message(
            id="msg-1", agent_id="a", invoker_id="u",
            message_group="g", content="hi",
        )
        d = msg.to_dict()
        assert "role" not in d
        assert "metadata" not in d

    def test_round_trip(self):
        """from_dict(to_dict(m)) reproduces the original object."""
        data = {
            "id": "msg-1",
            "agentID": "agent-a",
            "invokerID": "user-b",
            "messageGroup": "conv-1",
            "role": "USER",
            "content": "Hello!",
            "metadata": {"key": "val"},
            "createTimestamp": "2025-01-01T00:00:00Z",
        }
        msg = Message.from_dict(data)
        assert Message.from_dict(msg.to_dict()) == msg


# ── Enums ─────────────────────────────────────────────────────────────────────


class TestEnums:

    def test_message_role_values(self):
        """MessageRole enum has the expected members."""
        assert MessageRole.USER == "USER"
        assert MessageRole.ASSISTANT == "ASSISTANT"
        assert MessageRole.SYSTEM == "SYSTEM"
        assert MessageRole.TOOL == "TOOL"

    def test_message_role_is_str(self):
        """MessageRole values can be used as strings."""
        assert isinstance(MessageRole.USER, str)
        assert MessageRole.USER == "USER"


# ── RetentionConfig ─────────────────────────────────────────────────────────────


class TestRetentionConfig:

    def test_from_dict_maps_known_fields(self):
        """All known retention config fields are mapped correctly."""
        data = {
            "id": 1,
            "messageDays": 30,
            "memoryDays": 90,
            "usageLogDays": 180,
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }
        rc = RetentionConfig.from_dict(data)

        assert rc.id == 1
        assert rc.message_days == 30
        assert rc.memory_days == 90
        assert rc.usage_log_days == 180
        assert rc.create_timestamp == "2025-01-01T00:00:00Z"
        assert rc.update_timestamp == "2025-01-02T00:00:00Z"

    def test_from_dict_optional_fields_default_to_none(self):
        """Optional fields default to None when absent."""
        data = {"id": 1}
        rc = RetentionConfig.from_dict(data)
        assert rc.message_days is None
        assert rc.memory_days is None
        assert rc.usage_log_days is None
        assert rc.create_timestamp is None
        assert rc.update_timestamp is None

    def test_from_dict_empty_dict_uses_defaults(self):
        """An empty dict produces safe defaults."""
        rc = RetentionConfig.from_dict({})
        assert rc.id is None
        assert rc.message_days is None

    def test_round_trip(self):
        """from_dict(to_dict(rc)) reproduces the original object."""
        data = {
            "id": 1,
            "messageDays": 30,
            "memoryDays": 90,
            "usageLogDays": 180,
            "createTimestamp": "2025-01-01T00:00:00Z",
            "updateTimestamp": "2025-01-02T00:00:00Z",
        }
        rc = RetentionConfig.from_dict(data)
        assert RetentionConfig.from_dict(rc.to_dict()) == rc
