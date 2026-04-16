"""
GenAI Attribute Transformer.

Transforms OpenInference llm.* attributes to OpenTelemetry gen_ai.* semantic conventions,
replacing the original attributes to ensure pure OpenTelemetry compliance.
"""

import json
import logging
from typing import Any, Dict, List, MutableMapping, Optional, Sequence, cast

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


class GenAIAttributeTransformer(SpanExporter):
    """
    Span exporter wrapper that performs a minimal normalization of attributes for GenAI spans.
    It reduces span size and normalizes provider/model and usage metrics while removing only
    standard vendor-specific attributes. All non-standard attributes are preserved, allowing
    users to include custom telemetry data without naming restrictions.
    """

    # Traceloop keys used for extraction
    _TL_MODEL_NAME = "traceloop.association.properties.ls_model_name"
    _TL_PROVIDER = "traceloop.association.properties.ls_provider"

    _GENAI_PROMPT_PREFIX = "gen_ai.prompt."
    _GENAI_COMPLETION_PREFIX = "gen_ai.completion."

    _OPENINFERENCE_PREFIX = "llm."
    _TRACELOOP_PREFIX = "traceloop."

    # OpenInference llm.usage.* attribute keys
    _LLM_USAGE_TOTAL_TOKENS = "llm.usage.total_tokens"
    _LLM_USAGE_INPUT_TOKENS = "llm.usage.input_tokens"
    _LLM_USAGE_PROMPT_TOKENS = "llm.usage.prompt_tokens"
    _LLM_USAGE_OUTPUT_TOKENS = "llm.usage.output_tokens"
    _LLM_USAGE_COMPLETION_TOKENS = "llm.usage.completion_tokens"
    _LLM_USAGE_CACHE_READ_INPUT_TOKENS = "llm.usage.cache_read_input_tokens"

    def __init__(self, wrapped_exporter: SpanExporter):
        """
        Initialize the transformer.

        Args:
            wrapped_exporter: The underlying exporter to wrap
        """
        self.wrapped_exporter = wrapped_exporter
        logger.info(
            "GenAI attribute transformer initialized (minimal normalization enabled)"
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export spans after transforming attributes.

        Args:
            spans: The spans to export

        Returns:
            SpanExportResult from the wrapped exporter
        """
        for span in spans:
            try:
                self._normalize_attributes(span)
            except Exception as e:
                logger.debug(
                    f"Error normalizing GenAI attributes for span {getattr(span, 'name', '<unknown>')}: {e}"
                )

        return self.wrapped_exporter.export(spans)

    def shutdown(self) -> None:
        """Shutdown the wrapped exporter."""
        self.wrapped_exporter.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """
        Force flush the wrapped exporter.

        Args:
            timeout_millis: Timeout in milliseconds (None for default)

        Returns:
            True if flush succeeded
        """
        if timeout_millis is None:
            # Call without timeout to use default
            return self.wrapped_exporter.force_flush()
        return self.wrapped_exporter.force_flush(timeout_millis)

    def _normalize_attributes(self, span: ReadableSpan) -> None:
        """
        Perform minimal normalization on the span's attributes in-place.
        Only removes standard attributes that were transformed, preserving custom/proprietary ones.

        Args:
            span: The span to modify
        """
        if not span.attributes:
            return

        # Access the internal mutable attributes dict
        if not hasattr(span, "_attributes") or span._attributes is None:
            return

        attrs = cast(MutableMapping[str, Any], span._attributes)

        # Only consider spans that have traceloop.* or llm.* or gen_ai.prompt.* or gen_ai.completion.* attributes
        if not any(
            k.startswith(
                (
                    self._TRACELOOP_PREFIX,
                    self._OPENINFERENCE_PREFIX,
                    self._GENAI_PROMPT_PREFIX,
                    self._GENAI_COMPLETION_PREFIX,
                )
            )
            for k in attrs.keys()
        ):
            return

        # Track which specific attributes to remove after transformation
        keys_to_remove = set()

        model_name = attrs.get(self._TL_MODEL_NAME)
        if isinstance(model_name, str) and model_name:
            attrs["gen_ai.request.model"] = model_name
            keys_to_remove.add(self._TL_MODEL_NAME)
            response_model = attrs.get("gen_ai.response.model")
            if not response_model or response_model == "unknown":
                attrs["gen_ai.response.model"] = model_name

        provider = attrs.get(self._TL_PROVIDER)
        if isinstance(provider, str) and provider:
            attrs["gen_ai.provider.name"] = provider
            keys_to_remove.add(self._TL_PROVIDER)

        # Map usage attributes and track which ones were transformed
        keys_to_remove.update(self._map_llm_usage(attrs))

        # Transform messages and collect keys to remove (all gen_ai.prompt.* and gen_ai.completion.*)
        keys_to_remove.update(self._get_message_keys_to_remove(attrs))
        self._transform_messages(attrs)

        # Remove only the specific transformed attributes
        for key in keys_to_remove:
            attrs.pop(key, None)

    def _map_llm_usage(self, attrs: MutableMapping[str, Any]) -> set:
        """
        Map llm.usage.* keys into gen_ai.usage.* keys.

        Returns:
            Set of llm.usage.* keys that were transformed and should be removed
        """
        transformed_keys = set()

        # total tokens
        if self._LLM_USAGE_TOTAL_TOKENS in attrs:
            attrs["gen_ai.usage.total_tokens"] = attrs[self._LLM_USAGE_TOTAL_TOKENS]
            transformed_keys.add(self._LLM_USAGE_TOTAL_TOKENS)

        # input tokens (prefer input_tokens, fallback to prompt_tokens)
        if self._LLM_USAGE_INPUT_TOKENS in attrs:
            attrs["gen_ai.usage.input_tokens"] = attrs[self._LLM_USAGE_INPUT_TOKENS]
            transformed_keys.add(self._LLM_USAGE_INPUT_TOKENS)
        elif self._LLM_USAGE_PROMPT_TOKENS in attrs:
            attrs["gen_ai.usage.input_tokens"] = attrs[self._LLM_USAGE_PROMPT_TOKENS]
            transformed_keys.add(self._LLM_USAGE_PROMPT_TOKENS)

        # output tokens (prefer output_tokens, fallback to completion_tokens)
        if self._LLM_USAGE_OUTPUT_TOKENS in attrs:
            attrs["gen_ai.usage.output_tokens"] = attrs[self._LLM_USAGE_OUTPUT_TOKENS]
            transformed_keys.add(self._LLM_USAGE_OUTPUT_TOKENS)
        elif self._LLM_USAGE_COMPLETION_TOKENS in attrs:
            attrs["gen_ai.usage.output_tokens"] = attrs[
                self._LLM_USAGE_COMPLETION_TOKENS
            ]
            transformed_keys.add(self._LLM_USAGE_COMPLETION_TOKENS)

        # cache read input tokens (optional)
        if self._LLM_USAGE_CACHE_READ_INPUT_TOKENS in attrs:
            attrs["gen_ai.usage.cache_read_input_tokens"] = attrs[
                self._LLM_USAGE_CACHE_READ_INPUT_TOKENS
            ]
            transformed_keys.add(self._LLM_USAGE_CACHE_READ_INPUT_TOKENS)

        return transformed_keys

    def _get_message_keys_to_remove(self, attrs: MutableMapping[str, Any]) -> set:
        """
        Get all gen_ai.prompt.* and gen_ai.completion.* keys that should be removed.
        These are always removed since they're transformed to new format.

        Returns:
            Set of message attribute keys to remove
        """
        keys_to_remove = set()
        for key in attrs:
            if key.startswith(self._GENAI_PROMPT_PREFIX) or key.startswith(
                self._GENAI_COMPLETION_PREFIX
            ):
                keys_to_remove.add(key)
        return keys_to_remove

    def _transform_messages(self, attrs: MutableMapping[str, Any]) -> None:
        """
        Transform old-format gen_ai.prompt.* and gen_ai.completion.* attributes
        to new OTEL semconv 1.39.0 structured format.
        """
        # Transform input messages (gen_ai.prompt.* -> gen_ai.input.messages)
        input_messages = self._collect_indexed_attributes(
            attrs, self._GENAI_PROMPT_PREFIX
        )
        if input_messages:
            structured_input = self._structure_messages(input_messages)
            try:
                # Store as JSON string (OTEL spans may not support structured attributes yet)
                json_str = json.dumps(structured_input)
                attrs["gen_ai.input.messages"] = json_str
            except Exception as e:
                logger.debug(f"Failed to serialize input messages: {e}")

        # Transform output messages (gen_ai.completion.* -> gen_ai.output.messages)
        output_messages = self._collect_indexed_attributes(
            attrs, self._GENAI_COMPLETION_PREFIX
        )
        if output_messages:
            structured_output = self._structure_messages(output_messages)
            try:
                # Store as JSON string (OTEL spans may not support structured attributes yet)
                json_str = json.dumps(structured_output)
                attrs["gen_ai.output.messages"] = json_str
            except Exception as e:
                logger.debug(f"Failed to serialize output messages: {e}")

    def _collect_indexed_attributes(
        self, attrs: MutableMapping[str, Any], prefix: str
    ) -> Dict[int, Dict[str, Any]]:
        """
        Collect indexed attributes like gen_ai.prompt.0.role, gen_ai.prompt.0.content
        into a dictionary keyed by index.

        Args:
            attrs: The attributes dictionary
            prefix: The prefix to match (e.g., "gen_ai.prompt.")

        Returns:
            Dictionary mapping index to message data
        """
        indexed_messages: Dict[int, Dict[str, Any]] = {}

        for key, value in attrs.items():
            if not key.startswith(prefix):
                continue

            # Extract index and field name from key like "gen_ai.prompt.0.role"
            remainder = key[len(prefix) :]
            parts = remainder.split(".", 1)

            if len(parts) != 2:
                continue

            try:
                index = int(parts[0])
                field = parts[1]
            except (ValueError, IndexError):
                continue

            if index not in indexed_messages:
                indexed_messages[index] = {}

            indexed_messages[index][field] = value

        return indexed_messages

    def _structure_messages(
        self, indexed_messages: Dict[int, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert indexed message dictionary to OTEL semconv 1.39.0 structured format.

        Args:
            indexed_messages: Dictionary mapping index to message data

        Returns:
            List of structured messages in OTEL format
        """
        structured = []

        # Sort by index to maintain order
        for index in sorted(indexed_messages.keys()):
            message_data = indexed_messages[index]

            # Extract role (required)
            role = message_data.get("role", "user")

            # Build the structured message
            structured_message: Dict[str, Any] = {"role": role, "parts": []}

            # Handle content field
            if "content" in message_data:
                content = message_data["content"]
                structured_message["parts"].append({"type": "text", "content": content})

            # Handle finish_reason if present (for output messages)
            if "finish_reason" in message_data:
                structured_message["finish_reason"] = message_data["finish_reason"]

            # Handle any other fields that might be present
            for key, value in message_data.items():
                if key not in ("role", "content", "finish_reason"):
                    # Store additional fields at message level
                    structured_message[key] = value

            structured.append(structured_message)

        return structured
