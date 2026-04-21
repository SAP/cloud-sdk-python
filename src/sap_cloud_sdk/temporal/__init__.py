"""SAP Cloud SDK — Temporal module.

Integrates the SAP Managed Temporal service using ZTIS (SPIFFE/SPIRE) mTLS
authentication. Applications on Kyma Runtime or Cloud Foundry connect with
zero static secrets.

Quick start::

    import asyncio
    from sap_cloud_sdk.temporal import create_client, create_worker

    async def main():
        client = await create_client()
        result = await client.execute_workflow(
            "MyWorkflow", "arg", id="wf-1", task_queue="my-queue"
        )
        print(result)

    asyncio.run(main())

Environment variables
---------------------
``TEMPORAL_CALL_URL``
    Temporal frontend address (``host:port``).
``TEMPORAL_NAMESPACE``
    Temporal namespace name.
``WORKLOAD_API_SOCKET``
    Path to the SPIFFE Workload API socket (auto-discovered when absent).
``SPIFFE_ENDPOINT_SOCKET``
    Alternative SPIFFE socket env var (``unix://`` prefix supported).
``APPFND_LOCALDEV_TEMPORAL``
    Set to ``true`` for local development (``localhost:7233``, no TLS).
"""

from __future__ import annotations

from .client import TemporalClient, create_client, create_worker
from .config import TemporalConfig
from .exceptions import (
    ClientCreationError,
    ConfigurationError,
    SpiffeError,
    TemporalError,
    WorkerCreationError,
)

__all__ = [
    # Factories
    "create_client",
    "create_worker",
    # Types
    "TemporalClient",
    "TemporalConfig",
    # Exceptions
    "TemporalError",
    "ConfigurationError",
    "ClientCreationError",
    "SpiffeError",
    "WorkerCreationError",
]
