"""Step definitions for telemetry.feature."""

import logging
import os
from collections.abc import Sequence

from langchain_core.messages import HumanMessage
from opentelemetry import baggage, context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pytest_bdd import given, parsers, scenario, then, when
import pytest

from sap_cloud_sdk.core.telemetry.tracer import (
    execute_tool_span,
    invoke_agent_span,
)
from ._agent import build_langgraph_agent

log = logging.getLogger(__name__)

# --- scenario bindings ---


@scenario("telemetry.feature", "invoke_agent_span emits a span with required GenAI attributes")
def test_invoke_agent_required_attributes():
    pass


@scenario("telemetry.feature", "invoke_agent_span records errors")
def test_invoke_agent_records_errors():
    pass


@scenario("telemetry.feature", "spans carry SDK resource attributes")
def test_sdk_resource_attributes():
    pass


@scenario("telemetry.feature", "invoke_agent_span wrapping a real LLM call produces a complete trace")
def test_invoke_agent_wrapping_llm():
    pass


@scenario("telemetry.feature", "invoke_agent_span wrapping LLM call then tool produces a full agentic trace")
def test_invoke_agent_llm_then_tool():
    pass


@scenario("telemetry.feature", "propagate=True flows invoke_agent attributes to nested LLM span")
def test_propagate_true_to_llm_span():
    pass


@scenario("telemetry.feature", "propagate=False does not leak invoke_agent attributes to nested LLM span")
def test_propagate_false_to_llm_span():
    pass


@scenario("telemetry.feature", "baggage attributes propagate to Traceloop-instrumented LLM spans")
def test_baggage_propagates_to_llm_span():
    pass


@scenario("telemetry.feature", "LangGraph agent run produces an invoke_agent span with LangChain child spans")
def test_langgraph_auto_instrumentation():
    pass


# --- shared state ---


@pytest.fixture
def span_store():
    return {}


# --- given steps ---


@given("auto_instrument is initialized")
def auto_instrument_initialized(memory_exporter, transforming_exporter):
    pass


@given("AI Core is configured via set_aicore_config")
def aicore_configured_step(aicore_configured):
    pass


@given(parsers.parse('baggage key "{key}" is set to "{value}"'))
def set_baggage(key, value):
    token = context.attach(baggage.set_baggage(key, value))
    yield
    context.detach(token)


# --- when steps ---


@when(parsers.parse('I invoke an agent with provider "{provider}" and name "{name}" and conversation_id "{cid}"'))
def invoke_agent_full(provider, name, cid, memory_exporter, span_store):
    with invoke_agent_span(provider=provider, agent_name=name, conversation_id=cid):
        pass
    span_store["last"] = _require_span(memory_exporter, f"invoke_agent {name}")


@when("I invoke an agent that raises an exception")
def invoke_agent_with_error(memory_exporter, span_store):
    with pytest.raises(RuntimeError):
        with invoke_agent_span(provider="test", agent_name="error-agent"):
            raise RuntimeError("deliberate test error")
    span_store["last"] = _require_span(memory_exporter, "invoke_agent error-agent")


@when(parsers.parse('I invoke an agent with provider "{provider}" and name "{name}"'))
def invoke_agent_named(provider, name, memory_exporter, span_store):
    with invoke_agent_span(provider=provider, agent_name=name):
        pass
    span_store["last"] = _require_span(memory_exporter, f"invoke_agent {name}")


def _llm_call():
    """Make a real LLM call via AI Core using LangChain's LiteLLM integration.

    Uses ChatLiteLLM so Traceloop's LangChain instrumentor fires and emits a span
    with gen_ai.usage.* token counts.
    """
    from langchain_litellm import ChatLiteLLM
    from langchain_core.messages import HumanMessage as LCHumanMessage
    model_name = os.environ.get("AICORE_MODEL", "anthropic--claude-4.5-sonnet")
    llm = ChatLiteLLM(model=f"sap/{model_name}")
    llm.invoke([LCHumanMessage(content="Say hi in one word.")])


