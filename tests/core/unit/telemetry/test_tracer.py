"""Tests for tracer context overlay utilities."""

import pytest
from unittest.mock import patch, MagicMock, call
from contextlib import contextmanager

from opentelemetry.trace import Status, StatusCode, SpanKind

from cloud_sdk_python.core.telemetry.tracer import (
    context_overlay,
    get_current_span,
    add_span_attribute,
    chat_span,
    execute_tool_span,
    invoke_agent_span,
)
from cloud_sdk_python.core.telemetry.genai_operation import GenAIOperation


class TestContextOverlay:
    """Test suite for context_overlay function."""

    def test_context_overlay_basic(self):
        """Test basic context overlay usage."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with context_overlay(GenAIOperation.CHAT) as span:
                assert span is mock_span

    def test_context_overlay_with_attributes(self):
        """Test context overlay with custom attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        custom_attrs = {"user.id": "123", "session.id": "abc"}
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with context_overlay(GenAIOperation.CHAT, attributes=custom_attrs):
                pass
        
        assert captured_attributes == custom_attrs

    def test_context_overlay_with_different_span_kinds(self):
        """Test context overlay with different span kinds."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_kind = None
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_kind
            captured_kind = kind
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with context_overlay(GenAIOperation.EMBEDDINGS, kind=SpanKind.CLIENT):
                pass
        
        assert captured_kind == SpanKind.CLIENT

    def test_context_overlay_converts_enum_to_string(self):
        """Test that context overlay converts GenAIOperation enum to string."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_name = None
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_name
            captured_name = name
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with context_overlay(GenAIOperation.RETRIEVAL):
                pass
        
        assert captured_name == "retrieval"

    def test_context_overlay_handles_exception(self):
        """Test that context overlay handles exceptions and records them."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        test_exception = ValueError("Test error")
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with pytest.raises(ValueError, match="Test error"):
                with context_overlay(GenAIOperation.CHAT):
                    raise test_exception
        
        # Verify span status was set to error
        mock_span.set_status.assert_called_once()
        status_call = mock_span.set_status.call_args[0][0]
        assert status_call.status_code == StatusCode.ERROR
        assert "Test error" in str(status_call.description)
        
        # Verify exception was recorded
        mock_span.record_exception.assert_called_once_with(test_exception)

    def test_context_overlay_propagates_exception(self):
        """Test that context overlay propagates exceptions."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with pytest.raises(RuntimeError, match="Test"):
                with context_overlay(GenAIOperation.CHAT):
                    raise RuntimeError("Test")

    def test_context_overlay_with_various_operations(self):
        """Test context overlay with various GenAI operations."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        operations = [
            GenAIOperation.CHAT,
            GenAIOperation.EMBEDDINGS,
            GenAIOperation.TEXT_COMPLETION,
            GenAIOperation.CREATE_AGENT,
            GenAIOperation.INVOKE_AGENT,
        ]
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            for operation in operations:
                with context_overlay(operation):
                    pass

    def test_context_overlay_default_span_kind(self):
        """Test that context overlay uses INTERNAL as default span kind."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_kind = None
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_kind
            captured_kind = kind
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with context_overlay(GenAIOperation.CHAT):
                pass
        
        assert captured_kind == SpanKind.INTERNAL

    def test_context_overlay_yields_span(self):
        """Test that context overlay yields the span for advanced usage."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        
        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span
        
        mock_tracer.start_as_current_span = mock_start_as_current_span
        
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with context_overlay(GenAIOperation.CHAT) as span:
                assert span is mock_span
                # Span methods should be available
                span.add_event("test_event")
        
        mock_span.add_event.assert_called_once_with("test_event")


class TestGetCurrentSpan:
    """Test suite for get_current_span function."""

    def test_get_current_span_returns_span(self):
        """Test that get_current_span returns the current span."""
        mock_span = MagicMock()
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            span = get_current_span()
            assert span is mock_span

    def test_get_current_span_when_no_active_span(self):
        """Test get_current_span when no span is active."""
        mock_non_recording_span = MagicMock()
        mock_non_recording_span.is_recording.return_value = False
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_non_recording_span):
            span = get_current_span()
            assert span is mock_non_recording_span

    def test_get_current_span_returns_recording_span(self):
        """Test that get_current_span can return a recording span."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            span = get_current_span()
            assert span.is_recording()


