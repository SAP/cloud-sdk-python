"""Extension logging configuration for SAP Cloud SDK."""

import logging


def configure_extension_logging() -> None:
    """Attach ExtensionContextLogFilter to every root logging handler (idempotent).

    The filter enriches every log record emitted inside an extension context
    (tool call, hook, instruction) with ``ext_*`` attributes that downstream
    handlers can include in structured log output.

    Calling this function more than once is safe — the filter is not added
    twice to the same handler.

    Example::

        from sap_cloud_sdk.extensibility import configure_extension_logging

        configure_extension_logging()
    """
    from sap_cloud_sdk.core.telemetry import ExtensionContextLogFilter

    root = logging.getLogger()
    _filter = ExtensionContextLogFilter()
    for handler in root.handlers:
        if not any(isinstance(f, ExtensionContextLogFilter) for f in handler.filters):
            handler.addFilter(_filter)
