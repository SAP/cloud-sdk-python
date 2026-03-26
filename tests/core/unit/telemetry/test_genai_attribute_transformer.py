"""Tests for GenAI attribute transformer."""

import json
import pytest
from unittest.mock import MagicMock, Mock
from typing import MutableMapping, Any

from opentelemetry.sdk.trace.export import SpanExportResult

from sap_cloud_sdk.core.telemetry.genai_attribute_transformer import GenAIAttributeTransformer


def create_mock_span(attributes: dict, name: str = "test_span") -> MagicMock:
    """Helper to create a mock ReadableSpan with mutable attributes."""
    span = MagicMock()
    span.name = name
    span.attributes = attributes.copy()
    # Create a mutable dict that can be modified
    span._attributes = attributes.copy()
    return span


class TestGenAIAttributeTransformerInit:
    """Test suite for GenAIAttributeTransformer initialization."""

    def test_init_with_wrapped_exporter(self):
        """Test initialization with wrapped exporter."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        assert transformer.wrapped_exporter is mock_exporter


class TestNormalizeAttributes:
    """Test suite for _normalize_attributes method."""

    def test_normalize_attributes_with_traceloop_model_name(self):
        """Test normalization extracts model name from traceloop attributes."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'traceloop.association.properties.ls_provider': 'openai',
        })

        transformer._normalize_attributes(span)

        assert span._attributes['gen_ai.request.model'] == 'gpt-4'
        assert span._attributes['gen_ai.provider.name'] == 'openai'
        # Fallback: response.model should be set from request.model
        assert span._attributes['gen_ai.response.model'] == 'gpt-4'

    def test_normalize_attributes_preserves_existing_response_model(self):
        """Test normalization preserves existing gen_ai.response.model if present."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'gen_ai.response.model': 'gpt-4-turbo',  # Already present, should not be overwritten
        })

        transformer._normalize_attributes(span)

        assert span._attributes['gen_ai.request.model'] == 'gpt-4'
        # Should preserve the existing response.model
        assert span._attributes['gen_ai.response.model'] == 'gpt-4-turbo'

    def test_normalize_attributes_replaces_unknown_response_model(self):
        """Test normalization replaces 'unknown' gen_ai.response.model with request model."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'gen_ai.response.model': 'unknown',  # Should be replaced with actual model
        })

        transformer._normalize_attributes(span)

        assert span._attributes['gen_ai.request.model'] == 'gpt-4'
        # Should replace "unknown" with actual model name
        assert span._attributes['gen_ai.response.model'] == 'gpt-4'

    def test_normalize_attributes_with_llm_usage(self):
        """Test normalization maps llm.usage.* to gen_ai.usage.*."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.total_tokens': 150,
            'llm.usage.input_tokens': 100,
            'llm.usage.output_tokens': 50,
        })

        transformer._normalize_attributes(span)

        assert span._attributes['gen_ai.usage.total_tokens'] == 150
        assert span._attributes['gen_ai.usage.input_tokens'] == 100
        assert span._attributes['gen_ai.usage.output_tokens'] == 50

    def test_normalize_attributes_with_prompt_tokens_fallback(self):
        """Test normalization uses prompt_tokens as fallback for input_tokens."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.prompt_tokens': 100,
            'llm.usage.completion_tokens': 50,
        })

        transformer._normalize_attributes(span)

        assert span._attributes['gen_ai.usage.input_tokens'] == 100
        assert span._attributes['gen_ai.usage.output_tokens'] == 50

    def test_normalize_attributes_with_cache_read_tokens(self):
        """Test normalization includes cache read input tokens."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.cache_read_input_tokens': 25,
        })

        transformer._normalize_attributes(span)

        assert span._attributes['gen_ai.usage.cache_read_input_tokens'] == 25

    def test_normalize_attributes_removes_standard_traceloop_attributes(self):
        """Test normalization removes only standard traceloop.* attributes, preserving custom ones."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'traceloop.association.properties.ls_provider': 'openai',
            'traceloop.custom.attribute': 'custom_value',
            'traceloop.proprietary.data': 'proprietary_value',
            'gen_ai.request.model': 'should-remain',
        })

        transformer._normalize_attributes(span)

        # Standard traceloop.* attributes should be removed
        assert 'traceloop.association.properties.ls_model_name' not in span._attributes
        assert 'traceloop.association.properties.ls_provider' not in span._attributes

        # Custom/proprietary traceloop.* attributes should be preserved
        assert span._attributes.get('traceloop.custom.attribute') == 'custom_value'
        assert span._attributes.get('traceloop.proprietary.data') == 'proprietary_value'

        # gen_ai attributes should remain
        assert 'gen_ai.request.model' in span._attributes

    def test_normalize_attributes_removes_standard_llm_attributes(self):
        """Test normalization removes only standard llm.usage.* attributes, preserving custom ones."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.total_tokens': 150,
            'llm.usage.input_tokens': 100,
            'llm.custom_cost_tracking': 0.0023,
            'llm.proprietary.business_unit': 'finance',
        })

        transformer._normalize_attributes(span)

        # Standard llm.usage.* attributes should be removed after transformation
        assert 'llm.usage.total_tokens' not in span._attributes
        assert 'llm.usage.input_tokens' not in span._attributes

        # Custom/proprietary llm.* attributes should be preserved
        assert span._attributes.get('llm.custom_cost_tracking') == 0.0023
        assert span._attributes.get('llm.proprietary.business_unit') == 'finance'

        # gen_ai attributes should be present
        assert 'gen_ai.usage.total_tokens' in span._attributes
        assert 'gen_ai.usage.input_tokens' in span._attributes

    def test_normalize_attributes_skips_non_genai_spans(self):
        """Test normalization skips spans without traceloop or llm attributes."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        original_attrs = {
            'http.method': 'GET',
            'http.url': 'http://example.com',
        }
        span = create_mock_span(original_attrs.copy())

        transformer._normalize_attributes(span)

        # Attributes should remain unchanged
        assert span._attributes == original_attrs

    def test_normalize_attributes_with_no_attributes(self):
        """Test normalization handles span with no attributes."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = MagicMock()
        span.attributes = None

        # Should not raise an error
        transformer._normalize_attributes(span)

    def test_normalize_attributes_with_no_internal_attributes(self):
        """Test normalization handles span without _attributes."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = MagicMock()
        span.attributes = {'test': 'value'}
        span._attributes = None

        # Should not raise an error
        transformer._normalize_attributes(span)

    def test_normalize_attributes_handles_non_string_values(self):
        """Test normalization handles non-string model name and provider values."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 123,  # non-string
            'traceloop.association.properties.ls_provider': None,
        })

        transformer._normalize_attributes(span)

        # Should not add gen_ai attributes for non-string values
        assert 'gen_ai.request.model' not in span._attributes
        assert 'gen_ai.provider.name' not in span._attributes

    def test_normalize_attributes_handles_empty_string_values(self):
        """Test normalization handles empty string model name and provider."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': '',
            'traceloop.association.properties.ls_provider': '',
        })

        transformer._normalize_attributes(span)

        # Should not add gen_ai attributes for empty strings
        assert 'gen_ai.request.model' not in span._attributes
        assert 'gen_ai.provider.name' not in span._attributes


