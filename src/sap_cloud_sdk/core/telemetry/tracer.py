"""
Context overlay utilities for application-level instrumentation.

This module provides a simple API for users to create context overlays and add
attributes to traces, complementing the automatic instrumentation provided
by auto_instrument().
"""

from contextlib import contextmanager
from typing import Optional, Dict, Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span

from sap_cloud_sdk.core.telemetry.genai_operation import GenAIOperation
from sap_cloud_sdk.core.telemetry.telemetry import get_tenant_id
from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TENANT_ID

# OpenTelemetry GenAI semantic attribute names (avoid duplicate string literals)
_ATTR_GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
_ATTR_GEN_AI_PROVIDER_NAME = "gen_ai.provider.name"
_ATTR_GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
_ATTR_GEN_AI_TOOL_NAME = "gen_ai.tool.name"
_ATTR_GEN_AI_TOOL_TYPE = "gen_ai.tool.type"
_ATTR_GEN_AI_TOOL_DESCRIPTION = "gen_ai.tool.description"
_ATTR_GEN_AI_AGENT_NAME = "gen_ai.agent.name"
_ATTR_GEN_AI_AGENT_ID = "gen_ai.agent.id"
_ATTR_GEN_AI_AGENT_DESCRIPTION = "gen_ai.agent.description"
_ATTR_GEN_AI_CONVERSATION_ID = "gen_ai.conversation.id"
_ATTR_SERVER_ADDRESS = "server.address"


