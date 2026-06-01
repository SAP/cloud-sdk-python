"""Fixtures for telemetry integration tests."""

import os
from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sap_cloud_sdk.aicore import set_aicore_config
from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument
from sap_cloud_sdk.core.telemetry.genai_attribute_transformer import (
    GenAIAttributeTransformer,
)


@pytest.fixture(scope="session")
def memory_exporter() -> InMemorySpanExporter:
    """Initialize auto_instrument once per session and inject an in-memory exporter.

    Uses OTEL_TRACES_EXPORTER=console so Traceloop.init runs for real without
    needing a real collector endpoint. A second SimpleSpanProcessor backed by
    InMemorySpanExporter is added afterward for test assertions on raw spans.
    """
    raw_exporter = InMemorySpanExporter()
    with patch.dict(os.environ, {"OTEL_TRACES_EXPORTER": "console"}, clear=False):
        auto_instrument(disable_batch=True)
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(raw_exporter))
    return raw_exporter


@pytest.fixture(scope="session")
def transforming_exporter(memory_exporter: InMemorySpanExporter) -> InMemorySpanExporter:
    """Inject a second in-memory exporter wrapped in GenAIAttributeTransformer.

    Used by traceloop.feature tests to assert on transformer output
    (gen_ai.* attributes present, llm.usage.* and traceloop.* absent).
    """
    transformed_sink = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(GenAIAttributeTransformer(transformed_sink))
    )
    return transformed_sink


@pytest.fixture(autouse=True)
def clear_spans(memory_exporter: InMemorySpanExporter, transforming_exporter: InMemorySpanExporter):
    """Clear both exporters before each test so spans don't bleed between scenarios."""
    memory_exporter.clear()
    transforming_exporter.clear()


@pytest.fixture(scope="session")
def aicore_configured():
    """Call set_aicore_config() once per session.

    Skips if AICORE_BASE_URL is absent — tests depending on this fixture are
    skipped automatically.
    """
    if not os.environ.get("AICORE_BASE_URL"):
        pytest.skip("AICORE_BASE_URL not set — skipping AI Core integration tests")
    set_aicore_config()