class TestAddSpanAttribute:
    """Test suite for add_span_attribute function."""

    def test_add_span_attribute_to_recording_span(self):
        """Test adding attribute to a recording span."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            add_span_attribute("test.key", "test_value")
            mock_span.set_attribute.assert_called_once_with("test.key", "test_value")

    def test_add_span_attribute_to_non_recording_span(self):
        """Test adding attribute to a non-recording span does nothing."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            add_span_attribute("test.key", "test_value")
            mock_span.set_attribute.assert_not_called()

    def test_add_span_attribute_with_different_types(self):
        """Test adding attributes of different types."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        
        test_cases = [
            ("str.key", "string_value"),
            ("int.key", 42),
            ("float.key", 3.14),
            ("bool.key", True),
            ("list.key", ["a", "b", "c"]),
        ]
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            for key, value in test_cases:
                add_span_attribute(key, value)
        
        # Verify all attributes were set
        assert mock_span.set_attribute.call_count == len(test_cases)
        for (key, value), call_obj in zip(test_cases, mock_span.set_attribute.call_args_list):
            assert call_obj[0][0] == key
            assert call_obj[0][1] == value

    def test_add_span_attribute_with_namespaced_keys(self):
        """Test adding attributes with namespaced keys."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            add_span_attribute("app.user.id", "123")
            add_span_attribute("app.request.path", "/api/v1")
            add_span_attribute("custom.feature.enabled", True)
        
        assert mock_span.set_attribute.call_count == 3

    def test_add_span_attribute_safe_when_no_active_span(self):
        """Test that add_span_attribute is safe when no span is active."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            # Should not raise exception
            add_span_attribute("test.key", "value")
            mock_span.set_attribute.assert_not_called()


class TestChatSpan:
    """Test suite for chat_span function."""

    def test_chat_span_basic(self):
        """Test chat_span with required args only: span name, kind CLIENT, required attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_name = captured_kind = None
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_name, captured_kind
            captured_name = name
            captured_kind = kind
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai"):
                pass

        assert captured_name == "chat gpt-4"
        assert captured_kind == SpanKind.CLIENT
        assert captured_attributes["gen_ai.operation.name"] == "chat"
        assert captured_attributes["gen_ai.provider.name"] == "openai"
        assert captured_attributes["gen_ai.request.model"] == "gpt-4"

    def test_chat_span_with_server_address(self):
        """Test chat_span with server_address sets server.address."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai", server_address="api.openai.com"):
                pass

        assert captured_attributes.get("server.address") == "api.openai.com"

    def test_chat_span_without_server_address_omits_server_address(self):
        """Test chat_span without server_address does not set server.address."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai"):
                pass

        assert "server.address" not in captured_attributes

    def test_chat_span_with_conversation_id(self):
        """Test chat_span with conversation_id sets gen_ai.conversation.id."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai", conversation_id="conv_abc123"):
                pass

        assert captured_attributes.get("gen_ai.conversation.id") == "conv_abc123"

    def test_chat_span_without_conversation_id_omits_conversation_id(self):
        """Test chat_span without conversation_id does not set gen_ai.conversation.id."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai"):
                pass

        assert "gen_ai.conversation.id" not in captured_attributes

    def test_chat_span_with_extra_attributes(self):
        """Test chat_span merges optional attributes into span attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        extra = {"custom.key": "value", "gen_ai.conversation.id": "conv-1"}
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai", attributes=extra):
                pass

        assert captured_attributes.get("custom.key") == "value"
        assert captured_attributes.get("gen_ai.conversation.id") == "conv-1"

    def test_chat_span_required_attributes_not_overridable(self):
        """Test chat_span: user attributes cannot override required semantic keys."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai", attributes={
                "gen_ai.operation.name": "other",
                "gen_ai.provider.name": "other",
                "gen_ai.request.model": "other-model",
            }):
                pass

        assert captured_attributes["gen_ai.operation.name"] == "chat"
        assert captured_attributes["gen_ai.provider.name"] == "openai"
        assert captured_attributes["gen_ai.request.model"] == "gpt-4"

    def test_chat_span_handles_exception(self):
        """Test chat_span records exception and sets status to ERROR, then propagates."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        test_exception = ValueError("Test error")
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with pytest.raises(ValueError, match="Test error"):
                with chat_span("gpt-4", "openai"):
                    raise test_exception

        mock_span.set_status.assert_called_once()
        status_call = mock_span.set_status.call_args[0][0]
        assert status_call.status_code == StatusCode.ERROR
        assert "Test error" in str(status_call.description)
        mock_span.record_exception.assert_called_once_with(test_exception)

    def test_chat_span_yields_span(self):
        """Test chat_span yields the span for advanced usage."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with chat_span("gpt-4", "openai") as span:
                assert span is mock_span
                span.add_event("test")

        mock_span.add_event.assert_called_once_with("test")


