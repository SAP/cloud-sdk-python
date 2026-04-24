# Temporal User Guide

This module integrates with the SAP Managed Temporal service to provide durable workflow orchestration on SAP BTP. It wraps the official `temporalio` SDK and adds automatic ZTIS (SPIFFE/SPIRE) credential resolution so applications on Kyma Runtime or Cloud Foundry connect with zero static secrets.

## Installation

Install the SDK with the `temporal` extra to pull in the required dependencies:

```bash
pip install "sap-cloud-sdk[temporal]"
```

## Quick Start

```python
import asyncio
from sap_cloud_sdk.temporal import create_client, create_worker

async def main():
    # Auto-discovers SPIFFE socket + Temporal config from environment
    client = await create_client()

    handle = await client.start_workflow(
        "GreetingWorkflow", "World",
        id="greeting-1", task_queue="greetings",
    )
    result = await handle.result()
    print(f"Result: {result}")

asyncio.run(main())
```

## Prerequisites (Production)

Before using this module in a deployed environment:

1. **ZTIS Service Instance** provisioned in your BTP subaccount
2. **ServiceBinding** created with workload attestation matching your namespace and service account
3. **SPIRE Agent** running (DaemonSet on Kyma, sidecar buildpack on Cloud Foundry)
4. **SPIFFE socket** accessible at the expected path (see [Environment Variables](#environment-variables))
5. **Environment variables** injected from the service binding:
   - `TEMPORAL_CALL_URL` — Temporal frontend gRPC address
   - `TEMPORAL_NAMESPACE` — Temporal namespace name

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TEMPORAL_CALL_URL` | Yes (production) | Temporal frontend gRPC address (e.g. `frontend-us30d.temporal.services.cloud.sap:443`) |
| `TEMPORAL_NAMESPACE` | Yes (production) | Temporal namespace (e.g. `sf-33040a4e-77d1-47e7-8c23-4744e0757a64`) |
| `APPFND_LOCALDEV_TEMPORAL` | No | Set to `true` for local development — connects to `localhost:7233` without TLS |
| `WORKLOAD_API_SOCKET` | No | Override the SPIFFE socket path |
| `SPIFFE_ENDPOINT_SOCKET` | No | Alternative SPIFFE socket env var (`unix://` prefix supported) |

## Local Development

For local development against the Temporal dev server (no mTLS required):

```bash
# Install the Temporal CLI
brew install temporal

# Start the Temporal dev server
temporal server start-dev

# Enable local dev mode in your app
export APPFND_LOCALDEV_TEMPORAL=true

# Run your app — connects to localhost:7233, namespace "default"
python main.py
```

In local dev mode the SDK skips SPIFFE credential resolution entirely and connects to `localhost:7233` without TLS. The `TEMPORAL_CALL_URL` and `TEMPORAL_NAMESPACE` environment variables are not required.

## Concepts

- **Workflow**: A durable, fault-tolerant function that orchestrates activities. Must be deterministic — no I/O, no random, no system clock directly.
- **Activity**: A regular function that performs side effects (HTTP calls, DB writes, file I/O). Executed by the worker and retried automatically on failure.
- **Worker**: A long-running process that polls a task queue and executes workflows and activities.
- **Task Queue**: A named channel through which the Temporal server dispatches work to workers.
- **Schedule**: A recurring trigger that starts a workflow on a cron-like interval.

## Defining Workflows

Workflows must be **deterministic** — they replay from event history on failure. All side effects must be delegated to activities.

```python
from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from .activities import greet, send_notification

@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        greeting = await workflow.execute_activity(
            greet,
            name,
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            send_notification,
            greeting,
            start_to_close_timeout=timedelta(seconds=60),
        )
        return greeting
```

**Determinism rules:**
- No direct I/O, no `random`, no `time.time()` — use `workflow.now()` instead
- No threading — use `workflow.execute_activity()` for concurrent work
- Import non-deterministic modules inside `workflow.unsafe.imports_passed_through()`

## Defining Activities

Activities perform the actual work and are retried automatically on failure:

```python
from temporalio import activity

@activity.defn
async def greet(name: str) -> str:
    return f"Hello, {name}!"

@activity.defn
async def send_notification(message: str) -> None:
    activity.logger.info("Notification: %s", message)
```

For long-running activities, use heartbeating to report progress and allow cancellation:

```python
@activity.defn
async def process_large_dataset(dataset_id: str) -> int:
    records = load_dataset(dataset_id)
    processed = 0
    for batch in chunk(records, 100):
        process_batch(batch)
        processed += len(batch)
        activity.heartbeat(processed)
    return processed
```

## Creating a Client

```python
from sap_cloud_sdk.temporal import create_client

# Production (auto-discovers SPIFFE socket and env vars)
client = await create_client()

# Override target or namespace
client = await create_client(target="my-host:443", namespace="my-namespace")

# Pass a custom data converter
client = await create_client(data_converter=my_converter)
```

The `create_client()` factory:
1. Reads `TEMPORAL_CALL_URL` and `TEMPORAL_NAMESPACE` from the environment
2. Discovers the SPIFFE socket path (Kyma or Cloud Foundry)
3. Fetches an X.509 SVID from the SPIRE agent via the socket
4. Builds a `TLSConfig` for mTLS using the SVID and trust bundle
5. Connects and returns a `TemporalClient`

## Creating a Worker

```python
from sap_cloud_sdk.temporal import create_client, create_worker
from .workflows import GreetingWorkflow
from .activities import greet, send_notification

client = await create_client()

worker = create_worker(
    client,
    task_queue="greetings",
    workflows=[GreetingWorkflow],
    activities=[greet, send_notification],
)

await worker.run()
```

**Worker options:**

| Parameter | Default | Description |
|---|---|---|
| `task_queue` | required | Task queue name to poll |
| `workflows` | `[]` | Workflow classes decorated with `@workflow.defn` |
| `activities` | `[]` | Activity callables decorated with `@activity.defn` |
| `max_concurrent_activities` | `100` | Max parallel activity executions |
| `max_concurrent_workflow_tasks` | `100` | Max parallel workflow task executions |
| `max_concurrent_local_activities` | `100` | Max parallel local activity executions |
| `graceful_shutdown_timeout` | `None` | Duration to wait for in-flight tasks during shutdown |
| `build_id` | `None` | Build ID for Worker Versioning |

## Workflow Operations

### Start and wait for result

```python
result = await client.execute_workflow(
    GreetingWorkflow.run, "World",
    id="greeting-1", task_queue="greetings",
)
```

### Start without waiting

```python
handle = await client.start_workflow(
    GreetingWorkflow.run, "World",
    id="greeting-1", task_queue="greetings",
)
# Do other work...
result = await handle.result()
```

### Get a handle to an existing workflow

```python
handle = client.get_workflow_handle("greeting-1")
result = await handle.result()
```

### Signal a running workflow

```python
handle = client.get_workflow_handle("greeting-1")
await handle.signal(GreetingWorkflow.my_signal, "signal-data")
```

### Query a running workflow

```python
handle = client.get_workflow_handle("greeting-1")
status = await handle.query(GreetingWorkflow.current_status)
```

### Cancel a workflow

```python
handle = client.get_workflow_handle("greeting-1")
await handle.cancel()
```

### Terminate a workflow

```python
handle = client.get_workflow_handle("greeting-1")
await handle.terminate("Cleaning up stale workflow")
```

### List workflows

```python
async for wf in client.list_workflows('WorkflowType = "GreetingWorkflow"'):
    print(f"{wf.id} — {wf.status}")
```

## Schedules

Create recurring workflow executions:

```python
from temporalio.client import (
    Schedule, ScheduleActionStartWorkflow,
    ScheduleSpec, ScheduleIntervalSpec,
)
from datetime import timedelta

handle = await client.create_schedule(
    "daily-report",
    Schedule(
        action=ScheduleActionStartWorkflow(
            DailyReportWorkflow.run,
            id="daily-report",
            task_queue="reports",
        ),
        spec=ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(hours=24))],
        ),
    ),
)

# Get an existing schedule handle
handle = await client.get_schedule_handle("daily-report")
await handle.delete()
```

## API

### `create_client()`

```python
async def create_client(
    *,
    target: str | None = None,
    namespace: str | None = None,
    data_converter: Any = None,
    interceptors: Sequence[Any] | None = None,
    tls: bool | TLSConfig | None = None,
    retry_config: Any | None = None,
    keep_alive_config: Any | None = None,
    rpc_metadata: Mapping[str, str] | None = None,
    identity: str | None = None,
    lazy: bool = False,
) -> TemporalClient
```

### `create_worker()`

```python
def create_worker(
    client: TemporalClient,
    *,
    task_queue: str,
    workflows: Sequence[type] = (),
    activities: Sequence[Any] = (),
    activity_executor: Any | None = None,
    workflow_task_executor: Any | None = None,
    max_concurrent_activities: int = 100,
    max_concurrent_workflow_tasks: int = 100,
    max_concurrent_local_activities: int = 100,
    interceptors: Sequence[Any] | None = None,
    build_id: str | None = None,
    identity: str | None = None,
    graceful_shutdown_timeout: Any | None = None,
    debug_mode: bool = False,
) -> Worker
```

### `TemporalClient`

```python
class TemporalClient:
    inner: Client                    # Underlying temporalio.client.Client

    namespace: str                   # Connected namespace
    identity: str                    # Client identity string

    async def start_workflow(...) -> WorkflowHandle
    async def execute_workflow(...) -> Any
    def get_workflow_handle(workflow_id, *, run_id=None, ...) -> WorkflowHandle
    def list_workflows(query=None, ...) -> AsyncIterator[WorkflowExecution]
    async def count_workflows(query=None, ...) -> Any
    async def create_schedule(id, schedule, **kwargs) -> ScheduleHandle
    async def get_schedule_handle(id) -> ScheduleHandle
```

### `TemporalConfig`

```python
@dataclass(frozen=True)
class TemporalConfig:
    target: str             # Temporal frontend address (host:port)
    namespace: str          # Temporal namespace
    is_local_dev: bool      # True when APPFND_LOCALDEV_TEMPORAL=true
    spiffe_socket_path: str | None  # Resolved SPIFFE socket path
```

## Error Handling

```python
from sap_cloud_sdk.temporal import (
    create_client,
    TemporalError,
    ConfigurationError,
    ClientCreationError,
    SpiffeError,
    WorkerCreationError,
)

try:
    client = await create_client()
except ConfigurationError as e:
    # Missing TEMPORAL_CALL_URL, TEMPORAL_NAMESPACE, or SPIFFE socket
    print(f"Configuration error: {e}")
except SpiffeError as e:
    # SPIRE agent unreachable or SVID fetch failed
    print(f"SPIFFE/ZTIS error: {e}")
except ClientCreationError as e:
    # TLS or network error during connection
    print(f"Client creation error: {e}")
except TemporalError as e:
    # Catch-all for any SDK error
    print(f"SDK error: {e}")
```

All exceptions carry a `.cause` attribute with the original underlying exception when one is available.

## Advanced: Direct Access to the Temporal Client

For operations not exposed on the `TemporalClient` wrapper, use `.inner` to access the raw `temporalio.client.Client`:

```python
client = await create_client()
raw = client.inner

await raw.update_schedule(...)
async for wf in raw.list_workflows(...):
    ...
```

## Deployment on Kyma (Kubernetes)

Pod spec with the SPIFFE socket volume mount required for mTLS:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-temporal-app
spec:
  template:
    spec:
      containers:
        - name: app
          image: my-app:latest
          env:
            - name: TEMPORAL_CALL_URL
              valueFrom:
                secretKeyRef:
                  name: temporal-binding
                  key: call_url
            - name: TEMPORAL_NAMESPACE
              valueFrom:
                secretKeyRef:
                  name: temporal-binding
                  key: namespace
          volumeMounts:
            - name: spiffe-workload-api
              mountPath: /spiffe-workload-api
              readOnly: true
      volumes:
        - name: spiffe-workload-api
          hostPath:
            path: /run/spire/agent-sockets
            type: DirectoryOrCreate
```

The SDK discovers the SPIFFE socket automatically at `/spiffe-workload-api/spire-agent.sock` on Kyma and at `/tmp/spire-agent/public/api.sock` on Cloud Foundry. Use `WORKLOAD_API_SOCKET` or `SPIFFE_ENDPOINT_SOCKET` to override the path.

## Secret Resolution

### Service Binding (Kyma)

- Mount path: `/etc/secrets/appfnd/temporal/{instance}/` (or environment variables)
- Keys: `call_url`, `namespace`
- Env var fallbacks: `TEMPORAL_CALL_URL`, `TEMPORAL_NAMESPACE`

### SPIFFE Socket

The SDK searches for the SPIFFE socket in this order:

1. `WORKLOAD_API_SOCKET` environment variable
2. `SPIFFE_ENDPOINT_SOCKET` environment variable (`unix://` prefix stripped automatically)
3. `/spiffe-workload-api/spire-agent.sock` (Kyma default)
4. `/tmp/spire-agent/public/api.sock` (Cloud Foundry default)

## Troubleshooting

**`ConfigurationError: Temporal target address not configured`**
Set `TEMPORAL_CALL_URL` or `APPFND_LOCALDEV_TEMPORAL=true` for local development.

**`SpiffeError: Failed to fetch X.509 credentials`**
The SPIRE agent socket is not reachable. Check that the `spiffe-workload-api` volume is mounted correctly and the SPIRE DaemonSet is running.

**`ClientCreationError: Failed to connect to Temporal`**
The Temporal frontend is unreachable. Verify `TEMPORAL_CALL_URL` is correct and network connectivity is available.

**`WorkerCreationError: At least one workflow or activity must be provided`**
`create_worker()` requires at least one workflow class or activity function. Pass them via `workflows=[...]` or `activities=[...]`.

**Workflow sandbox validation error**
If defining workflow classes in test modules (not separate packages), add `sandboxed=False` to the decorator: `@workflow.defn(sandboxed=False)`.
