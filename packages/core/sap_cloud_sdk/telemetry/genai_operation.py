"""GenAI operation types following OpenTelemetry semantic conventions."""

from enum import Enum


class GenAIOperation(str, Enum):
    """
    GenAI operation types following OpenTelemetry semantic conventions.

    These operation names should be used when creating spans for GenAI operations
    to ensure compliance with OpenTelemetry semantic conventions.

    Reference: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

    Examples:
        >>> from sap_cloud_sdk.telemetry import context_overlay, GenAIOperation
        >>> with context_overlay(GenAIOperation.CHAT):
        ...     response = llm.chat(message)
    """

    CHAT = "chat"
    """Chat completion operation such as OpenAI Chat API."""

    TEXT_COMPLETION = "text_completion"
    """Text completions operation such as OpenAI Completions API (Legacy)."""

    EMBEDDINGS = "embeddings"
    """Embeddings operation such as OpenAI Create embeddings API."""

    GENERATE_CONTENT = "generate_content"
    """Multimodal content generation operation such as Gemini Generate Content."""

    RETRIEVAL = "retrieval"
    """Retrieval operation such as OpenAI Search Vector Store API."""

    EXECUTE_TOOL = "execute_tool"
    """Execute a tool."""

    CREATE_AGENT = "create_agent"
    """Create GenAI agent."""

    INVOKE_AGENT = "invoke_agent"
    """Invoke GenAI agent."""

    def __str__(self) -> str:
        """Return the string value of the operation."""
        return self.value
