import os
import re

from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Span

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register
from sap_cloud_sdk.core.telemetry.config import ENV_HIGH_CARDINALITY_URLS

# Internal attribute that marks a span for suppression at export time.
# The span is still created so that W3C traceparent headers are injected
# into the outgoing request, preserving distributed trace context.
_SUPPRESS_ATTR = "sap.cloud_sdk.suppress"


def _compile_patterns() -> list[re.Pattern]:
    raw = os.getenv(ENV_HIGH_CARDINALITY_URLS, "")
    patterns = [p.strip() for p in raw.split(",") if p.strip()]
    return [re.compile(re.escape(p)) for p in patterns]


_patterns: list[re.Pattern] = _compile_patterns()


def _is_high_cardinality(url: str) -> bool:
    return any(p.search(url) for p in _patterns)


def _request_hook(span: Span, request) -> None:
    if _is_high_cardinality(str(request.url)):
        span.set_attribute(_SUPPRESS_ATTR, True)


async def _async_request_hook(span: Span, request) -> None:
    if _is_high_cardinality(str(request.url)):
        span.set_attribute(_SUPPRESS_ATTR, True)


_instrumentor = HTTPXClientInstrumentor()


class HttpxInstrumentor(LibraryInstrumentor):
    """Instruments httpx sync and async clients with OTel spans and W3C header propagation.

    Spans for URLs matching SAP_CLOUD_SDK_HIGH_CARDINALITY_URLS (comma-separated substrings,
    unset by default) are marked for suppression at export time. The span is still created so
    that W3C traceparent headers propagate to the downstream service.
    """

    library_name = "httpx"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self, **kwargs) -> None:
        _instrumentor.instrument(
            request_hook=_request_hook,
            async_request_hook=_async_request_hook,
        )

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(HttpxInstrumentor())
