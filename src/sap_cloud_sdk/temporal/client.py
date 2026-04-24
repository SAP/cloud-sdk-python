"""Temporal client for the SAP Cloud SDK.

The primary entry point is :func:`create_client`, an async factory that:

1. Resolves configuration from the environment (see :mod:`.config`).
2. Fetches X.509 SVID credentials from the SPIRE agent (see :mod:`._spiffe`).
3. Builds a :class:`temporalio.service.TLSConfig` for mTLS.
4. Connects a :class:`temporalio.client.Client`.
5. Returns a thin :class:`TemporalClient` wrapper that proxies common
   operations and exposes the raw client via ``.inner``.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Mapping, Optional, Sequence, Type, Union

from temporalio.client import (
    Client,
    Schedule,
    ScheduleHandle,
    WorkflowExecution,
    WorkflowHandle,
)
from temporalio.common import RetryPolicy, SearchAttributePair, TypedSearchAttributes, _arg_unset
from temporalio.service import RPCError, TLSConfig
from temporalio.worker import Worker

from sap_cloud_sdk.core.telemetry import Module, Operation, record_error_metric, record_request_metric

from ._spiffe import fetch_x509_credentials
from .config import TemporalConfig, resolve_config
from .exceptions import ClientCreationError, ConfigurationError, SpiffeError, WorkerCreationError

logger = logging.getLogger(__name__)


class TemporalClient:
    """Thin wrapper around :class:`temporalio.client.Client`.

    Provides pass-through methods for the most common Temporal operations
    while exposing the underlying client via :attr:`inner` for anything
    not directly surfaced.
    """

    def __init__(self, client: Client, config: TemporalConfig) -> None:
        self._client = client
        self._config = config

    @property
    def inner(self) -> Client:
        """The underlying :class:`temporalio.client.Client` instance."""
        return self._client

    @property
    def namespace(self) -> str:
        """The Temporal namespace this client is connected to."""
        return self._config.namespace

    @property
    def identity(self) -> str:
        """The identity string reported by this client."""
        return self._client.identity

    async def start_workflow(
        self,
        workflow: Union[str, Any],
        arg: Any = _arg_unset,
        *,
        id: str,
        task_queue: str,
        args: Sequence[Any] = (),
        execution_timeout: Optional[Any] = None,
        run_timeout: Optional[Any] = None,
        task_timeout: Optional[Any] = None,
        id_reuse_policy: Optional[Any] = None,
        id_conflict_policy: Optional[Any] = None,
        retry_policy: Optional[RetryPolicy] = None,
        cron_schedule: str = "",
        memo: Optional[Mapping[str, Any]] = None,
        search_attributes: Optional[
            Union[TypedSearchAttributes, Sequence[SearchAttributePair]]
        ] = None,
        start_delay: Optional[Any] = None,
        start_signal: Optional[str] = None,
        start_signal_args: Sequence[Any] = (),
        rpc_metadata: Optional[Mapping[str, str]] = None,
        rpc_timeout: Optional[Any] = None,
        request_eager_start: bool = False,
    ) -> WorkflowHandle[Any, Any]:
        """Start a workflow execution.

        Args:
            workflow: Workflow type name or callable decorated with ``@workflow.defn``.
            arg: Single argument to pass to the workflow (use ``args`` for multiple).
            id: Unique workflow execution ID.
            task_queue: Task queue to schedule the workflow on.
            args: Multiple arguments to pass to the workflow.
            execution_timeout: Timeout for the entire workflow execution.
            run_timeout: Timeout for a single workflow run.
            task_timeout: Timeout for a single workflow task.
            id_reuse_policy: Policy for reusing a workflow ID.
            id_conflict_policy: Policy for conflicting workflow IDs.
            retry_policy: Retry policy for the workflow.
            cron_schedule: Cron schedule string for recurring workflows.
            memo: Memo key-value pairs.
            search_attributes: Search attributes for visibility queries.
            start_delay: Delay before starting the workflow.
            start_signal: Signal to send on workflow start.
            start_signal_args: Arguments for the start signal.
            rpc_metadata: Additional gRPC metadata.
            rpc_timeout: Timeout for the RPC call.
            request_eager_start: Request eager workflow start.

        Returns:
            A :class:`WorkflowHandle` for the started workflow execution.
        """
        source = getattr(self, "_telemetry_source", None)
        kw: dict[str, Any] = {
            "arg": arg,
            "id": id,
            "task_queue": task_queue,
            "args": args,
            "cron_schedule": cron_schedule,
            "start_signal_args": start_signal_args,
            "request_eager_start": request_eager_start,
        }
        if execution_timeout is not None:
            kw["execution_timeout"] = execution_timeout
        if run_timeout is not None:
            kw["run_timeout"] = run_timeout
        if task_timeout is not None:
            kw["task_timeout"] = task_timeout
        if id_reuse_policy is not None:
            kw["id_reuse_policy"] = id_reuse_policy
        if id_conflict_policy is not None:
            kw["id_conflict_policy"] = id_conflict_policy
        if retry_policy is not None:
            kw["retry_policy"] = retry_policy
        if memo is not None:
            kw["memo"] = memo
        if search_attributes is not None:
            kw["search_attributes"] = search_attributes
        if start_delay is not None:
            kw["start_delay"] = start_delay
        if start_signal is not None:
            kw["start_signal"] = start_signal
        if rpc_metadata is not None:
            kw["rpc_metadata"] = rpc_metadata
        if rpc_timeout is not None:
            kw["rpc_timeout"] = rpc_timeout
        try:
            result = await self._client.start_workflow(workflow, **kw)  # type: ignore[arg-type]
            record_request_metric(Module.TEMPORAL, source, Operation.TEMPORAL_WORKFLOW_START.value)
            return result
        except Exception:
            record_error_metric(Module.TEMPORAL, source, Operation.TEMPORAL_WORKFLOW_START.value)
            raise

    async def execute_workflow(
        self,
        workflow: Union[str, Any],
        arg: Any = _arg_unset,
        *,
        id: str,
        task_queue: str,
        args: Sequence[Any] = (),
        execution_timeout: Optional[Any] = None,
        run_timeout: Optional[Any] = None,
        task_timeout: Optional[Any] = None,
        id_reuse_policy: Optional[Any] = None,
        id_conflict_policy: Optional[Any] = None,
        retry_policy: Optional[RetryPolicy] = None,
        cron_schedule: str = "",
        memo: Optional[Mapping[str, Any]] = None,
        search_attributes: Optional[
            Union[TypedSearchAttributes, Sequence[SearchAttributePair]]
        ] = None,
        start_delay: Optional[Any] = None,
        start_signal: Optional[str] = None,
        start_signal_args: Sequence[Any] = (),
        rpc_metadata: Optional[Mapping[str, str]] = None,
        rpc_timeout: Optional[Any] = None,
        request_eager_start: bool = False,
        result_type: Optional[Type[Any]] = None,
    ) -> Any:
        """Start a workflow and wait for its result.

        Args:
            workflow: Workflow type name or callable.
            arg: Single argument to pass to the workflow.
            id: Unique workflow execution ID.
            task_queue: Task queue to schedule the workflow on.
            result_type: Expected result type for deserialization.
            **kwargs: Additional options forwarded to ``start_workflow``.

        Returns:
            The workflow result deserialized to *result_type* (or ``Any``).
        """
        source = getattr(self, "_telemetry_source", None)
        kw: dict[str, Any] = {
            "arg": arg,
            "id": id,
            "task_queue": task_queue,
            "args": args,
            "cron_schedule": cron_schedule,
            "start_signal_args": start_signal_args,
            "request_eager_start": request_eager_start,
        }
        if execution_timeout is not None:
            kw["execution_timeout"] = execution_timeout
        if run_timeout is not None:
            kw["run_timeout"] = run_timeout
        if task_timeout is not None:
            kw["task_timeout"] = task_timeout
        if id_reuse_policy is not None:
            kw["id_reuse_policy"] = id_reuse_policy
        if id_conflict_policy is not None:
            kw["id_conflict_policy"] = id_conflict_policy
        if retry_policy is not None:
            kw["retry_policy"] = retry_policy
        if memo is not None:
            kw["memo"] = memo
        if search_attributes is not None:
            kw["search_attributes"] = search_attributes
        if start_delay is not None:
            kw["start_delay"] = start_delay
        if start_signal is not None:
            kw["start_signal"] = start_signal
        if rpc_metadata is not None:
            kw["rpc_metadata"] = rpc_metadata
        if rpc_timeout is not None:
            kw["rpc_timeout"] = rpc_timeout
        if result_type is not None:
            kw["result_type"] = result_type
        try:
            result = await self._client.execute_workflow(workflow, **kw)  # type: ignore[arg-type]
            record_request_metric(Module.TEMPORAL, source, Operation.TEMPORAL_WORKFLOW_EXECUTE.value)
            return result
        except Exception:
            record_error_metric(Module.TEMPORAL, source, Operation.TEMPORAL_WORKFLOW_EXECUTE.value)
            raise

    def get_workflow_handle(
        self,
        workflow_id: str,
        *,
        run_id: Optional[str] = None,
        first_execution_run_id: Optional[str] = None,
    ) -> WorkflowHandle[Any, Any]:
        """Get a handle to an existing workflow execution.

        Args:
            workflow_id: The workflow execution ID.
            run_id: Specific run ID (defaults to latest run).
            first_execution_run_id: First execution run ID for chained workflows.

        Returns:
            A :class:`WorkflowHandle` for the specified execution.
        """
        return self._client.get_workflow_handle(
            workflow_id,
            run_id=run_id,
            first_execution_run_id=first_execution_run_id,
        )

    def list_workflows(
        self,
        query: Optional[str] = None,
        *,
        rpc_metadata: Optional[Mapping[str, str]] = None,
        rpc_timeout: Optional[Any] = None,
    ) -> AsyncIterator[WorkflowExecution]:
        """List workflow executions with an optional visibility query.

        Args:
            query: Temporal visibility query string (e.g. ``WorkflowType = "MyWorkflow"``).
            rpc_metadata: Additional gRPC metadata.
            rpc_timeout: Timeout for the RPC call.

        Returns:
            An async iterator of :class:`WorkflowExecution` objects.
        """
        kw: dict[str, Any] = {}
        if rpc_metadata is not None:
            kw["rpc_metadata"] = rpc_metadata
        if rpc_timeout is not None:
            kw["rpc_timeout"] = rpc_timeout
        return self._client.list_workflows(query, **kw)

    async def count_workflows(
        self,
        query: Optional[str] = None,
        *,
        rpc_metadata: Optional[Mapping[str, str]] = None,
        rpc_timeout: Optional[Any] = None,
    ) -> Any:
        """Count workflow executions matching a visibility query.

        Args:
            query: Temporal visibility query string.
            rpc_metadata: Additional gRPC metadata.
            rpc_timeout: Timeout for the RPC call.

        Returns:
            A count response object.
        """
        source = getattr(self, "_telemetry_source", None)
        kw: dict[str, Any] = {}
        if rpc_metadata is not None:
            kw["rpc_metadata"] = rpc_metadata
        if rpc_timeout is not None:
            kw["rpc_timeout"] = rpc_timeout
        try:
            result = await self._client.count_workflows(query, **kw)
            record_request_metric(Module.TEMPORAL, source, Operation.TEMPORAL_WORKFLOW_COUNT.value)
            return result
        except Exception:
            record_error_metric(Module.TEMPORAL, source, Operation.TEMPORAL_WORKFLOW_COUNT.value)
            raise

    async def create_schedule(
        self,
        id: str,
        schedule: Schedule,
        **kwargs: Any,
    ) -> ScheduleHandle:
        """Create a new Temporal schedule.

        Args:
            id: Unique schedule ID.
            schedule: The :class:`Schedule` definition.
            **kwargs: Additional options forwarded to the underlying client.

        Returns:
            A :class:`ScheduleHandle` for managing the schedule.
        """
        source = getattr(self, "_telemetry_source", None)
        try:
            result = await self._client.create_schedule(id, schedule, **kwargs)
            record_request_metric(Module.TEMPORAL, source, Operation.TEMPORAL_SCHEDULE_CREATE.value)
            return result
        except Exception:
            record_error_metric(Module.TEMPORAL, source, Operation.TEMPORAL_SCHEDULE_CREATE.value)
            raise

    async def get_schedule_handle(self, id: str) -> ScheduleHandle:
        """Get a handle to an existing schedule.

        Args:
            id: The schedule ID.

        Returns:
            A :class:`ScheduleHandle`.
        """
        return await self._client.get_schedule_handle(id)


async def create_client(
    *,
    target: Optional[str] = None,
    namespace: Optional[str] = None,
    data_converter: Any = None,
    interceptors: Optional[Sequence[Any]] = None,
    tls: Optional[Union[bool, TLSConfig]] = None,
    retry_config: Optional[Any] = None,
    keep_alive_config: Optional[Any] = None,
    rpc_metadata: Optional[Mapping[str, str]] = None,
    identity: Optional[str] = None,
    lazy: bool = False,
) -> TemporalClient:
    """Create a Temporal client with SAP ZTIS mTLS authentication.

    In production the function discovers the SPIFFE socket, fetches an X.509
    SVID from the SPIRE agent, and connects to the Temporal frontend over mTLS.
    In local-dev mode (``APPFND_LOCALDEV_TEMPORAL=true``) it connects to
    ``localhost:7233`` without TLS.

    Args:
        target: Override the Temporal frontend address (``host:port``).
        namespace: Override the Temporal namespace.
        data_converter: Custom data converter for payload serialization.
        interceptors: Client interceptors.
        tls: Explicit TLS config. When ``None`` the SDK builds one from SPIFFE
            credentials (or disables TLS in local-dev mode).
        retry_config: gRPC retry configuration.
        keep_alive_config: gRPC keep-alive configuration.
        rpc_metadata: Additional gRPC metadata sent with every call.
        identity: Client identity string.
        lazy: When ``True``, defer the actual connection until the first RPC call.

    Returns:
        A :class:`TemporalClient` wrapping the connected Temporal client.

    Raises:
        ConfigurationError: When required environment variables are missing.
        SpiffeError: When SVID fetching fails.
        ClientCreationError: On any failure during client creation.

    Example::

        import asyncio
        from sap_cloud_sdk.temporal import create_client

        async def main():
            client = await create_client()
            result = await client.execute_workflow(
                "MyWorkflow", "arg", id="wf-1", task_queue="my-queue"
            )
            print(result)

        asyncio.run(main())
    """
    try:
        config = resolve_config(target=target, namespace=namespace)
    except ConfigurationError as exc:
        raise ClientCreationError(
            f"Failed to resolve Temporal configuration: {exc}", cause=exc
        ) from exc

    resolved_tls: Union[bool, TLSConfig, None] = tls
    if resolved_tls is None:
        if config.is_local_dev:
            resolved_tls = False
            logger.info("Local-dev mode: TLS disabled")
        else:
            if config.spiffe_socket_path is None:
                raise ClientCreationError(
                    "SPIFFE socket path is required in production mode but was not resolved."
                )
            try:
                creds = fetch_x509_credentials(config.spiffe_socket_path)
            except (SpiffeError, OSError) as exc:
                raise ClientCreationError(
                    f"Failed to fetch SPIFFE credentials: {exc}", cause=exc
                ) from exc

            resolved_tls = TLSConfig(
                server_root_ca_cert=creds.trust_bundle_pem,
                client_cert=creds.cert_chain_pem,
                client_private_key=creds.private_key_pem,
            )
            logger.info("Built mTLS config from SPIFFE SVID (%s)", creds.spiffe_id)

    connect_kwargs: dict[str, Any] = {
        "target_host": config.target,
        "namespace": config.namespace,
        "tls": resolved_tls,
        "lazy": lazy,
    }
    if data_converter is not None:
        connect_kwargs["data_converter"] = data_converter
    if interceptors is not None:
        connect_kwargs["interceptors"] = interceptors
    if retry_config is not None:
        connect_kwargs["retry_config"] = retry_config
    if keep_alive_config is not None:
        connect_kwargs["keep_alive_config"] = keep_alive_config
    if rpc_metadata is not None:
        connect_kwargs["rpc_metadata"] = rpc_metadata
    if identity is not None:
        connect_kwargs["identity"] = identity

    try:
        client = await Client.connect(**connect_kwargs)
    except (OSError, RuntimeError, RPCError) as exc:
        raise ClientCreationError(
            f"Failed to connect to Temporal at {config.target}: {exc}", cause=exc
        ) from exc

    logger.info(
        "Connected to Temporal  target=%s  namespace=%s  local_dev=%s",
        config.target,
        config.namespace,
        config.is_local_dev,
    )
    return TemporalClient(client, config)


def create_worker(
    client: TemporalClient,
    *,
    task_queue: str,
    workflows: Sequence[Type[Any]] = (),
    activities: Sequence[Any] = (),
    activity_executor: Optional[Any] = None,
    workflow_task_executor: Optional[Any] = None,
    max_concurrent_activities: int = 100,
    max_concurrent_workflow_tasks: int = 100,
    max_concurrent_local_activities: int = 100,
    interceptors: Optional[Sequence[Any]] = None,
    build_id: Optional[str] = None,
    identity: Optional[str] = None,
    graceful_shutdown_timeout: Optional[Any] = None,
    debug_mode: bool = False,
) -> Any:
    """Create a Temporal Worker.

    Args:
        client: A :class:`TemporalClient` obtained from :func:`create_client`.
        task_queue: The task queue to poll.
        workflows: Workflow classes decorated with ``@workflow.defn``.
        activities: Activity callables decorated with ``@activity.defn``.
        activity_executor: Custom executor for running activities.
        workflow_task_executor: Custom executor for workflow tasks.
        max_concurrent_activities: Maximum concurrent activity executions.
        max_concurrent_workflow_tasks: Maximum concurrent workflow task executions.
        max_concurrent_local_activities: Maximum concurrent local activity executions.
        interceptors: Worker-level interceptors.
        build_id: Build ID for Worker Versioning.
        identity: Override the worker identity string.
        graceful_shutdown_timeout: Duration to wait for in-flight tasks during shutdown.
        debug_mode: Enable Temporal workflow debug mode.

    Returns:
        A :class:`temporalio.worker.Worker` ready to be run with ``await worker.run()``.

    Raises:
        WorkerCreationError: When the Worker cannot be constructed.
    """
    if not workflows and not activities:
        raise WorkerCreationError(
            "At least one workflow or activity must be provided to create_worker()."
        )

    worker_kwargs: dict[str, Any] = {
        "client": client.inner,
        "task_queue": task_queue,
        "workflows": list(workflows),
        "activities": list(activities),
        "max_concurrent_activities": max_concurrent_activities,
        "max_concurrent_workflow_tasks": max_concurrent_workflow_tasks,
        "max_concurrent_local_activities": max_concurrent_local_activities,
        "debug_mode": debug_mode,
    }
    if activity_executor is not None:
        worker_kwargs["activity_executor"] = activity_executor
    if workflow_task_executor is not None:
        worker_kwargs["workflow_task_executor"] = workflow_task_executor
    if interceptors is not None:
        worker_kwargs["interceptors"] = interceptors
    if build_id is not None:
        worker_kwargs["build_id"] = build_id
    if identity is not None:
        worker_kwargs["identity"] = identity
    if graceful_shutdown_timeout is not None:
        worker_kwargs["graceful_shutdown_timeout"] = graceful_shutdown_timeout

    try:
        worker = Worker(**worker_kwargs)
    except Exception as exc:
        raise WorkerCreationError(
            f"Failed to create Temporal Worker for task queue '{task_queue}': {exc}",
            cause=exc,
        ) from exc

    logger.info(
        "Created Worker  task_queue=%s  workflows=%d  activities=%d",
        task_queue,
        len(workflows),
        len(activities),
    )
    return worker
