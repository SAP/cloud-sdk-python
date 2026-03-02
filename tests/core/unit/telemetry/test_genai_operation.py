"""Tests for GenAIOperation enum."""

import pytest

from cloud_sdk_python.core.telemetry.genai_operation import GenAIOperation


class TestGenAIOperation:
    """Test suite for GenAIOperation enum."""

    def test_genai_operation_values(self):
        """Test that GenAIOperation enum has expected values."""
        assert GenAIOperation.CHAT.value == "chat"
        assert GenAIOperation.TEXT_COMPLETION.value == "text_completion"
        assert GenAIOperation.EMBEDDINGS.value == "embeddings"
        assert GenAIOperation.GENERATE_CONTENT.value == "generate_content"
        assert GenAIOperation.RETRIEVAL.value == "retrieval"
        assert GenAIOperation.EXECUTE_TOOL.value == "execute_tool"
        assert GenAIOperation.CREATE_AGENT.value == "create_agent"
        assert GenAIOperation.INVOKE_AGENT.value == "invoke_agent"

    def test_genai_operation_str_representation(self):
        """Test that GenAIOperation enum converts to string correctly."""
        assert str(GenAIOperation.CHAT) == "chat"
        assert str(GenAIOperation.TEXT_COMPLETION) == "text_completion"
        assert str(GenAIOperation.EMBEDDINGS) == "embeddings"
        assert str(GenAIOperation.GENERATE_CONTENT) == "generate_content"
        assert str(GenAIOperation.RETRIEVAL) == "retrieval"
        assert str(GenAIOperation.EXECUTE_TOOL) == "execute_tool"
        assert str(GenAIOperation.CREATE_AGENT) == "create_agent"
        assert str(GenAIOperation.INVOKE_AGENT) == "invoke_agent"

    def test_genai_operation_is_string_enum(self):
        """Test that GenAIOperation enum inherits from str."""
        assert isinstance(GenAIOperation.CHAT, str)
        assert isinstance(GenAIOperation.EMBEDDINGS, str)
        assert isinstance(GenAIOperation.CREATE_AGENT, str)

    def test_genai_operation_equality(self):
        """Test GenAIOperation enum equality comparisons."""
        assert GenAIOperation.CHAT == GenAIOperation.CHAT
        assert GenAIOperation.CHAT != GenAIOperation.EMBEDDINGS
        assert GenAIOperation.CHAT == "chat"
        assert "chat" == GenAIOperation.CHAT

    def test_genai_operation_in_collection(self):
        """Test GenAIOperation enum membership in collections."""
        operations = [GenAIOperation.CHAT, GenAIOperation.EMBEDDINGS]
        assert GenAIOperation.CHAT in operations
        assert GenAIOperation.RETRIEVAL not in operations

    def test_all_genai_operations_present(self):
        """Test that all expected GenAI operations are present."""
        all_operations = list(GenAIOperation)
        assert len(all_operations) == 8
        assert GenAIOperation.CHAT in all_operations
        assert GenAIOperation.TEXT_COMPLETION in all_operations
        assert GenAIOperation.EMBEDDINGS in all_operations
        assert GenAIOperation.GENERATE_CONTENT in all_operations
        assert GenAIOperation.RETRIEVAL in all_operations
        assert GenAIOperation.EXECUTE_TOOL in all_operations
        assert GenAIOperation.CREATE_AGENT in all_operations
        assert GenAIOperation.INVOKE_AGENT in all_operations

    def test_genai_operation_iteration(self):
        """Test iterating over GenAIOperation enum."""
        operation_values = [str(op) for op in GenAIOperation]
        assert "chat" in operation_values
        assert "text_completion" in operation_values
        assert "embeddings" in operation_values
        assert "generate_content" in operation_values
        assert "retrieval" in operation_values
        assert "execute_tool" in operation_values
        assert "create_agent" in operation_values
        assert "invoke_agent" in operation_values

    def test_genai_operation_for_llm_operations(self):
        """Test GenAI operations for common LLM use cases."""
        # Chat operations
        assert GenAIOperation.CHAT.value == "chat"
        
        # Embedding operations
        assert GenAIOperation.EMBEDDINGS.value == "embeddings"
        
        # Agent operations
        assert GenAIOperation.CREATE_AGENT.value == "create_agent"
        assert GenAIOperation.INVOKE_AGENT.value == "invoke_agent"

    def test_genai_operation_unique_values(self):
        """Test that all GenAI operation values are unique."""
        all_operations = list(GenAIOperation)
        operation_values = [op.value for op in all_operations]
        assert len(operation_values) == len(set(operation_values))