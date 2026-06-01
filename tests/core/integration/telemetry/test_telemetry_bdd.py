"""Step definitions for telemetry.feature."""

import logging
import os

import pytest
from langchain_core.messages import HumanMessage
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pytest_bdd import given, parsers, scenario, then, when

from sap_cloud_sdk.core.telemetry.tracer import (
    add_span_attribute,
    execute_tool_span,
    invoke_agent_span,
)
from ._agent import build_langgraph_agent

log = logging.getLogger(__name__)

# --- scenario bindings ---


@scenario("telemetry.feature", "invoke_agent_span emits a span with required GenAI attributes")
def test_invoke_agent_required_attributes():
    pass


@scenario("telemetry.feature", "invoke_agent_span without optional fields")
def test_invoke_agent_no_optional_fields():
    pass


@scenario("telemetry.feature", "invoke_agent_span records errors")
def test_invoke_agent_records_errors():
    pass


@scenario("telemetry.feature", "spans carry SDK resource attributes")
def test_sdk_resource_attributes():
    pass


@scenario("telemetry.feature", "spans carry environment resource attributes")
def test_env_resource_attributes():
    pass


@scenario("telemetry.feature", "propagate=True flows attributes to child spans via ContextVar")
def test_propagate_true():
    pass


@scenario("telemetry.feature", "propagate=False does not leak attributes to child spans")
def test_propagate_false():
    pass


@scenario("telemetry.feature", "baggage attributes appear on spans")
def test_baggage_attributes():
    pass


@scenario("telemetry.feature", "add_span_attribute adds a custom attribute to the active span")
def test_add_span_attribute():
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
    """Mutable dict to pass spans between when/then steps."""
    return {}


# --- given steps ---


@given("auto_instrument is initialized")
def auto_instrument_initialized(memory_exporter, transforming_exporter):
    # Requesting both exporters ensures auto_instrument() has run and both
    # processors are registered before any spans are emitted.
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
    span = _find_span(memory_exporter, f"invoke_agent {name}")
    log.info("Emitted span: %s | attributes: %s", span.name, dict(span.attributes or {}))
    span_store["last"] = span


@when(parsers.parse('I invoke an agent with provider "{provider}" only'))
def invoke_agent_minimal(provider, memory_exporter, span_store):
    with invoke_agent_span(provider=provider):
        pass
    span = _find_span(memory_exporter, "invoke_agent")
    log.info("Emitted span: %s | attributes: %s", span.name, dict(span.attributes or {}))
    span_store["last"] = span


@when(parsers.parse('I invoke an agent with provider "{provider}" and name "{name}"'))
def invoke_agent_named(provider, name, memory_exporter, span_store):
    with invoke_agent_span(provider=provider, agent_name=name):
        pass
    span = _find_span(memory_exporter, f"invoke_agent {name}")
    log.info("Emitted span: %s | attributes: %s", span.name, dict(span.attributes or {}))
    span_store["last"] = span


@when("I invoke an agent that raises an exception")
def invoke_agent_with_error(memory_exporter, span_store):
    with pytest.raises(RuntimeError):
        with invoke_agent_span(provider="test", agent_name="error-agent"):
            raise RuntimeError("deliberate test error")
    span = _find_span(memory_exporter, "invoke_agent error-agent")
    log.info("Emitted span: %s | status: %s | events: %s", span.name, span.status.status_code, [e.name for e in span.events])
    span_store["last"] = span


@when(parsers.parse('I invoke an agent with propagate={propagate} and attribute "{key}" equal to "{value}"'))
def invoke_agent_with_propagation(propagate, key, value, memory_exporter, span_store):
    do_propagate = propagate.strip() == "True"
    with invoke_agent_span(
        provider="test",
        agent_name="propagation-test",
        attributes={key: value},
        propagate=do_propagate,
    ):
        with trace.get_tracer("test").start_as_current_span("child-span"):
            pass
    child = _find_span(memory_exporter, "child-span")
    log.info("Child span attributes: %s", dict(child.attributes or {}))
    span_store["child"] = child


@when("I invoke an agent and add a custom attribute mid-span")
def invoke_agent_add_custom_attr(memory_exporter, span_store):
    with invoke_agent_span(provider="test", agent_name="custom-attr-agent"):
        add_span_attribute("custom.response.tokens", 42)
    span = _find_span(memory_exporter, "invoke_agent custom-attr-agent")
    log.info("Emitted span: %s | attributes: %s", span.name, dict(span.attributes or {}))
    span_store["last"] = span