@contextmanager
def context_overlay(
    name: GenAIOperation,
    *,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    """
    Create a context overlay for tracing GenAI operations.

    Works in both sync and async code. The span is automatically closed
    when exiting the context, and exceptions are automatically recorded.
    This context manager integrates seamlessly with the auto-instrumentation
    provided by auto_instrument(), allowing you to create parent spans that
    wrap auto-instrumented AI framework calls.

    Args:
        name: GenAI operation name following OpenTelemetry semantic conventions.
              Example: GenAIOperation.CHAT, GenAIOperation.EMBEDDINGS
        attributes: Optional custom attributes to add to the span
                   (e.g., {"user.id": "123", "session.id": "abc"})
        kind: Span kind - usually INTERNAL for application code.
              Other options: SERVER, CLIENT, PRODUCER, CONSUMER

    Yields:
        The created span (available for advanced use cases like adding events)

    Examples:
        Basic GenAI operation:
        ```python
        from sap_cloud_sdk.core.telemetry import context_overlay, GenAIOperation

        with context_overlay(GenAIOperation.CHAT):
            response = llm.chat(message)
        ```

        With custom attributes:
        ```python
        with context_overlay(
            name=GenAIOperation.CHAT,
            attributes={"user.id": "123", "session.id": "abc"}
        ):
            response = llm.chat(message)
        ```

        In async code (works the same):
        ```python
        async def handle_request():
            with context_overlay(GenAIOperation.CHAT):
                result = await llm.chat_async(message)
        ```

        Nested spans:
        ```python
        with context_overlay(GenAIOperation.RETRIEVAL):
            documents = retrieve_documents(query)

            with context_overlay(GenAIOperation.CHAT):
                response = llm.chat(documents)
        ```

        Advanced usage with span events:
        ```python
        with context_overlay(GenAIOperation.EMBEDDINGS) as span:
            span.add_event("processing_started")
            embeddings = generate_embeddings(text)
            span.add_event("processing_completed")
        ```
    """
    tracer = trace.get_tracer(__name__)

    # Convert enum to string if needed
    span_name = str(name)

    # Add tenant_id if set
    span_attrs = attributes.copy() if attributes else {}
    span_attrs[_ATTR_GEN_AI_OPERATION_NAME] = span_name
    tenant_id = get_tenant_id()
    if tenant_id:
        span_attrs[ATTR_SAP_TENANT_ID] = tenant_id

    with tracer.start_as_current_span(
        span_name, kind=kind, attributes=span_attrs
    ) as span:
        try:
            yield span
        except Exception as e:
            # Record the exception in the span
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def chat_span(
    model: str,
    provider: str,
    *,
    conversation_id: Optional[str] = None,
    server_address: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Create a span for LLM chat/completion API calls (OpenTelemetry GenAI Inference span).

    Uses span kind CLIENT for external calls to an LLM service. Required
    OpenTelemetry GenAI attributes are set at span creation time. Overriding
    semantic convention keys via the attributes parameter is not recommended.

    See: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/

    Args:
        model: The name of the GenAI model (e.g. "gpt-4").
        provider: The GenAI provider (e.g. "openai", "anthropic"). Set as gen_ai.provider.name.
        conversation_id: Optional. Used to correlate different messages in the same conversation
            (e.g. thread or session ID). Set as gen_ai.conversation.id when provided.
        server_address: Optional server address. If None, server.address is not set.
        attributes: Optional dict of extra attributes to add or override on the span.

    Yields:
        The created Span (e.g. to set gen_ai.usage.input_tokens, gen_ai.response.finish_reason).

    Examples:
        Agentic workflow with chat and tool execution:
        ```python
        from sap_cloud_sdk.core.telemetry import chat_span, execute_tool_span

        with chat_span(model="gpt-4", provider="openai") as span:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "What's the weather?"}],
                tools=[weather_tool]
            )
            span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
            span.set_attribute("gen_ai.response.finish_reason", response.choices[0].finish_reason)

            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                with execute_tool_span(tool_name=tool_call.function.name) as tool_span:
                    result = execute_function(tool_call.function.name, tool_call.function.arguments)
                    tool_span.set_attribute("gen_ai.tool.call.result", result)
        ```
    """
    tracer = trace.get_tracer(__name__)
    span_name = f"chat {model}"
    base_attrs: Dict[str, Any] = {
        _ATTR_GEN_AI_OPERATION_NAME: "chat",
        _ATTR_GEN_AI_PROVIDER_NAME: provider,
        _ATTR_GEN_AI_REQUEST_MODEL: model,
    }
    if conversation_id is not None:
        base_attrs[_ATTR_GEN_AI_CONVERSATION_ID] = conversation_id
    if server_address is not None:
        base_attrs[_ATTR_SERVER_ADDRESS] = server_address
    # Add tenant_id if set
    tenant_id = get_tenant_id()
    if tenant_id:
        base_attrs[ATTR_SAP_TENANT_ID] = tenant_id
    # User attributes first, then base_attrs so required semantic keys are never overridden
    span_attrs = {**(attributes or {}), **base_attrs}

    with tracer.start_as_current_span(
        span_name,
        kind=trace.SpanKind.CLIENT,
        attributes=span_attrs,
    ) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def execute_tool_span(
    tool_name: str,
    *,
    tool_type: Optional[str] = None,
    tool_description: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Create a span for tool execution in agentic workflows (OpenTelemetry GenAI Execute Tool span).

    Uses span kind INTERNAL for in-process tool execution. Required GenAI
    attributes are set at span creation time. Overriding semantic convention
    keys via the attributes parameter is not recommended.

    Args:
        tool_name: The name of the tool being executed.
        tool_type: Optional tool type (e.g. "function").
        tool_description: Optional tool description.
        attributes: Optional dict of extra attributes to add or override on the span.

    Yields:
        The created Span (e.g. to set gen_ai.tool.call.result after execution).

    Examples:
        Inside a chat response loop when handling a tool call:
        ```python
        from sap_cloud_sdk.core.telemetry import execute_tool_span

        with execute_tool_span(tool_name=tool_call.function.name) as tool_span:
            result = execute_function(tool_call.function.name, tool_call.function.arguments)
            tool_span.set_attribute("gen_ai.tool.call.result", result)
        ```
    """
    tracer = trace.get_tracer(__name__)
    span_name = f"execute_tool {tool_name}"
    base_attrs: Dict[str, Any] = {
        _ATTR_GEN_AI_OPERATION_NAME: "execute_tool",
        _ATTR_GEN_AI_TOOL_NAME: tool_name,
    }
    if tool_type is not None:
        base_attrs[_ATTR_GEN_AI_TOOL_TYPE] = tool_type
    if tool_description is not None:
        base_attrs[_ATTR_GEN_AI_TOOL_DESCRIPTION] = tool_description
    # Add tenant_id if set
    tenant_id = get_tenant_id()
    if tenant_id:
        base_attrs[ATTR_SAP_TENANT_ID] = tenant_id
    # User attributes first, then base_attrs so required semantic keys are never overridden
    span_attrs = {**(attributes or {}), **base_attrs}

    with tracer.start_as_current_span(
        span_name,
        kind=trace.SpanKind.INTERNAL,
        attributes=span_attrs,
    ) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def invoke_agent_span(
    provider: str,
    *,
    agent_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_description: Optional[str] = None,
    conversation_id: Optional[str] = None,
    server_address: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.CLIENT,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Create a span for GenAI agent invocation (OpenTelemetry GenAI Invoke agent span).

    Represents an instance of an agent invocation. Span kind is CLIENT by default
    (remote agents); use kind=INTERNAL for in-process agents (e.g. LangChain, CrewAI).
    Required OpenTelemetry GenAI attributes are set at span creation time.
    Overriding semantic convention keys via the attributes parameter is not recommended.

    See: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/

    Args:
        provider: The GenAI provider (e.g. "openai", "anthropic"). Set as gen_ai.provider.name.
        agent_name: Optional human-readable name of the agent (e.g. "Math Tutor").
        agent_id: Optional unique identifier of the GenAI agent.
        agent_description: Optional free-form description of the agent.
        conversation_id: Optional. Used to correlate different messages in the same conversation
            (e.g. thread or session ID). Set as gen_ai.conversation.id when provided.
        server_address: Optional server address. If None, server.address is not set.
        kind: Span kind; CLIENT for remote agents, INTERNAL for in-process.
        attributes: Optional dict of extra attributes to add or override on the span.

    Yields:
        The created Span (e.g. to set usage, response attributes).

    Examples:
        Remote agent (e.g. OpenAI Assistants API):
        ```python
        from sap_cloud_sdk.core.telemetry import invoke_agent_span

        with invoke_agent_span(provider="openai", agent_name="SupportBot", server_address="api.openai.com"):
            response = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=asst_id)
        ```

        In-process agent (e.g. LangChain):
        ```python
        with invoke_agent_span(provider="openai", agent_name="Chain", kind=trace.SpanKind.INTERNAL):
            result = agent.invoke({"input": user_input})
        ```
    """
    tracer = trace.get_tracer(__name__)
    span_name = f"invoke_agent {agent_name}" if agent_name else "invoke_agent"
    base_attrs: Dict[str, Any] = {
        _ATTR_GEN_AI_OPERATION_NAME: "invoke_agent",
        _ATTR_GEN_AI_PROVIDER_NAME: provider,
    }
    if agent_name is not None:
        base_attrs[_ATTR_GEN_AI_AGENT_NAME] = agent_name
    if agent_id is not None:
        base_attrs[_ATTR_GEN_AI_AGENT_ID] = agent_id
    if agent_description is not None:
        base_attrs[_ATTR_GEN_AI_AGENT_DESCRIPTION] = agent_description
    if conversation_id is not None:
        base_attrs[_ATTR_GEN_AI_CONVERSATION_ID] = conversation_id
    if server_address is not None:
        base_attrs[_ATTR_SERVER_ADDRESS] = server_address
    # Add tenant_id if set
    tenant_id = get_tenant_id()
    if tenant_id:
        base_attrs[ATTR_SAP_TENANT_ID] = tenant_id
    # User attributes first, then base_attrs so required semantic keys are never overridden
    span_attrs = {**(attributes or {}), **base_attrs}

    with tracer.start_as_current_span(
        span_name,
        kind=kind,
        attributes=span_attrs,
    ) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def get_current_span() -> Span:
    """
    Get the currently active span.

    Returns the span that is currently active in the execution context.
    If no span is active, returns a non-recording span (safe to use but
    won't record any data).

    Returns:
        Current active span, or a non-recording span if none is active

    Examples:
        Add attributes to the current span:
        ```python
        span = get_current_span()
        span.set_attribute("custom.value", 42)
        span.add_event("milestone_reached")
        ```

        Check if span is recording:
        ```python
        span = get_current_span()
        if span.is_recording():
            # Span is active and recording
            span.set_attribute("debug.info", debug_data)
        ```
    """
    return trace.get_current_span()


def add_span_attribute(key: str, value: Any) -> None:
    """
    Add an attribute to the current active span.

    This is a convenience function that adds an attribute to whatever
    span is currently active in the execution context. If no span is
    active, this function does nothing (safe to call).

    Args:
        key: Attribute key. Recommend using namespacing (e.g., "app.user.id")
        value: Attribute value. Can be str, int, float, bool, or sequences of these types

    Examples:
        Add various attribute types:
        ```python
        add_span_attribute("request.id", request_id)
        add_span_attribute("user.role", "admin")
        add_span_attribute("item.count", 42)
        add_span_attribute("feature.enabled", True)
        add_span_attribute("tags", ["important", "urgent"])
        ```

        Use within a context overlay:
        ```python
        with context_overlay(GenAIOperation.EMBEDDINGS):
            data = load_data()
            add_span_attribute("data.size", len(data))

            result = process(data)
            add_span_attribute("result.status", "success")
        ```
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(key, value)
