#!/usr/bin/env python3
"""Subprocess helper: invoke_agent identity via ContextVar + SpanProcessor + external tracer.

Run from repo root with PYTHONPATH=src (see test_tracer.py).

Modes:
  default           — propagate=True expects gen_ai.agent.* on nested span
  --propagate-false — propagate=False expects nested span WITHOUT those attrs from identity injection
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# src layout
_ROOT = Path(__file__).resolve().parents[4]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from sap_cloud_sdk.core.telemetry.invoke_agent_identity_processor import (
    InvokeAgentIdentitySpanProcessor,
)
from sap_cloud_sdk.core.telemetry.tracer import invoke_agent_span


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--propagate-false",
        action="store_true",
        help="Verify identity injection is NOT applied when propagate=False",
    )
    args = parser.parse_args()
    propagate = not args.propagate_false

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(InvokeAgentIdentitySpanProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    external_tracer = trace.get_tracer("third_party_simulating_langgraph")

    with invoke_agent_span(
        provider="openai",
        agent_name="currency-agent-local",
        agent_id="f268d3fd-096f-4ebc-b7ed-6fc03dfb3dde",
        kind=SpanKind.INTERNAL,
        propagate=propagate,
    ):
        with external_tracer.start_as_current_span("invoke_agent"):
            pass

    spans = {s.name: dict(s.attributes or {}) for s in exporter.get_finished_spans()}
    if "invoke_agent" not in spans:
        print("FAIL: no inner invoke_agent span", spans, file=sys.stderr)
        return 1
    inner = spans["invoke_agent"]

    if propagate:
        if inner.get("gen_ai.agent.name") != "currency-agent-local":
            print("FAIL: gen_ai.agent.name", inner, file=sys.stderr)
            return 1
        if inner.get("gen_ai.agent.id") != "f268d3fd-096f-4ebc-b7ed-6fc03dfb3dde":
            print("FAIL: gen_ai.agent.id", inner, file=sys.stderr)
            return 1
        print(
            "OK: external child span carries gen_ai.agent.name and gen_ai.agent.id via SpanProcessor"
        )
        return 0

    # propagate=False: SDK must not push agent identity into ContextVar for this scope
    if inner.get("gen_ai.agent.name") is not None or inner.get("gen_ai.agent.id") is not None:
        print(
            "FAIL: propagate=False but nested span has gen_ai.agent.* (should not):",
            inner,
            file=sys.stderr,
        )
        return 1
    print(
        "OK: propagate=False — nested span has no gen_ai.agent.* from identity propagation"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