class TestMapLLMUsage:
    """Test suite for _map_llm_usage method."""

    def test_map_llm_usage_all_fields(self):
        """Test mapping all usage fields."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'llm.usage.total_tokens': 150,
            'llm.usage.input_tokens': 100,
            'llm.usage.output_tokens': 50,
            'llm.usage.cache_read_input_tokens': 25,
        }

        transformer._map_llm_usage(attrs)

        assert attrs['gen_ai.usage.total_tokens'] == 150
        assert attrs['gen_ai.usage.input_tokens'] == 100
        assert attrs['gen_ai.usage.output_tokens'] == 50
        assert attrs['gen_ai.usage.cache_read_input_tokens'] == 25

    def test_map_llm_usage_prefers_input_tokens(self):
        """Test that input_tokens is preferred over prompt_tokens."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'llm.usage.input_tokens': 100,
            'llm.usage.prompt_tokens': 200,  # should be ignored
        }

        transformer._map_llm_usage(attrs)

        assert attrs['gen_ai.usage.input_tokens'] == 100

    def test_map_llm_usage_prefers_output_tokens(self):
        """Test that output_tokens is preferred over completion_tokens."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'llm.usage.output_tokens': 50,
            'llm.usage.completion_tokens': 100,  # should be ignored
        }

        transformer._map_llm_usage(attrs)

        assert attrs['gen_ai.usage.output_tokens'] == 50

    def test_map_llm_usage_partial_fields(self):
        """Test mapping with only some fields present."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'llm.usage.total_tokens': 150,
        }

        transformer._map_llm_usage(attrs)

        assert attrs['gen_ai.usage.total_tokens'] == 150
        assert 'gen_ai.usage.input_tokens' not in attrs
        assert 'gen_ai.usage.output_tokens' not in attrs


