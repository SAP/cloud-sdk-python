"""SAP Cloud SDK for Python - Print module

The create_client() function loads credentials from mounts/env vars and
returns a configured PrintClient.

Usage:
    from sap_cloud_sdk.print import create_client, PrintQueue, PrintContent, PrintTask

    client = create_client()

    # List queues
    queues = client.list_queues()

    # Upload a document and print it
    with open("invoice.pdf", "rb") as f:
        doc_id = client.upload_document(f, filename="invoice.pdf")

    task = PrintTask(
        item_id=doc_id,
        qname="my-queue",
        print_contents=[PrintContent(object_key=doc_id, document_name="invoice.pdf")],
    )
    client.create_print_task(task)
"""

from __future__ import annotations

from typing import Optional

from sap_cloud_sdk.print._models import (
    PrintContent,
    PrintProfile,
    PrintQueue,
    PrintTask,
    PrintTaskMetadata,
)
from sap_cloud_sdk.print.config import load_from_env_or_mount, PrintConfig
from sap_cloud_sdk.print._http import PrintHttp, TokenProvider
from sap_cloud_sdk.print.client import PrintClient
from sap_cloud_sdk.print.exceptions import (
    PrintError,
    ClientCreationError,
    ConfigError,
    HttpError,
    PrintOperationError,
)

from sap_cloud_sdk.core.telemetry import (
    Module,
    Operation,
    record_error_metric as _record_error_metric,
)


def create_client(
    *,
    instance: Optional[str] = None,
    config: Optional[PrintConfig] = None,
    _telemetry_source: Optional[Module] = None,
) -> PrintClient:
    """Create a PrintClient with secret resolution and OAuth setup.

    Args:
        instance: Instance name used for secret resolution. Defaults to "default".
        config: Optional explicit PrintConfig, bypasses secret resolution.
        _telemetry_source: Internal parameter for telemetry. Not for external use.

    Returns:
        Configured PrintClient.

    Raises:
        ClientCreationError: If client creation fails.
    """
    try:
        binding = config or load_from_env_or_mount(instance)
        tp = TokenProvider(binding)
        http = PrintHttp(config=binding, token_provider=tp)
        return PrintClient(http, _telemetry_source=_telemetry_source)
    except Exception as e:
        _record_error_metric(
            Module.PRINT,
            _telemetry_source,
            Operation.PRINT_CREATE_CLIENT,
        )
        raise ClientCreationError(f"failed to create print client: {e}") from e


__all__ = [
    # Models
    "PrintQueue",
    "PrintProfile",
    "PrintContent",
    "PrintTask",
    "PrintTaskMetadata",
    "PrintConfig",
    # Factory
    "create_client",
    # Client
    "PrintClient",
    # Exceptions
    "PrintError",
    "ClientCreationError",
    "ConfigError",
    "HttpError",
    "PrintOperationError",
]
