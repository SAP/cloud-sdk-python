#!/usr/bin/env python3
"""Subprocess helper: invoke_agent_span(propagate=True) + BaggageSpanProcessor + external tracer.

Run from repo root with PYTHONPATH=src (see test_tracer.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

# src layout
_ROOT = Path(__file__).resolve().parents[4]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from opentelemetry import trace
from opentelemetry.processor.baggage import ALLOW_ALL_BAGGAGE_KEYS, BaggageSpanProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from sap_cloud_sdk.core.telemetry.tracer import invoke_agent_span


def main() -> int:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    external_tracer = trace.get_tracer("third_party_simulating_langgraph")

    with invoke_agent_span(
        provider="openai",
        agent_name="currency-agent-local",
        agent_id="f268d3fd-096f-4ebc-b7ed-6fc03dfb3dde",
        kind=SpanKind.INTERNAL,
        propagate=True,
    ):
        with external_tracer.start_as_current_span("invoke_agent"):
            pass

    spans = {s.name: dict(s.attributes or {}) for s in exporter.get_finished_spans()}
    inner = spans.get("invoke_agent")
    if not inner:
        print("FAIL: no inner invoke_agent span", spans, file=sys.stderr)
        return 1
    if inner.get("gen_ai.agent.name") != "currency-agent-local":
        print("FAIL: gen_ai.agent.name", inner, file=sys.stderr)
        return 1
    if inner.get("gen_ai.agent.id") != "f268d3fd-096f-4ebc-b7ed-6fc03dfb3dde":
        print("FAIL: gen_ai.agent.id", inner, file=sys.stderr)
        return 1
    print("OK: external child span carries gen_ai.agent.name and gen_ai.agent.id via baggage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