class TestExport:
    """Test suite for export method."""

    def test_export_normalizes_genai_spans(self):
        """Test that export normalizes spans with traceloop/llm attributes."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.total_tokens': 150,
        }, name='chat')
        spans = [span]

        result = transformer.export(spans)

        # Verify transformation occurred
        assert 'gen_ai.request.model' in span._attributes
        assert 'gen_ai.usage.total_tokens' in span._attributes
        assert not any(k.startswith('llm.') for k in span._attributes.keys())
        assert not any(k.startswith('traceloop.') for k in span._attributes.keys())
        assert result == SpanExportResult.SUCCESS

    def test_export_non_genai_spans_unchanged(self):
        """Test that non-GenAI spans are not transformed."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        original_attrs = {
            'http.method': 'GET',
            'http.url': 'http://example.com',
        }
        span = create_mock_span(original_attrs.copy())
        spans = [span]

        result = transformer.export(spans)

        # Verify no transformation occurred
        assert span._attributes == original_attrs
        assert result == SpanExportResult.SUCCESS

    def test_export_handles_transformation_error(self):
        """Test that export handles errors during transformation gracefully."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        # Create span that will cause error during transformation
        span = MagicMock()
        span.attributes = {'traceloop.association.properties.ls_model_name': 'gpt-4'}
        span.name = 'chat'
        # Missing _attributes will cause error
        delattr(span, '_attributes')

        spans = [span]

        # Should not raise exception, still calls wrapped exporter
        result = transformer.export(spans)
        mock_exporter.export.assert_called_once()
        assert result == SpanExportResult.SUCCESS

    def test_export_calls_wrapped_exporter(self):
        """Test that export always calls the wrapped exporter."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({'http.method': 'GET'})
        spans = [span]

        result = transformer.export(spans)

        mock_exporter.export.assert_called_once_with(spans)
        assert result == SpanExportResult.SUCCESS


