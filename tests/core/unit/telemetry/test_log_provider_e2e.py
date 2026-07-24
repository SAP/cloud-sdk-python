"""End-to-end tests for OTel log provider using a real in-memory exporter.

These tests exercise the full log pipeline — LoggingHandler → LoggerProvider →
processor → exporter — without mocking. They verify that logs emitted via the
standard stdlib logging API arrive with the correct resource attributes and,
when inside an active span, carry trace/span correlation IDs.
"""

import logging
import pytest

from opentelemetry import trace
from opentelemetry._logs import _internal as _logs_internal
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging.handler import LoggingHandler

from sap_cloud_sdk.core.telemetry._provider import setup_log_provider
from sap_cloud_sdk.core.telemetry.config import InstrumentationConfig


@pytest.fixture()
def log_exporter(monkeypatch):
    """Set up a real LoggerProvider backed by an in-memory exporter.

    Resets the OTel logger provider singleton before and after each test so
    tests are fully isolated. Uses SimpleLogRecordProcessor so records flush
    synchronously without needing a flush() call.
    """
    # Reset the OTel logger provider singleton so set_logger_provider() works
    _logs_internal._LOGGER_PROVIDER_SET_ONCE._done = False
    _logs_internal._LOGGER_PROVIDER = None

    exporter = InMemoryLogRecordExporter()

    monkeypatch.setattr(
        "sap_cloud_sdk.core.telemetry._provider._create_log_exporter",
        lambda: exporter,
    )
    monkeypatch.setattr(
        "sap_cloud_sdk.core.telemetry._provider.BatchLogRecordProcessor",
        SimpleLogRecordProcessor,
    )
    monkeypatch.setattr(
        "sap_cloud_sdk.core.telemetry._provider.get_config",
        lambda: InstrumentationConfig(
            enabled=True,
            service_name="test-svc",
            otlp_endpoint="http://localhost:4317",
        ),
    )
    monkeypatch.setenv("APPFND_CONHOS_APP_NAME", "test-svc")
    monkeypatch.setenv("APPFND_CONHOS_REGION", "eu10")
    monkeypatch.setenv("APPFND_CONHOS_SUBACCOUNTID", "sub-123")
    monkeypatch.setenv("APPFND_CONHOS_SYSTEM_ROLE", "TEST")
    monkeypatch.setenv("SAP_SOLUTION_AREA", "AFND")

    provider = setup_log_provider()
    assert provider is not None

    root = logging.getLogger()
    original_level = root.level
    root.setLevel(logging.DEBUG)

    yield exporter

    root.setLevel(original_level)
    for h in list(root.handlers):
        if isinstance(h, LoggingHandler):
            root.removeHandler(h)

    # Reset singleton again so the next test starts clean
    _logs_internal._LOGGER_PROVIDER_SET_ONCE._done = False
    _logs_internal._LOGGER_PROVIDER = None


@pytest.fixture()
def tracer():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    return provider.get_tracer("test")


class TestLogProviderEndToEnd:
    def test_log_record_reaches_exporter(self, log_exporter):
        logging.getLogger("test.basic").warning("hello from sdk")

        records = log_exporter.get_finished_logs()
        assert len(records) == 1
        assert records[0].log_record.body == "hello from sdk"

    def test_severity_mapped_correctly(self, log_exporter):
        logger = logging.getLogger("test.severity")
        logger.info("info msg")
        logger.warning("warn msg")
        logger.error("error msg")

        records = log_exporter.get_finished_logs()
        severities = [r.log_record.severity_text for r in records]
        assert severities == ["INFO", "WARN", "ERROR"]

    def test_resource_attributes_on_record(self, log_exporter):
        logging.getLogger("test.resource").info("check resource")

        r = log_exporter.get_finished_logs()[0]
        attrs = r.resource.attributes
        assert attrs.get("service.name") == "test-svc"
        assert attrs.get("sap.cloud_sdk.language") == "python"
        assert attrs.get("cloud.region") == "eu10"
        assert attrs.get("sap.cld.subaccount_id") == "sub-123"

    def test_extra_fields_become_log_attributes(self, log_exporter):
        logging.getLogger("test.extra").warning(
            "structured log", extra={"tenant_id": "t-abc", "duration_ms": 42}
        )

        r = log_exporter.get_finished_logs()[0]
        assert r.log_record.attributes.get("tenant_id") == "t-abc"
        assert r.log_record.attributes.get("duration_ms") == 42

    def test_trace_correlation_inside_span(self, log_exporter, tracer):
        with tracer.start_as_current_span("test-span") as span:
            logging.getLogger("test.trace").info("inside span")
            expected_trace_id = span.get_span_context().trace_id
            expected_span_id = span.get_span_context().span_id

        r = log_exporter.get_finished_logs()[0]
        assert r.log_record.trace_id == expected_trace_id
        assert r.log_record.span_id == expected_span_id

    def test_no_trace_correlation_outside_span(self, log_exporter):
        logging.getLogger("test.no_trace").info("outside span")

        r = log_exporter.get_finished_logs()[0]
        assert r.log_record.trace_id == 0
        assert r.log_record.span_id == 0
