"""Patches for buggy MCP OTel instrumentation."""


def unwrap_buggy_mcp_otel_patches() -> None:
    """Undo @dont_throw wrapping added by opentelemetry-instrumentation-mcp.

    The ``opentelemetry-instrumentation-mcp`` package wraps ``BaseSession.send_request``
    and ``streamablehttp_client`` with a ``@dont_throw`` decorator that swallows
    exceptions and corrupts MCP ``initialize()`` responses.  This function removes
    those wrappers so that MCP sessions behave correctly.

    Silently no-ops when the instrumentation is absent or already removed — safe
    to call unconditionally at agent startup.

    Example::

        from sap_cloud_sdk.extensibility import unwrap_buggy_mcp_otel_patches

        unwrap_buggy_mcp_otel_patches()
    """
    try:
        from opentelemetry.instrumentation.utils import unwrap  # type: ignore[import-untyped]

        unwrap("mcp.shared.session.BaseSession", "send_request")
        import mcp.client.streamable_http

        unwrap("mcp.client.streamable_http", "streamablehttp_client")
        import langchain_mcp_adapters.sessions  # type: ignore[import-untyped]  # ty: ignore[unresolved-import]

        langchain_mcp_adapters.sessions.streamablehttp_client = (
            mcp.client.streamable_http.streamablehttp_client
        )
    except Exception:
        pass
