"""Step definitions for telemetry.feature."""

import logging
from contextlib import contextmanager

import pytest
from langchain_core.messages import HumanMessage
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pytest_bdd import given, parsers, scenario, then, when

from sap_cloud_sdk.core.telemetry.tracer import invoke_agent_span
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