class TestShutdownAndForceFlush:
    """Test suite for shutdown and force_flush methods."""

    def test_shutdown_calls_wrapped_exporter(self):
        """Test that shutdown calls wrapped exporter's shutdown."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        transformer.shutdown()

        mock_exporter.shutdown.assert_called_once()

    def test_force_flush_without_timeout(self):
        """Test force_flush without timeout parameter."""
        mock_exporter = MagicMock()
        mock_exporter.force_flush.return_value = True
        transformer = GenAIAttributeTransformer(mock_exporter)

        result = transformer.force_flush()

        mock_exporter.force_flush.assert_called_once_with()
        assert result is True

    def test_force_flush_with_timeout(self):
        """Test force_flush with timeout parameter."""
        mock_exporter = MagicMock()
        mock_exporter.force_flush.return_value = True
        transformer = GenAIAttributeTransformer(mock_exporter)

        result = transformer.force_flush(timeout_millis=5000)

        mock_exporter.force_flush.assert_called_once_with(5000)
        assert result is True

    def test_force_flush_returns_false_on_failure(self):
        """Test force_flush returns False when wrapped exporter fails."""
        mock_exporter = MagicMock()
        mock_exporter.force_flush.return_value = False
        transformer = GenAIAttributeTransformer(mock_exporter)

        result = transformer.force_flush()

        assert result is False


class TestTransformMessages:
    """Test suite for _transform_messages method."""

    def test_transform_input_messages(self):
        """Test transforming gen_ai.prompt.* to gen_ai.input.messages."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'gen_ai.prompt.0.role': 'user',
            'gen_ai.prompt.0.content': 'What is Application Foundation?',
            'gen_ai.prompt.1.role': 'system',
            'gen_ai.prompt.1.content': 'You are a helpful assistant',
        })

        transformer._normalize_attributes(span)

        # Check that gen_ai.input.messages was created
        assert 'gen_ai.input.messages' in span._attributes

        # Parse and verify the JSON structure
        messages = json.loads(span._attributes['gen_ai.input.messages'])
        assert len(messages) == 2

        assert messages[0]['role'] == 'user'
        assert messages[0]['parts'][0]['type'] == 'text'
        assert messages[0]['parts'][0]['content'] == 'What is Application Foundation?'

        assert messages[1]['role'] == 'system'
        assert messages[1]['parts'][0]['type'] == 'text'
        assert messages[1]['parts'][0]['content'] == 'You are a helpful assistant'

        # Verify old attributes were removed
        assert not any(k.startswith('gen_ai.prompt.') for k in span._attributes.keys())

    def test_transform_output_messages(self):
        """Test transforming gen_ai.completion.* to gen_ai.output.messages."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'gen_ai.completion.0.role': 'assistant',
            'gen_ai.completion.0.content': 'Application Foundation is...',
            'gen_ai.completion.0.finish_reason': 'stop',
        })

        transformer._normalize_attributes(span)

        # Check that gen_ai.output.messages was created
        assert 'gen_ai.output.messages' in span._attributes

        # Parse and verify the JSON structure
        messages = json.loads(span._attributes['gen_ai.output.messages'])
        assert len(messages) == 1

        assert messages[0]['role'] == 'assistant'
        assert messages[0]['parts'][0]['type'] == 'text'
        assert messages[0]['parts'][0]['content'] == 'Application Foundation is...'
        assert messages[0]['finish_reason'] == 'stop'

        # Verify old attributes were removed
        assert not any(k.startswith('gen_ai.completion.') for k in span._attributes.keys())

    def test_transform_multiple_output_messages(self):
        """Test transforming multiple completion messages."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'gen_ai.completion.0.role': 'assistant',
            'gen_ai.completion.0.content': 'First response',
            'gen_ai.completion.1.role': 'assistant',
            'gen_ai.completion.1.content': 'Second response',
        })

        transformer._normalize_attributes(span)

        messages = json.loads(span._attributes['gen_ai.output.messages'])
        assert len(messages) == 2
        assert messages[0]['parts'][0]['content'] == 'First response'
        assert messages[1]['parts'][0]['content'] == 'Second response'

    def test_transform_no_messages(self):
        """Test that transformation works when no message attributes present."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.total_tokens': 150,
        })

        transformer._normalize_attributes(span)

        # Should not create message attributes
        assert 'gen_ai.input.messages' not in span._attributes
        assert 'gen_ai.output.messages' not in span._attributes

    def test_transform_messages_with_extra_fields(self):
        """Test that extra fields in messages are preserved."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'gen_ai.prompt.0.role': 'user',
            'gen_ai.prompt.0.content': 'Hello',
            'gen_ai.prompt.0.custom_field': 'custom_value',
        })

        transformer._normalize_attributes(span)

        messages = json.loads(span._attributes['gen_ai.input.messages'])
        assert messages[0]['custom_field'] == 'custom_value'