def _llm_call():
    """Make a minimal real LLM call via AI Core using LangChain's LiteLLM integration.

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
    log.info("Emitted spans: %s", [(s.name, dict(s.attributes or {})) for s in spans])
    span_store["all_local_spans"] = spans


@when("I invoke an agent that calls an LLM then executes a tool")
def invoke_agent_llm_then_tool(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(provider="sap-aicore", agent_name="agent-with-tool"):
        _llm_call()
        with execute_tool_span(tool_name="search", tool_type="function"):
            pass
    spans = transforming_exporter.get_finished_spans()
    log.info("Emitted spans: %s", [(s.name, dict(s.attributes or {})) for s in spans])
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
    log.info("Emitted spans: %s", [(s.name, dict(s.attributes or {})) for s in spans])
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
    log.info("Emitted spans: %s", [(s.name, dict(s.attributes or {})) for s in spans])
    span_store["all_local_spans"] = spans


@when("I invoke an agent wrapping a direct LLM call with baggage")
def invoke_agent_wrapping_llm_with_baggage(memory_exporter, transforming_exporter, span_store):
    with invoke_agent_span(provider="sap-aicore", agent_name="baggage-llm-agent"):
        _llm_call()
    spans = transforming_exporter.get_finished_spans()
    log.info("Emitted spans: %s", [(s.name, dict(s.attributes or {})) for s in spans])
    span_store["all_local_spans"] = spans


@when(parsers.parse('I run a LangGraph agent with provider "{provider}" and name "{name}"'))
def run_langgraph_agent(provider, name, transforming_exporter, span_store):
    agent = build_langgraph_agent()
    with invoke_agent_span(provider=provider, agent_name=name) as root_span:
        span_store["root_span_id"] = root_span.get_span_context().span_id
        agent.invoke({"messages": [HumanMessage(content="Say hello in one word.")]})
    all_spans = transforming_exporter.get_finished_spans()
    log.info("All spans emitted (%d):", len(all_spans))
    for s in all_spans:
        log.info("  [%s] %s | attrs: %s", s.get_span_context().span_id, s.name, dict(s.attributes or {}))
    span_store["all_spans"] = all_spans
    span_store["last"] = _find_span_in(all_spans, f"invoke_agent {name}")


# --- then steps ---


@then(parsers.parse('a span named "{name}" is recorded'))
def span_named_is_recorded(name, memory_exporter, span_store):
    spans = span_store.get("all_spans") or memory_exporter.get_finished_spans()
    log.info("Checking for span named '%s' among: %s", name, [s.name for s in spans])
    span = _find_span_in(spans, name)
    assert span is not None, f"No span named '{name}' found. Spans: {[s.name for s in spans]}"
    span_store["last"] = span


@then(parsers.parse('the span has attribute "{key}" equal to "{value}"'))
def span_has_attribute(key, value, span_store):
    span = span_store["last"]
    actual = span.attributes.get(key)
    log.info("Checking span '%s': '%s' == '%s' (actual: %r)", span.name, key, value, actual)
    assert actual == value, f"Expected span attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('the span has attribute "{key}" set'))
def span_has_attribute_set(key, span_store):
    span = span_store["last"]
    actual = (span.attributes or {}).get(key)
    log.info("Checking span '%s': '%s' is set (actual: %r)", span.name, key, actual)
    assert actual is not None, f"Expected span attribute '{key}' to be set, got None"


@then(parsers.parse('the span does not have attribute "{key}"'))
def span_lacks_attribute(key, span_store):
    span = span_store["last"]
    log.info("Checking span '%s' does NOT have attribute '%s' (attrs: %s)", span.name, key, list((span.attributes or {}).keys()))
    assert key not in (span.attributes or {}), (
        f"Expected span to NOT have attribute '{key}', but it was present"
    )


@then("the span status is ERROR")
def span_status_is_error(span_store):
    span = span_store["last"]
    log.info("Checking span '%s' status: %s", span.name, span.status.status_code)
    assert span.status.status_code == StatusCode.ERROR, (
        f"Expected ERROR status, got {span.status.status_code}"
    )


@then("the span has an exception event")
def span_has_exception_event(span_store):
    span = span_store["last"]
    event_names = [e.name for e in span.events]
    log.info("Checking span '%s' events: %s", span.name, event_names)
    assert "exception" in event_names, f"No exception event found. Events: {event_names}"


@then(parsers.parse('the span resource has attribute "{key}" equal to "{value}"'))
def span_resource_attr_equals(key, value, span_store):
    span = span_store["last"]
    actual = span.resource.attributes.get(key)
    log.info("Checking span '%s' resource: '%s' == '%s' (actual: %r)", span.name, key, value, actual)
    assert actual == value, f"Expected resource attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('the span resource has attribute "{key}" set'))
def span_resource_attr_set(key, span_store):
    span = span_store["last"]
    actual = span.resource.attributes.get(key)
    log.info("Checking span '%s' resource: '%s' is set (actual: %r)", span.name, key, actual)
    assert actual, f"Expected resource attribute '{key}' to be set, got {actual!r}"


@then(parsers.parse('the child span has attribute "{key}" equal to "{value}"'))
def child_span_has_attribute(key, value, span_store):
    child = span_store["child"]
    assert child is not None, "No child span was recorded"
    actual = child.attributes.get(key)
    log.info("Checking child span '%s': '%s' == '%s' (actual: %r)", child.name, key, value, actual)
    assert actual == value, (
        f"Expected child span attribute '{key}' == '{value}', got {actual!r}"
    )


@then(parsers.parse('the child span does not have attribute "{key}"'))
def child_span_lacks_attribute(key, span_store):
    child = span_store["child"]
    assert child is not None, "No child span was recorded"
    log.info("Checking child span '%s' does NOT have '%s' (attrs: %s)", child.name, key, list((child.attributes or {}).keys()))
    assert key not in (child.attributes or {}), (
        f"Expected child span to NOT have attribute '{key}', but it was present"
    )


@then(parsers.parse('at least one descendant span with attribute "{key}" equal to "{value}" is recorded'))
def descendant_with_attribute_equals(key, value, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    log.info("Checking descendants for %s=%r among %d spans", key, value, len(descendants))
    for s in descendants:
        log.info("  [%s] %s=%r", s.name, key, (s.attributes or {}).get(key))
    match = next(
        (s for s in descendants if s.attributes and s.attributes.get(key) == value),
        None,
    )
    assert match is not None, (
        f"No descendant span with {key}={value!r}. "
        f"Descendants: {[(s.name, dict(s.attributes or {})) for s in descendants]}"
    )


@then(parsers.parse('at least one descendant span has attribute "{key}" set'))
def descendant_has_attribute_set(key, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    log.info("Checking descendants for '%s' set among %d spans", key, len(descendants))
    for s in descendants:
        log.info("  [%s] %s=%r", s.name, key, (s.attributes or {}).get(key))
    match = next(
        (s for s in descendants if s.attributes and s.attributes.get(key)),
        None,
    )
    assert match is not None, (
        f"No descendant span with attribute '{key}' set. "
        f"Descendants: {[(s.name, dict(s.attributes or {})) for s in descendants]}"
    )


@then(parsers.parse('no descendant span has an attribute starting with "{prefix}"'))
def no_descendant_has_attribute_prefix(prefix, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    violations = [
        (s.name, k)
        for s in descendants
        for k in (s.attributes or {})
        if k.startswith(prefix)
    ]
    log.info("Checking no descendant has attribute starting with '%s': violations=%s", prefix, violations)
    assert not violations, (
        f"Found raw attribute(s) with prefix '{prefix}' that should have been transformed: {violations}"
    )


@then(parsers.parse('no descendant span has attribute "{key}"'))
def no_descendant_has_exact_attribute(key, span_store):
    descendants = _get_descendants(span_store["all_spans"], span_store["root_span_id"])
    violations = [s.name for s in descendants if key in (s.attributes or {})]
    log.info("Checking no descendant has attribute '%s': violations=%s", key, violations)
    assert not violations, (
        f"Attribute '{key}' should have been transformed away but found on: {violations}"
    )


@then(parsers.parse('the span "{name}" is a child of "{parent_name}"'))
def span_is_child_of(name, parent_name, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    child = _find_span_in(spans, name)
    parent = _find_span_in(spans, parent_name)
    assert child is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    assert parent is not None, f"Span '{parent_name}' not found. Available: {[s.name for s in spans]}"
    parent_id = parent.get_span_context().span_id
    log.info("Checking '%s' is child of '%s': child.parent=%s, parent.span_id=%s", name, parent_name, child.parent, parent_id)
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
    log.info("Checking span '%s': '%s' == '%s' (actual: %r)", name, key, value, actual)
    assert str(actual) == value, f"Expected span '{name}' attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('a span with operation "{operation}" is a child of "{parent_name}"'))
def span_with_operation_is_child_of(operation, parent_name, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    parent = _find_span_in(spans, parent_name)
    assert parent is not None, f"Parent span '{parent_name}' not found. Available: {[s.name for s in spans]}"
    parent_id = parent.get_span_context().span_id
    child = next(
        (s for s in spans if (s.attributes or {}).get("gen_ai.operation.name") == operation
         and s.parent is not None and s.parent.span_id == parent_id),
        None,
    )
    log.info("Checking child with operation '%s' under '%s': %s", operation, parent_name,
             child.name if child else "NOT FOUND")
    assert child is not None, (
        f"No span with gen_ai.operation.name='{operation}' found as child of '{parent_name}'. "
        f"Spans: {[(s.name, (s.attributes or {}).get('gen_ai.operation.name')) for s in spans]}"
    )
    span_store["op_span"] = child


@then(parsers.parse('that span has attribute "{key}" equal to "{value}"'))
def op_span_has_attribute_equals(key, value, span_store):
    span = span_store["op_span"]
    actual = (span.attributes or {}).get(key)
    log.info("Checking op span '%s': '%s' == '%s' (actual: %r)", span.name, key, value, actual)
    assert str(actual) == value, f"Expected attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('that span has attribute "{key}" set'))
def op_span_has_attribute_set(key, span_store):
    span = span_store["op_span"]
    actual = (span.attributes or {}).get(key)
    log.info("Checking op span '%s': '%s' is set (actual: %r)", span.name, key, actual)
    assert actual is not None, f"Expected attribute '{key}' to be set on span '{span.name}', got None"


@then(parsers.parse('that span does not have attribute "{key}"'))
def op_span_lacks_attribute(key, span_store):
    span = span_store["op_span"]
    actual = (span.attributes or {}).get(key)
    log.info("Checking op span '%s' does NOT have '%s' (actual: %r)", span.name, key, actual)
    assert actual is None, f"Expected attribute '{key}' to be absent from '{span.name}', got {actual!r}"


@then(parsers.parse('the span "{name}" has resource attribute "{key}" equal to "{value}"'))
def named_span_resource_attr_equals(name, key, value, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    span = _find_span_in(spans, name)
    assert span is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    actual = span.resource.attributes.get(key)
    log.info("Checking span '%s' resource '%s' == '%s' (actual: %r)", name, key, value, actual)
    assert actual == value, f"Expected span '{name}' resource attribute '{key}' == '{value}', got {actual!r}"


@then(parsers.parse('the span "{name}" has resource attribute "{key}" set'))
def named_span_resource_attr_set(name, key, memory_exporter, span_store):
    spans = span_store.get("all_local_spans") or memory_exporter.get_finished_spans()
    span = _find_span_in(spans, name)
    assert span is not None, f"Span '{name}' not found. Available: {[s.name for s in spans]}"
    actual = span.resource.attributes.get(key)
    log.info("Checking span '%s' resource '%s' is set (actual: %r)", name, key, actual)
    assert actual, f"Expected span '{name}' resource attribute '{key}' to be set, got {actual!r}"


# --- helpers ---


def _find_span(exporter: InMemorySpanExporter, name: str) -> ReadableSpan | None:
    return _find_span_in(exporter.get_finished_spans(), name)


def _find_span_in(spans: list[ReadableSpan], name: str) -> ReadableSpan | None:
    return next((s for s in spans if s.name == name), None)


def _get_descendants(all_spans: list[ReadableSpan], root_span_id: int) -> list[ReadableSpan]:
    """Return all spans descending from root_span_id within the same trace."""
    return [
        s for s in all_spans
        if s.get_span_context().span_id != root_span_id
        and _is_descendant(s, root_span_id, all_spans)
    ]


def _is_descendant(span: ReadableSpan, ancestor_id: int, all_spans: list[ReadableSpan]) -> bool:
    current = span
    visited = set()
    while current is not None and current.parent is not None:
        parent_id = current.parent.span_id
        if parent_id in visited:
            break
        visited.add(parent_id)
        if parent_id == ancestor_id:
            return True
        current = next(
            (s for s in all_spans if s.get_span_context().span_id == parent_id),
            None,
        )
    return False
