#!/usr/bin/env python3
"""
End-to-end check: OTLP export to Jaeger UI with propagate=True vs propagate=False.

Requires Jaeger all-in-one with OTLP gRPC on localhost:4317 and UI on localhost:16686, e.g.:

    docker compose -f cluster-observability-verification/local-otel-jaeger-test/docker-compose.yml up -d

Then from cloud-sdk-python repo root:

    PYTHONPATH=src python scripts/verify_invoke_agent_jaeger_integration.py

Each OTLP/Jaeger scenario runs in a **fresh Python subprocess** so TracerProvider can initialize
(OpenTelemetry forbids overriding the provider in-process).

Exit code 0 only if both scenarios pass Jaeger assertions.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

# Imports below are only needed in worker process (lazy in _worker_main)
DEFAULT_OTLP = "http://localhost:4317"
DEFAULT_UI = "http://localhost:16686"


def _grpc_host_port(endpoint: str) -> str:
    u = endpoint.strip()
    if u.startswith("http://"):
        u = u[7:]
    elif u.startswith("https://"):
        u = u[8:]
    return u.split("/")[0]


def _tags_dict(span: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in span.get("tags") or []:
        key = t.get("key")
        if key:
            out[key] = t.get("value")
    return out


def _fetch_trace_for_service(ui_base: str, service: str, timeout_sec: float = 45.0) -> Optional[dict]:
    q = urllib.parse.urlencode({"service": service, "limit": "5"})
    url = f"{ui_base.rstrip('/')}/api/traces?{q}"
    deadline = time.monotonic() + timeout_sec
    last_err: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
            traces = data.get("data") or []
            if traces:
                return traces[0]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            last_err = e
        time.sleep(0.8)
    if last_err:
        print(f"WARN: Jaeger poll error: {last_err}", file=sys.stderr)
    return None


def _worker_main() -> int:
    """Single-process OTLP emit + Jaeger assert (import OTEL only here)."""
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.processor.baggage import ALLOW_ALL_BAGGAGE_KEYS, BaggageSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import SpanKind

    from sap_cloud_sdk.core.telemetry.tracer import invoke_agent_span

    p = argparse.ArgumentParser()
    p.add_argument("--worker", action="store_true")
    p.add_argument("--propagate", type=lambda x: x.lower() == "true", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--otlp-endpoint", default=DEFAULT_OTLP)
    p.add_argument("--jaeger-ui", default=DEFAULT_UI)
    p.add_argument("--agent-name", default="currency-agent-local")
    p.add_argument("--agent-id", default="f268d3fd-096f-4ebc-b7ed-6fc03dfb3dde")
    args = p.parse_args()

    propagate = args.propagate
    svc = f"sdk-prop-{'true' if propagate else 'false'}-{args.run_id}"

    resource = Resource.create({"service.name": svc})
    exporter = OTLPSpanExporter(endpoint=_grpc_host_port(args.otlp_endpoint), insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    external = trace.get_tracer("langchain")

    with invoke_agent_span(
        provider="sap",
        agent_name=args.agent_name,
        agent_id=args.agent_id,
        kind=SpanKind.INTERNAL,
        propagate=propagate,
    ):
        with external.start_as_current_span("invoke_agent"):
            pass

    provider.shutdown()

    trace_data = _fetch_trace_for_service(args.jaeger_ui, svc)
    if not trace_data:
        print(
            f"FAIL: No trace in Jaeger for service={svc!r}",
            file=sys.stderr,
        )
        return 1

    inner: Optional[dict] = None
    for sp in trace_data.get("spans", []):
        if sp.get("operationName") == "invoke_agent":
            inner = sp
            break
    if not inner:
        print(f"FAIL: No span invoke_agent in trace for {svc}", file=sys.stderr)
        return 1

    tags = _tags_dict(inner)
    name_tag = tags.get("gen_ai.agent.name")
    id_tag = tags.get("gen_ai.agent.id")

    if propagate:
        if name_tag != args.agent_name or id_tag != args.agent_id:
            print(
                f"FAIL propagate=True: expected name={args.agent_name!r} id={args.agent_id!r}; "
                f"got name={name_tag!r} id={id_tag!r} tags={tags}",
                file=sys.stderr,
            )
            return 1
        print(f"PASS propagate=True: Jaeger shows gen_ai.agent.* on nested span ({svc})", flush=True)
        return 0

    if name_tag is not None or id_tag is not None:
        print(
            f"FAIL propagate=False: expected no gen_ai.agent.* on nested span; "
            f"got name={name_tag!r} id={id_tag!r}",
            file=sys.stderr,
        )
        return 1
    print(f"PASS propagate=False: nested span has no gen_ai.agent.* ({svc})", flush=True)
    return 0


def orchestrator_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--otlp-endpoint", default=DEFAULT_OTLP)
    parser.add_argument("--jaeger-ui", default=DEFAULT_UI)
    parser.add_argument("--agent-name", default="currency-agent-local")
    parser.add_argument("--agent-id", default="f268d3fd-096f-4ebc-b7ed-6fc03dfb3dde")
    args = parser.parse_args()

    run_id = str(int(time.time() * 1000) % 10_000_000)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]

    py = sys.executable
    env = os.environ.copy()
    src = str(repo_root / "src")
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + src if env.get("PYTHONPATH") else src

    print(
        f"Jaeger UI: {args.jaeger_ui} | OTLP: {args.otlp_endpoint}\n"
        "Ensure Jaeger all-in-one is running (OTLP :4317, UI :16686).\n",
        flush=True,
    )

    base_cmd = [
        py,
        str(script_path),
        "--worker",
        "--run-id",
        run_id,
        "--otlp-endpoint",
        args.otlp_endpoint,
        "--jaeger-ui",
        args.jaeger_ui,
        "--agent-name",
        args.agent_name,
        "--agent-id",
        args.agent_id,
    ]

    for propagate, label in ((False, "disabled (propagate=False)"), (True, "enabled (propagate=True)")):
        cmd = base_cmd + ["--propagate", str(propagate).lower()]
        print(f"\n=== {label} ===", flush=True)
        r = subprocess.run(cmd, env=env, cwd=str(repo_root))
        if r.returncode != 0:
            print(
                "\nTip: start Jaeger:\n"
                "  docker compose -f "
                "<repo>/generic/cluster-observability-verification/"
                "local-otel-jaeger-test/docker-compose.yml up -d\n",
                file=sys.stderr,
            )
            return r.returncode

    print("\nAll Jaeger integration checks passed.", flush=True)
    return 0


def main() -> int:
    if "--worker" in sys.argv:
        return _worker_main()
    return orchestrator_main()


if __name__ == "__main__":
    raise SystemExit(main())