class TestCollectIndexedAttributes:
    """Test suite for _collect_indexed_attributes method."""

    def test_collect_indexed_attributes_basic(self):
        """Test basic collection of indexed attributes."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'gen_ai.prompt.0.role': 'user',
            'gen_ai.prompt.0.content': 'Hello',
            'gen_ai.prompt.1.role': 'assistant',
            'gen_ai.prompt.1.content': 'Hi',
        }

        result = transformer._collect_indexed_attributes(attrs, 'gen_ai.prompt.')

        assert len(result) == 2
        assert result[0] == {'role': 'user', 'content': 'Hello'}
        assert result[1] == {'role': 'assistant', 'content': 'Hi'}

    def test_collect_indexed_attributes_empty(self):
        """Test collection with no matching attributes."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'http.method': 'GET',
            'http.url': 'http://example.com',
        }

        result = transformer._collect_indexed_attributes(attrs, 'gen_ai.prompt.')

        assert len(result) == 0

    def test_collect_indexed_attributes_invalid_format(self):
        """Test collection handles invalid attribute formats."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        attrs = {
            'gen_ai.prompt.notanumber.role': 'user',
            'gen_ai.prompt.0': 'missing_field',
            'gen_ai.prompt.': 'no_index',
        }

        result = transformer._collect_indexed_attributes(attrs, 'gen_ai.prompt.')

        # Should skip invalid formats
        assert len(result) == 0


class TestStructureMessages:
    """Test suite for _structure_messages method."""

    def test_structure_messages_basic(self):
        """Test basic message structuring."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        indexed_messages = {
            0: {'role': 'user', 'content': 'Hello'},
            1: {'role': 'assistant', 'content': 'Hi'},
        }

        result = transformer._structure_messages(indexed_messages)

        assert len(result) == 2
        assert result[0]['role'] == 'user'
        assert result[0]['parts'][0]['type'] == 'text'
        assert result[0]['parts'][0]['content'] == 'Hello'

    def test_structure_messages_with_finish_reason(self):
        """Test structuring messages with finish_reason."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        indexed_messages = {
            0: {'role': 'assistant', 'content': 'Response', 'finish_reason': 'stop'},
        }

        result = transformer._structure_messages(indexed_messages)

        assert result[0]['finish_reason'] == 'stop'

    def test_structure_messages_missing_content(self):
        """Test structuring messages without content field."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        indexed_messages = {
            0: {'role': 'user'},
        }

        result = transformer._structure_messages(indexed_messages)

        assert result[0]['role'] == 'user'
        assert len(result[0]['parts']) == 0

    def test_structure_messages_default_role(self):
        """Test structuring messages without role uses default."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        indexed_messages = {
            0: {'content': 'Hello'},
        }

        result = transformer._structure_messages(indexed_messages)

        assert result[0]['role'] == 'user'

    def test_structure_messages_preserves_order(self):
        """Test that messages are ordered by index."""
        mock_exporter = MagicMock()
        transformer = GenAIAttributeTransformer(mock_exporter)

        indexed_messages = {
            2: {'role': 'system', 'content': 'Third'},
            0: {'role': 'user', 'content': 'First'},
            1: {'role': 'assistant', 'content': 'Second'},
        }

        result = transformer._structure_messages(indexed_messages)

        assert len(result) == 3
        assert result[0]['parts'][0]['content'] == 'First'
        assert result[1]['parts'][0]['content'] == 'Second'
        assert result[2]['parts'][0]['content'] == 'Third'


class TestIntegrationScenarios:
    """Test suite for end-to-end transformation scenarios."""

    def test_full_transformation_with_traceloop_preserves_custom(self):
        """Test complete transformation for Traceloop instrumented span, preserving custom attributes."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'traceloop.association.properties.ls_provider': 'openai',
            'llm.usage.total_tokens': 150,
            'llm.usage.input_tokens': 100,
            'llm.usage.output_tokens': 50,
            'llm.custom_cost_tracking': 0.0023,
            'traceloop.custom_session_id': 'session-123',
        }, name='ChatCompletion')

        transformer.export([span])

        # Verify all transformations
        attrs = span._attributes
        assert attrs['gen_ai.request.model'] == 'gpt-4'
        assert attrs['gen_ai.provider.name'] == 'openai'
        assert attrs['gen_ai.usage.total_tokens'] == 150
        assert attrs['gen_ai.usage.input_tokens'] == 100
        assert attrs['gen_ai.usage.output_tokens'] == 50

        # Verify standard llm.usage.* and traceloop.association.* attributes were removed
        assert 'llm.usage.total_tokens' not in attrs
        assert 'llm.usage.input_tokens' not in attrs
        assert 'traceloop.association.properties.ls_model_name' not in attrs
        assert 'traceloop.association.properties.ls_provider' not in attrs

        # Verify custom attributes were preserved
        assert attrs.get('llm.custom_cost_tracking') == 0.0023
        assert attrs.get('traceloop.custom_session_id') == 'session-123'

    def test_full_transformation_with_messages(self):
        """Test complete transformation including message conversion."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'traceloop.association.properties.ls_provider': 'openai',
            'gen_ai.prompt.0.role': 'user',
            'gen_ai.prompt.0.content': 'What is AI?',
            'gen_ai.completion.0.role': 'assistant',
            'gen_ai.completion.0.content': 'AI is...',
            'gen_ai.completion.0.finish_reason': 'stop',
            'llm.usage.total_tokens': 150,
        }, name='ChatCompletion')

        transformer.export([span])

        attrs = span._attributes

        # Verify basic transformations
        assert attrs['gen_ai.request.model'] == 'gpt-4'
        assert attrs['gen_ai.provider.name'] == 'openai'

        # Verify message transformations
        assert 'gen_ai.input.messages' in attrs
        assert 'gen_ai.output.messages' in attrs

        input_messages = json.loads(attrs['gen_ai.input.messages'])
        assert len(input_messages) == 1
        assert input_messages[0]['role'] == 'user'

        output_messages = json.loads(attrs['gen_ai.output.messages'])
        assert len(output_messages) == 1
        assert output_messages[0]['role'] == 'assistant'
        assert output_messages[0]['finish_reason'] == 'stop'

        # Verify all old attributes were removed
        assert not any(key.startswith('llm.') for key in attrs.keys())
        assert not any(key.startswith('traceloop.') for key in attrs.keys())
        assert not any(key.startswith('gen_ai.prompt.') for key in attrs.keys())
        assert not any(key.startswith('gen_ai.completion.') for key in attrs.keys())

    def test_mixed_genai_and_non_genai_spans(self):
        """Test exporting mix of GenAI and non-GenAI spans."""
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = SpanExportResult.SUCCESS
        transformer = GenAIAttributeTransformer(mock_exporter)

        genai_span = create_mock_span({
            'traceloop.association.properties.ls_model_name': 'gpt-4',
            'llm.usage.total_tokens': 150,
        }, name='chat')

        http_span = create_mock_span({
            'http.method': 'GET',
        }, name='http_request')

        transformer.export([genai_span, http_span])

        # GenAI span should be transformed
        assert 'gen_ai.request.model' in genai_span._attributes
        assert not any(k.startswith('llm.') for k in genai_span._attributes.keys())

        # HTTP span should be unchanged
        assert 'http.method' in http_span._attributes
        assert 'gen_ai.request.model' not in http_span._attributes