@when("I invoke an agent wrapping a direct LLM call")
def invoke_agent_wrapping_llm(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(provider="sap-aicore", agent_name="llm-agent"):
        _llm_call()
    spans = transforming_exporter.get_finished_spans()
    _log_spans(spans)
    span_store["all_local_spans"] = spans


@when("I invoke an agent that calls an LLM then executes a tool")
def invoke_agent_llm_then_tool(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(provider="sap-aicore", agent_name="agent-with-tool"):
        _llm_call()
        with execute_tool_span(tool_name="search", tool_type="function"):
            pass
    spans = transforming_exporter.get_finished_spans()
    _log_spans(spans)
    span_store["all_local_spans"] = spans


@when("I invoke an agent with propagate=True wrapping a real LLM call")
def invoke_agent_propagate_to_llm(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(
        provider="sap-aicore",
        agent_name="propagate-llm-agent",
        attributes={"custom.session": "s42"},
        propagate=True,
    ):
        _llm_call()
    spans = transforming_exporter.get_finished_spans()
    _log_spans(spans)
    span_store["all_local_spans"] = spans


@when("I invoke an agent with propagate=False wrapping a real LLM call")
def invoke_agent_no_propagate_to_llm(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(
        provider="sap-aicore",
        agent_name="no-propagate-llm-agent",
        attributes={"custom.session": "s42"},
        propagate=False,
    ):
        _llm_call()
    spans = transforming_exporter.get_finished_spans()
    _log_spans(spans)
    span_store["all_local_spans"] = spans


@when("I invoke an agent wrapping a direct LLM call with baggage")
def invoke_agent_wrapping_llm_with_baggage(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(provider="sap-aicore", agent_name="baggage-llm-agent"):
        _llm_call()
    spans = transforming_exporter.get_finished_spans()
    _log_spans(spans)
    span_store["all_local_spans"] = spans


@when(parsers.parse('I run a LangGraph agent with provider "{provider}" and name "{name}"'))
def run_langgraph_agent(provider, name, transforming_exporter, span_store):
    agent = build_langgraph_agent()
    with invoke_agent_span(provider=provider, agent_name=name) as root_span:
        ctx = root_span.get_span_context()
        assert ctx is not None
        span_store["root_span_id"] = ctx.span_id
        agent.invoke({"messages": [HumanMessage(content="Say hello in one word.")]})
    all_spans = transforming_exporter.get_finished_spans()
    _log_spans(all_spans)
    span_store["all_spans"] = all_spans
    span_store["last"] = _require_span_in(all_spans, f"invoke_agent {name}")


# --- then steps ---


@then(parsers.parse('a span named "{name}" is recorded'))
def span_named_is_recorded(name, memory_exporter, span_store):
    spans = span_store.get("all_spans") or memory_exporter.get_finished_spans()
    span = _find_span_in(spans, name)
    assert span is not None, f"No span named '{name}' found. Available: {[s.name for s in spans]}"
    span_store["last"] = span


@then(parsers.parse('the span has attribute "{key}" equal to "{value}"'))
def span_has_attribute(key, value, span_store):
    span = span_store["last"]
    actual = span.attributes.get(key)
    assert actual == value, f"Expected span attribute '{key}' == '{value}', got {actual!r}"


@then("the span status is ERROR")
def span_status_is_error(span_store):
    span = span_store["last"]
    assert span.status.status_code == StatusCode.ERROR, (
        f"Expected ERROR status, got {span.status.status_code}"
    )


@then("the span has an exception event")
def span_has_exception_event(span_store):
    span = span_store["last"]
    event_names = [e.name for e in span.events]
    assert "exception" in event_names, f"No exception event found. Events: {event_names}"


@then(parsers.parse('the span resource has attribute "{key}" equal to "{value}"'))
def span_resource_attr_equals(key, value, span_store):
    span = span_store["last"]
    actual = span.resource.attributes.get(key)
    assert actual == value, f"Expected resource attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('the span resource has attribute "{key}" set'))
def span_resource_attr_set(key, span_store):
    span = span_store["last"]
    actual = span.resource.attributes.get(key)
    assert actual, f"Expected resource attribute '{key}' to be set, got {actual!r}"


@then(parsers.parse('at least one descendant span with attribute "{key}" equal to "{value}" is recorded'))
def descendant_with_attribute_equals(key, value, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    match = next((s for s in descendants if s.attributes and s.attributes.get(key) == value), None)
    assert match is not None, (
        f"No descendant span with {key}={value!r}. "
        f"Descendants: {[(s.name, dict(s.attributes or {})) for s in descendants]}"
    )


@then(parsers.parse('at least one descendant span has attribute "{key}" set'))
def descendant_has_attribute_set(key, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    match = next((s for s in descendants if s.attributes and s.attributes.get(key)), None)
    assert match is not None, (
        f"No descendant span with attribute '{key}' set. "
        f"Descendants: {[(s.name, dict(s.attributes or {})) for s in descendants]}"
    )


@then(parsers.parse('no descendant span has an attribute starting with "{prefix}"'))
def no_descendant_has_attribute_prefix(prefix, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    violations = [(s.name, k) for s in descendants for k in (s.attributes or {}) if k.startswith(prefix)]
    assert not violations, f"Found raw attribute(s) with prefix '{prefix}' that should have been transformed: {violations}"


@then(parsers.parse('no descendant span has attribute "{key}"'))
def no_descendant_has_exact_attribute(key, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    violations = [s.name for s in descendants if key in (s.attributes or {})]
    assert not violations, f"Attribute '{key}' should have been transformed away but found on: {violations}"


@then(parsers.parse('the span "{name}" is a child of "{parent_name}"'))
def span_is_child_of(name, parent_name, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    child = _find_span_in(spans, name)
    parent = _find_span_in(spans, parent_name)
    assert child is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    assert parent is not None, f"Span '{parent_name}' not found. Available: {[s.name for s in spans]}"
    parent_id = _span_id(parent)
    assert child.parent is not None and child.parent.span_id == parent_id, (
        f"Span '{name}' is not a child of '{parent_name}'. "
        f"child.parent={child.parent}, expected span_id={parent_id}"
    )


@then(parsers.parse('the span "{name}" has attribute "{key}" equal to "{value}"'))
def named_span_has_attribute(name, key, value, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    span = _find_span_in(spans, name)
    assert span is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    actual = span.attributes.get(key) if span.attributes else None
    assert str(actual) == value, f"Expected span '{name}' attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('a span with operation "{operation}" is a child of "{parent_name}"'))
def span_with_operation_is_child_of(operation, parent_name, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    parent = _find_span_in(spans, parent_name)
    assert parent is not None, f"Parent span '{parent_name}' not found. Available: {[s.name for s in spans]}"
    parent_id = _span_id(parent)
    child = next(
        (s for s in spans
         if (s.attributes or {}).get("gen_ai.operation.name") == operation
         and s.parent is not None and s.parent.span_id == parent_id),
        None,
    )
    assert child is not None, (
        f"No span with gen_ai.operation.name='{operation}' found as child of '{parent_name}'. "
        f"Spans: {[(s.name, (s.attributes or {}).get('gen_ai.operation.name')) for s in spans]}"
    )
    span_store["op_span"] = child


@then(parsers.parse('that span has attribute "{key}" equal to "{value}"'))
def op_span_has_attribute_equals(key, value, span_store):
    span = span_store["op_span"]
    actual = (span.attributes or {}).get(key)
    assert str(actual) == value, f"Expected attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('that span has attribute "{key}" set'))
def op_span_has_attribute_set(key, span_store):
    span = span_store["op_span"]
    actual = (span.attributes or {}).get(key)
    assert actual is not None, f"Expected attribute '{key}' to be set on span '{span.name}', got None"


@then(parsers.parse('that span does not have attribute "{key}"'))
def op_span_lacks_attribute(key, span_store):
    span = span_store["op_span"]
    actual = (span.attributes or {}).get(key)
    assert actual is None, f"Expected attribute '{key}' to be absent from '{span.name}', got {actual!r}"


@then(parsers.parse('the span "{name}" has resource attribute "{key}" equal to "{value}"'))
def named_span_resource_attr_equals(name, key, value, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    span = _find_span_in(spans, name)
    assert span is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    actual = span.resource.attributes.get(key)
    assert actual == value, f"Expected span '{name}' resource attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('the span "{name}" has resource attribute "{key}" set'))
def named_span_resource_attr_set(name, key, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    span = _find_span_in(spans, name)
    assert span is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    actual = span.resource.attributes.get(key)
    assert actual, f"Expected span '{name}' resource attribute '{key}' to be set, got {actual!r}"


# --- helpers ---


def _find_span(exporter: InMemorySpanExporter, name: str) -> ReadableSpan | None:
    return _find_span_in(exporter.get_finished_spans(), name)


def _require_span(exporter: InMemorySpanExporter, name: str) -> ReadableSpan:
    spans = exporter.get_finished_spans()
    return _require_span_in(spans, name)


def _find_span_in(spans: Sequence[ReadableSpan], name: str) -> ReadableSpan | None:
    return next((s for s in spans if s.name == name), None)


def _require_span_in(spans: Sequence[ReadableSpan], name: str) -> ReadableSpan:
    span = _find_span_in(spans, name)
    assert span is not None, (
        f"No span named '{name}' found.\n"
        f"Recorded spans: {[s.name for s in spans]}"
    )
    return span


def _log_spans(spans: Sequence[ReadableSpan]) -> None:
    log.info("Collected %d span(s):", len(spans))
    for s in spans:
        log.info("  [%s] attrs=%s", s.name, dict(s.attributes or {}))


def _get_descendants(all_spans: Sequence[ReadableSpan], root_span_id: int) -> list[ReadableSpan]:
    return [
        s for s in all_spans
        if _span_id(s) != root_span_id
        and _is_descendant(s, root_span_id, all_spans)
    ]


def _span_id(span: ReadableSpan) -> int:
    ctx = span.get_span_context()
    assert ctx is not None
    return ctx.span_id


def _is_descendant(span: ReadableSpan, ancestor_id: int, all_spans: Sequence[ReadableSpan]) -> bool:
    current: ReadableSpan | None = span
    visited: set[int] = set()
    while current is not None and current.parent is not None:
        parent_id = current.parent.span_id
        if parent_id in visited:
            break
        visited.add(parent_id)
        if parent_id == ancestor_id:
            return True
        current = next(
            (s for s in all_spans if _span_id(s) == parent_id),
            None,
        )
    return False
