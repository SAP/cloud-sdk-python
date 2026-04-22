"""
Context overlay utilities for application-level instrumentation.

This module provides a simple API for users to create context overlays and add
attributes to traces, complementing the automatic instrumentation provided
by auto_instrument().
"""

from contextlib import contextmanager, nullcontext
from typing import Optional, Dict, Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span

from sap_cloud_sdk.core.telemetry.genai_operation import GenAIOperation
from sap_cloud_sdk.core.telemetry.telemetry import (
    get_tenant_id,
    get_propagated_attributes,
    _propagated_attrs_var,
    _invoke_agent_identity_var,
)
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
def _propagate_attributes(attrs: Dict[str, Any]):
    """Push attrs onto the propagation stack for the duration of the context."""
    current = _propagated_attrs_var.get()
    merged = {**current, **attrs}
    token = _propagated_attrs_var.set(merged)
    try:
        yield
    finally:
        _propagated_attrs_var.reset(token)


@contextmanager
def _invoke_agent_identity_scope(span_attrs: Dict[str, Any]):
    """Push gen_ai.agent.{name,id,description} onto a ContextVar for the duration of the context.

    Third-party instrumentations create spans without merging :func:`get_propagated_attributes`.
    :class:`~sap_cloud_sdk.core.telemetry.invoke_agent_identity_processor.InvokeAgentIdentitySpanProcessor`
    (registered by :func:`sap_cloud_sdk.core.telemetry.auto_instrument.auto_instrument`) copies these
    values onto every started span while the scope is active, without using W3C Baggage.
    """
    keys = (
        _ATTR_GEN_AI_AGENT_NAME,
        _ATTR_GEN_AI_AGENT_ID,
        _ATTR_GEN_AI_AGENT_DESCRIPTION,
    )
    patch_dict = {k: str(span_attrs[k]) for k in keys if span_attrs.get(k) is not None}
    if not patch_dict:
        yield
        return
    prev = _invoke_agent_identity_var.get()
    merged: Dict[str, str] = {**(prev or {}), **patch_dict}
    token = _invoke_agent_identity_var.set(merged)
    try:
        yield
    finally:
        _invoke_agent_identity_var.reset(token)


@contextmanager
def context_overlay(
    name: GenAIOperation,
    *,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    propagate: bool = False,
):
    """
    Create a context overlay for tracing GenAI operations.

    Args:
        name: GenAI operation name following OpenTelemetry semantic conventions.
              Example: GenAIOperation.CHAT, GenAIOperation.EMBEDDINGS
        attributes: Optional custom attributes to add to the span
                   (e.g., {"user.id": "123", "session.id": "abc"})
        kind: Span kind - usually INTERNAL for application code.
              Other options: SERVER, CLIENT, PRODUCER, CONSUMER
        propagate: If True, this span's attributes are passed to all nested spans
                   within its scope as the lowest-priority layer.

    Yields:
        The created span (available for advanced use cases like adding events)

    Example:
        ```python
        with context_overlay(GenAIOperation.CHAT, attributes={"user.id": "123"}):
            response = llm.chat(message)
        ```
    """
    tracer = trace.get_tracer(__name__)

    # Convert enum to string if needed
    span_name = str(name)

    # Merge propagated attrs (lowest priority), then user attrs, then required attrs
    propagated = get_propagated_attributes()
    span_attrs = {**propagated, **(attributes or {})}
    span_attrs[_ATTR_GEN_AI_OPERATION_NAME] = span_name
    tenant_id = get_tenant_id()
    if tenant_id:
        span_attrs[ATTR_SAP_TENANT_ID] = tenant_id

    ctx = _propagate_attributes(span_attrs) if propagate else nullcontext()
    with ctx:
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
    propagate: bool = False,
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
        propagate: If True, this span's attributes are passed to all nested spans
                   within its scope as the lowest-priority layer.

    Yields:
        The created Span (e.g. to set gen_ai.usage.input_tokens, gen_ai.response.finish_reason).

    Example:
        ```python
        with chat_span(model="gpt-4", provider="openai", conversation_id="cid") as span:
            response = client.chat.completions.create(...)
            span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
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
    # Propagated attrs (lowest), user attrs, required semantic keys (highest)
    propagated = get_propagated_attributes()
    span_attrs = {**propagated, **(attributes or {}), **base_attrs}

    ctx = _propagate_attributes(span_attrs) if propagate else nullcontext()
    with ctx:
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
    propagate: bool = False,
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
        propagate: If True, this span's attributes are passed to all nested spans
                   within its scope as the lowest-priority layer.

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
    # Propagated attrs (lowest), user attrs, required semantic keys (highest)
    propagated = get_propagated_attributes()
    span_attrs = {**propagated, **(attributes or {}), **base_attrs}

    ctx = _propagate_attributes(span_attrs) if propagate else nullcontext()
    with ctx:
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
    propagate: bool = False,
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
        propagate: If True, this span's attributes are passed to all nested spans
                   within its scope as the lowest-priority layer. Additionally,
                   ``gen_ai.agent.{name,id,description}`` are stored in a ContextVar and
                   copied onto every nested span by
                   :class:`~sap_cloud_sdk.core.telemetry.invoke_agent_identity_processor.InvokeAgentIdentitySpanProcessor`
                   when it is registered (e.g. via :func:`sap_cloud_sdk.core.telemetry.auto_instrument.auto_instrument`).

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
    # Propagated attrs (lowest), user attrs, required semantic keys (highest)
    propagated = get_propagated_attributes()
    span_attrs = {**propagated, **(attributes or {}), **base_attrs}

    ctx_prop = _propagate_attributes(span_attrs) if propagate else nullcontext()
    ctx_identity = (
        _invoke_agent_identity_scope(span_attrs) if propagate else nullcontext()
    )
    with ctx_prop:
        with ctx_identity:
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