class TestExecuteToolSpan:
    """Test suite for execute_tool_span function."""

    def test_execute_tool_span_basic(self):
        """Test execute_tool_span with only tool_name: name, kind INTERNAL, required attrs."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_name = captured_kind = None
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_name, captured_kind
            captured_name = name
            captured_kind = kind
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with execute_tool_span("get_weather"):
                pass

        assert captured_name == "execute_tool get_weather"
        assert captured_kind == SpanKind.INTERNAL
        assert captured_attributes["gen_ai.operation.name"] == "execute_tool"
        assert captured_attributes["gen_ai.tool.name"] == "get_weather"
        assert "gen_ai.tool.type" not in captured_attributes
        assert "gen_ai.tool.description" not in captured_attributes

    def test_execute_tool_span_with_tool_type_and_description(self):
        """Test execute_tool_span with tool_type and tool_description sets attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with execute_tool_span(
                "get_weather",
                tool_type="function",
                tool_description="Get weather",
            ):
                pass

        assert captured_attributes.get("gen_ai.tool.type") == "function"
        assert captured_attributes.get("gen_ai.tool.description") == "Get weather"

    def test_execute_tool_span_without_optionals_omits_attrs(self):
        """Test execute_tool_span without tool_type/tool_description omits those attrs."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with execute_tool_span("get_weather"):
                pass

        assert captured_attributes.keys() == {"gen_ai.operation.name", "gen_ai.tool.name"}

    def test_execute_tool_span_with_extra_attributes(self):
        """Test execute_tool_span merges optional attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with execute_tool_span("get_weather", attributes={"custom.key": 42}):
                pass

        assert captured_attributes.get("custom.key") == 42

    def test_execute_tool_span_required_attributes_not_overridable(self):
        """Test execute_tool_span: user attributes cannot override required semantic keys."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with execute_tool_span("get_weather", attributes={
                "gen_ai.operation.name": "other",
                "gen_ai.tool.name": "other_tool",
            }):
                pass

        assert captured_attributes["gen_ai.operation.name"] == "execute_tool"
        assert captured_attributes["gen_ai.tool.name"] == "get_weather"

    def test_execute_tool_span_handles_exception(self):
        """Test execute_tool_span records exception and propagates."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        test_exception = RuntimeError("Tool failed")
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with pytest.raises(RuntimeError, match="Tool failed"):
                with execute_tool_span("get_weather"):
                    raise test_exception

        mock_span.set_status.assert_called_once()
        status_call = mock_span.set_status.call_args[0][0]
        assert status_call.status_code == StatusCode.ERROR
        mock_span.record_exception.assert_called_once_with(test_exception)

    def test_execute_tool_span_yields_span(self):
        """Test execute_tool_span yields the span."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with execute_tool_span("get_weather") as span:
                assert span is mock_span
                span.set_attribute("gen_ai.tool.call.result", "sunny")

        mock_span.set_attribute.assert_called_once_with("gen_ai.tool.call.result", "sunny")


class TestInvokeAgentSpan:
    """Test suite for invoke_agent_span function."""

    def test_invoke_agent_span_basic(self):
        """Test invoke_agent_span with provider and agent_name: span name, kind CLIENT, required attrs."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_name = captured_kind = None
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_name, captured_kind
            captured_name = name
            captured_kind = kind
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="MyAgent"):
                pass

        assert captured_name == "invoke_agent MyAgent"
        assert captured_kind == SpanKind.CLIENT
        assert captured_attributes["gen_ai.operation.name"] == "invoke_agent"
        assert captured_attributes["gen_ai.provider.name"] == "openai"
        assert captured_attributes["gen_ai.agent.name"] == "MyAgent"

    def test_invoke_agent_span_without_agent_name(self):
        """Test invoke_agent_span without agent_name uses span name 'invoke_agent' only."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_name = None
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_name
            captured_name = name
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai"):
                pass

        assert captured_name == "invoke_agent"
        assert "gen_ai.agent.name" not in captured_attributes

    def test_invoke_agent_span_with_agent_id_description_server_address(self):
        """Test invoke_agent_span with optional agent_id, agent_description, server_address."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(
                provider="openai",
                agent_name="Bot",
                agent_id="asst_123",
                agent_description="Help with math",
                server_address="api.openai.com",
            ):
                pass

        assert captured_attributes.get("gen_ai.agent.id") == "asst_123"
        assert captured_attributes.get("gen_ai.agent.description") == "Help with math"
        assert captured_attributes.get("server.address") == "api.openai.com"

    def test_invoke_agent_span_with_conversation_id(self):
        """Test invoke_agent_span with conversation_id sets gen_ai.conversation.id."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="Bot", conversation_id="thread_xyz"):
                pass

        assert captured_attributes.get("gen_ai.conversation.id") == "thread_xyz"

    def test_invoke_agent_span_without_conversation_id_omits_conversation_id(self):
        """Test invoke_agent_span without conversation_id does not set gen_ai.conversation.id."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="Bot"):
                pass

        assert "gen_ai.conversation.id" not in captured_attributes

    def test_invoke_agent_span_kind_internal(self):
        """Test invoke_agent_span with kind=INTERNAL."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_kind = None

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            nonlocal captured_kind
            captured_kind = kind
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="Chain", kind=SpanKind.INTERNAL):
                pass

        assert captured_kind == SpanKind.INTERNAL

    def test_invoke_agent_span_with_extra_attributes(self):
        """Test invoke_agent_span merges optional attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="Bot", attributes={"gen_ai.conversation.id": "conv-1"}):
                pass

        assert captured_attributes.get("gen_ai.conversation.id") == "conv-1"

    def test_invoke_agent_span_required_attributes_not_overridable(self):
        """Test invoke_agent_span: user attributes cannot override required semantic keys."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        captured_attributes = {}

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            captured_attributes.update(attributes or {})
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="Bot", attributes={
                "gen_ai.operation.name": "other",
                "gen_ai.provider.name": "other",
            }):
                pass

        assert captured_attributes["gen_ai.operation.name"] == "invoke_agent"
        assert captured_attributes["gen_ai.provider.name"] == "openai"

    def test_invoke_agent_span_handles_exception(self):
        """Test invoke_agent_span records exception and propagates."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        test_exception = ValueError("Agent failed")
        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with pytest.raises(ValueError, match="Agent failed"):
                with invoke_agent_span(provider="openai", agent_name="Bot"):
                    raise test_exception

        mock_span.set_status.assert_called_once()
        status_call = mock_span.set_status.call_args[0][0]
        assert status_call.status_code == StatusCode.ERROR
        mock_span.record_exception.assert_called_once_with(test_exception)

    def test_invoke_agent_span_yields_span(self):
        """Test invoke_agent_span yields the span for advanced usage."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()

        @contextmanager
        def mock_start_as_current_span(name, kind=None, attributes=None):
            yield mock_span

        mock_tracer.start_as_current_span = mock_start_as_current_span

        with patch('opentelemetry.trace.get_tracer', return_value=mock_tracer):
            with invoke_agent_span(provider="openai", agent_name="Bot") as span:
                assert span is mock_span
                span.add_event("agent_step")

        mock_span.add_event.assert_called_once_with("agent_step")
