"""Built-in framework adapters."""

try:
    from sap_cloud_sdk.core.runtime_context.adapters import _starlette  # noqa: F401
except ImportError:
    pass
