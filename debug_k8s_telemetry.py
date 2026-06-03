"""
Reproduces the k8s autoinstrumentation resource-attribute bug with a real LangChain agent.

What this simulates
-------------------
On k8s, the OTel operator runs sitecustomize.py at pod startup (before any app
code), which:
  1. Creates a TracerProvider whose resource carries telemetry.auto.version.
  2. Calls LangChainInstrumentor().instrument() — this calls provider.get_tracer()
     and caches a Tracer that snapshots provider.resource at that instant.

The app then calls auto_instrument(), which merges SAP resource attrs onto
provider._resource — but the cached LangChain Tracer still holds the old object.
All LangChain spans therefore carry the operator resource only, never SAP attrs.

Run
---
    .venv/bin/python debug_k8s_telemetry.py

Output
------
  spans_debug.json  — every finished span with its resource attributes
  Console           — PASS / FAIL per span with the attrs that matter

Exit code 0 = all spans carry SAP attrs (bug fixed)
Exit code 1 = some spans are missing SAP attrs (bug present)
"""

import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

# ── env: pretend we are running in a k8s pod ─────────────────────────────────
os.environ.update({
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "APPFND_CONHOS_APP_NAME":       "my-agent",
    "APPFND_CONHOS_ENVIRONMENT":    "dev",
    "APPFND_CONHOS_REGION":         "eu10",
    "APPFND_CONHOS_SUBACCOUNTID":   "sub-abc-123",
    "APPFND_CONHOS_SYSTEM_ROLE":    "ZAFT",
    "SAP_SOLUTION_AREA":            "AFND",
})

# ── imports that must happen before anything touches the global provider ──────
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration

# ── fake LLM so we need no API key ───────────────────────────────────────────
class _EchoLLM(BaseChatModel):
    """Instantly echoes the last human message back as an AI message."""

    @property
    def _llm_type(self) -> str:
        return "echo"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        text = messages[-1].content if messages else "hello"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — simulate the OTel operator's sitecustomize.py
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Phase 1: operator sitecustomize.py ──────────────────────────────────")

span_exporter = InMemorySpanExporter()

operator_provider = TracerProvider(
    resource=Resource.create({
        "telemetry.auto.version":  "0.62b1",
        "k8s.deployment.name":     "my-agent-deployment",
        "k8s.namespace.name":      "prod",
        "service.name":            "my-agent-deployment",   # operator-derived, should be overridden
    })
)
operator_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
trace.set_tracer_provider(operator_provider)
print("  [operator] TracerProvider installed with telemetry.auto.version=0.62b1")

# The operator calls LangChainInstrumentor().instrument() — this internally
# calls provider.get_tracer() and caches the Tracer with the current resource.
LangchainInstrumentor().instrument()
print("  [operator] LangchainInstrumentor().instrument() done")
print(f"  [operator] provider._tracers cache now has {len(operator_provider._tracers)} tracer(s)")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — application startup: call auto_instrument()
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Phase 2: app calls auto_instrument() ────────────────────────────────")

# We patch Traceloop.init so it doesn't try to connect to a real collector,
# but we let _merge_resource_attrs_into_active_provider_if_wrapper_installed
# run against the live operator_provider — that's the code under test.
from unittest.mock import patch
with patch("sap_cloud_sdk.core.telemetry.auto_instrument.Traceloop"), \
     patch("sap_cloud_sdk.core.telemetry.auto_instrument.GRPCSpanExporter"), \
     patch("sap_cloud_sdk.core.telemetry.auto_instrument.GenAIAttributeTransformer"):
    from sap_cloud_sdk.core.telemetry import auto_instrument
    auto_instrument()

print(f"  [sdk]      provider._resource after merge: {list(operator_provider.resource.attributes.keys())}")
print(f"  [sdk]      provider._tracers cache still has {len(operator_provider._tracers)} tracer(s)")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — run a tiny LangChain chain (the agent's "work")
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Phase 3: agent invokes LangChain chain ──────────────────────────────")

llm = _EchoLLM()
response = llm.invoke([HumanMessage(content="What is the capital of France?")])
print(f"  [agent]    LLM response: {response.content!r}")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — collect spans, validate, write to file
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Phase 4: span validation ────────────────────────────────────────────")

SAP_ATTRS = [
    "sap.cloud_sdk.name",
    "sap.cloud_sdk.language",
    "sap.cloud_sdk.version",
    "sap.solution_area",
    "sap.cld.subaccount_id",
]

finished = span_exporter.get_finished_spans()
output = []
all_ok = True

for span in finished:
    attrs = dict(span.resource.attributes)
    missing = [k for k in SAP_ATTRS if k not in attrs]
    ok = len(missing) == 0
    all_ok = all_ok and ok

    entry = {
        "span_name":          span.name,
        "instrumentation":    span.instrumentation_scope.name if span.instrumentation_scope else "unknown",
        "status":             "PASS" if ok else "FAIL",
        "missing_sap_attrs":  missing,
        "resource_attributes": attrs,
    }
    output.append(entry)

    status_label = "PASS" if ok else "FAIL"
    print(f"  [{status_label}] {span.name!r}  ({entry['instrumentation']})")
    if missing:
        print(f"       missing: {missing}")
    else:
        print(f"       sap.cloud_sdk.name = {attrs.get('sap.cloud_sdk.name')!r}")
        print(f"       service.name       = {attrs.get('service.name')!r}")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spans_debug.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  Wrote {len(output)} span(s) to {out_path}")

if all_ok:
    print("\nRESULT: PASS — all spans carry SAP resource attributes.\n")
    sys.exit(0)
else:
    failed = sum(1 for e in output if e["status"] == "FAIL")
    print(f"\nRESULT: FAIL — {failed}/{len(output)} span(s) missing SAP resource attributes.\n")
    sys.exit(1)
