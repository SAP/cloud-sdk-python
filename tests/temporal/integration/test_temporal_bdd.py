"""BDD step definitions for Temporal integration tests."""

import asyncio
import threading
from datetime import timedelta
from typing import Any, List, Optional

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from temporalio import activity, workflow
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from sap_cloud_sdk.temporal import (
    ClientCreationError,
    ConfigurationError,
    TemporalClient,
    WorkerCreationError,
    create_client,
    create_worker,
)
from sap_cloud_sdk.temporal.config import TemporalConfig

scenarios("temporal.feature")


# ---------------------------------------------------------------------------
# Workflow & activity definitions (sandboxed=False for test-module definitions)
# ---------------------------------------------------------------------------


@activity.defn
async def greet_activity(name: str) -> str:
    if not name:
        raise ValueError("name must not be empty")
    return f"Hello, {name}!"


_flaky_counts: dict = {}


@activity.defn
async def flaky_activity(run_id: str) -> str:
    _flaky_counts[run_id] = _flaky_counts.get(run_id, 0) + 1
    if _flaky_counts[run_id] < 3:
        raise RuntimeError("transient failure")
    return "recovered"


@workflow.defn(sandboxed=False)
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        from temporalio.common import RetryPolicy
        return await workflow.execute_activity(
            greet_activity, name,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )


@workflow.defn(sandboxed=False)
class LongRunningWorkflow:
    @workflow.run
    async def run(self) -> str:
        await asyncio.sleep(3600)
        return "done"


@workflow.defn(sandboxed=False)
class SignalableWorkflow:
    def __init__(self) -> None:
        self._proceed = False

    @workflow.signal
    async def proceed(self) -> None:
        self._proceed = True

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self._proceed)
        return "signalled"


@workflow.defn(sandboxed=False)
class QueryableWorkflow:
    def __init__(self) -> None:
        self._status = "running"

    @workflow.query
    def current_status(self) -> str:
        return self._status

    @workflow.run
    async def run(self) -> str:
        await asyncio.sleep(3600)
        return "done"


@workflow.defn(sandboxed=False)
class RetryableWorkflow:
    @workflow.run
    async def run(self, run_id: str) -> str:
        from temporalio.common import RetryPolicy

        return await workflow.execute_activity(
            flaky_activity,
            run_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )


_ALL_WORKFLOWS = [
    GreetingWorkflow, LongRunningWorkflow, SignalableWorkflow, QueryableWorkflow, RetryableWorkflow
]
_ALL_ACTIVITIES = [greet_activity, flaky_activity]
_ALL_TASK_QUEUES = ["greetings", "long-running", "signalable", "queryable", "retryable"]


# ---------------------------------------------------------------------------
# Shared session-scoped event loop + Temporal env running on a background thread
# ---------------------------------------------------------------------------

_bg_loop: asyncio.AbstractEventLoop = None  # type: ignore[assignment]
_temporal_env: WorkflowEnvironment = None  # type: ignore[assignment]
_temporal_client: TemporalClient = None  # type: ignore[assignment]
_workers: list = []


def _start_background_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return loop


def _submit(coro):
    """Submit a coroutine to the background loop and block until done."""
    future = asyncio.run_coroutine_threadsafe(coro, _bg_loop)
    return future.result(timeout=60)


@pytest.fixture(scope="session", autouse=True)
def temporal_session(tmp_path_factory):
    global _bg_loop, _temporal_env, _temporal_client, _workers

    _bg_loop = _start_background_loop()

    async def _setup():
        global _temporal_env, _temporal_client
        _temporal_env = await WorkflowEnvironment.start_local()
        config = TemporalConfig(target="localhost:7233", namespace="default", is_local_dev=True)
        _temporal_client = TemporalClient(_temporal_env.client, config)

        for tq in _ALL_TASK_QUEUES:
            w = Worker(
                _temporal_env.client,
                task_queue=tq,
                workflows=_ALL_WORKFLOWS,
                activities=_ALL_ACTIVITIES,
            )
            _workers.append(w)
            asyncio.ensure_future(w.run(), loop=_bg_loop)

    _submit(_setup())
    yield

    async def _teardown():
        for w in _workers:
            await w.shutdown()
        await _temporal_env.shutdown()

    _submit(_teardown())


def _run(coro):
    """Run a coroutine on the shared background loop."""
    return _submit(coro)


# ---------------------------------------------------------------------------
# Test context
# ---------------------------------------------------------------------------


class TemporalTestContext:
    def __init__(self) -> None:
        self.workflow_id: Optional[str] = None
        self.task_queue: str = "greetings"
        self.handle: Any = None
        self.result: Any = None
        self.last_error: Optional[Exception] = None
        self.schedule_id: Optional[str] = None
        self.query_result: Any = None
        self.concurrent_results: List[dict] = []
        self.concurrent_errors: List[Exception] = []


@pytest.fixture
def ctx() -> TemporalTestContext:
    return TemporalTestContext()


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@given("the Temporal service is available")
def temporal_service_available(temporal_session):
    assert _temporal_env is not None


@given("I have a valid Temporal client")
def valid_temporal_client(ctx, temporal_session):
    assert _temporal_client is not None


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(parsers.parse('I have a workflow id "{workflow_id}"'))
def set_workflow_id(ctx, workflow_id: str):
    ctx.workflow_id = workflow_id


@given(parsers.parse('I have a task queue "{task_queue}"'))
def set_task_queue(ctx, task_queue: str):
    ctx.task_queue = task_queue


@given(parsers.parse('I have a schedule id "{schedule_id}"'))
def set_schedule_id(ctx, schedule_id: str):
    ctx.schedule_id = schedule_id


# ---------------------------------------------------------------------------
# When steps — workflow execution
# ---------------------------------------------------------------------------


@when(parsers.parse('I execute the greeting workflow with input "{name}"'))
def execute_greeting_workflow(ctx, name: str):
    wf_id = ctx.workflow_id or f"wf-{name.lower()}"
    tq = ctx.task_queue

    async def _coro():
        return await _temporal_client.execute_workflow(
            GreetingWorkflow.run, name, id=wf_id, task_queue=tq
        )

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when(parsers.parse('I execute the greeting workflow with input "{name}" and id "{wf_id}"'))
def execute_greeting_workflow_with_id(ctx, name: str, wf_id: str):
    ctx.workflow_id = wf_id
    execute_greeting_workflow(ctx, name)


@when(parsers.parse('I start the greeting workflow with input "{name}"'))
def start_greeting_workflow(ctx, name: str):
    wf_id = ctx.workflow_id or f"wf-{name.lower()}-async"
    tq = ctx.task_queue

    async def _coro():
        handle = await _temporal_client.start_workflow(
            GreetingWorkflow.run, name, id=wf_id, task_queue=tq
        )
        return handle

    try:
        ctx.handle = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when("I wait for the workflow result")
def wait_for_workflow_result(ctx):
    async def _coro():
        return await ctx.handle.result()

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when(parsers.parse('I get a handle to workflow "{workflow_id}"'))
def get_workflow_handle(ctx, workflow_id: str):
    ctx.handle = _temporal_client.get_workflow_handle(workflow_id)


@when(parsers.parse('I execute the greeting workflow with input "{name}" using ALLOW_DUPLICATE policy'))
def execute_workflow_allow_duplicate(ctx, name: str):
    from temporalio.common import WorkflowIDReusePolicy

    wf_id = ctx.workflow_id
    tq = ctx.task_queue

    async def _coro():
        return await _temporal_client.execute_workflow(
            GreetingWorkflow.run, name, id=wf_id, task_queue=tq,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


# ---------------------------------------------------------------------------
# When steps — cancel / terminate
# ---------------------------------------------------------------------------


@when("I start the long-running workflow")
def start_long_running_workflow(ctx):
    wf_id = ctx.workflow_id
    tq = ctx.task_queue

    async def _coro():
        return await _temporal_client.start_workflow(
            LongRunningWorkflow.run, id=wf_id, task_queue=tq
        )

    try:
        ctx.handle = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when(parsers.parse('I cancel the workflow "{workflow_id}"'))
def cancel_workflow(ctx, workflow_id: str):
    async def _coro():
        handle = _temporal_client.get_workflow_handle(workflow_id)
        await handle.cancel()

    try:
        _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when(parsers.parse('I terminate the workflow "{workflow_id}" with reason "{reason}"'))
def terminate_workflow(ctx, workflow_id: str, reason: str):
    async def _coro():
        handle = _temporal_client.get_workflow_handle(workflow_id)
        await handle.terminate(reason)

    try:
        _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


# ---------------------------------------------------------------------------
# When steps — signal / query
# ---------------------------------------------------------------------------


@when("I start the signalable workflow")
def start_signalable_workflow(ctx):
    wf_id = ctx.workflow_id
    tq = ctx.task_queue

    async def _coro():
        return await _temporal_client.start_workflow(
            SignalableWorkflow.run, id=wf_id, task_queue=tq
        )

    try:
        ctx.handle = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when(parsers.parse('I send signal "{signal_name}" to workflow "{workflow_id}"'))
def send_signal(ctx, signal_name: str, workflow_id: str):
    async def _coro():
        handle = _temporal_client.get_workflow_handle(workflow_id)
        await handle.signal(SignalableWorkflow.proceed)
        return await handle.result()

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when("I start the queryable workflow")
def start_queryable_workflow(ctx):
    wf_id = ctx.workflow_id
    tq = ctx.task_queue

    async def _coro():
        return await _temporal_client.start_workflow(
            QueryableWorkflow.run, id=wf_id, task_queue=tq
        )

    try:
        ctx.handle = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when(parsers.parse('I query workflow "{workflow_id}" for "{query_name}"'))
def query_workflow(ctx, workflow_id: str, query_name: str):
    async def _coro():
        handle = _temporal_client.get_workflow_handle(workflow_id)
        return await handle.query(QueryableWorkflow.current_status)

    try:
        ctx.query_result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


# ---------------------------------------------------------------------------
# When steps — list / retry / timeout
# ---------------------------------------------------------------------------


@when(parsers.parse("I list workflows with query '{query}'"))
def list_workflows(ctx, query: str):
    import time
    time.sleep(1)  # Allow visibility index to catch up

    async def _coro():
        results = []
        async for wf in _temporal_client.list_workflows(query):
            results.append(wf)
        return results

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when("I execute the retryable workflow that fails twice then succeeds")
def execute_retryable_workflow(ctx):
    wf_id = ctx.workflow_id
    tq = ctx.task_queue

    async def _coro():
        return await _temporal_client.execute_workflow(
            RetryableWorkflow.run, wf_id, id=wf_id, task_queue=tq
        )

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when("I attempt to execute a workflow with execution timeout of 1 millisecond")
def execute_workflow_with_timeout(ctx):
    wf_id = ctx.workflow_id

    async def _coro():
        return await _temporal_client.execute_workflow(
            LongRunningWorkflow.run, id=wf_id, task_queue="long-running",
            execution_timeout=timedelta(milliseconds=1),
        )

    try:
        ctx.result = _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


# ---------------------------------------------------------------------------
# When steps — error scenarios
# ---------------------------------------------------------------------------


@when("I attempt to create a client without required environment variables")
def attempt_create_client_no_env(ctx, monkeypatch):
    for var in ("TEMPORAL_CALL_URL", "TEMPORAL_NAMESPACE", "APPFND_LOCALDEV_TEMPORAL"):
        monkeypatch.delenv(var, raising=False)

    async def _try():
        try:
            await create_client()
            return None
        except (ClientCreationError, ConfigurationError) as e:
            return e

    ctx.last_error = _run(_try())


@when("I attempt to create a worker with no workflows and no activities")
def attempt_create_worker_no_tasks(ctx):
    from unittest.mock import MagicMock

    mock_client = TemporalClient(
        MagicMock(), TemporalConfig("localhost:7233", "default", is_local_dev=True)
    )
    try:
        create_worker(mock_client, task_queue="empty-queue")
        ctx.last_error = None
    except WorkerCreationError as e:
        ctx.last_error = e


# ---------------------------------------------------------------------------
# When steps — schedules
# ---------------------------------------------------------------------------


@when("I create a schedule that runs the greeting workflow every 24 hours")
def create_schedule(ctx):
    from temporalio.client import Schedule, ScheduleActionStartWorkflow, ScheduleIntervalSpec, ScheduleSpec

    schedule_id = ctx.schedule_id
    tq = ctx.task_queue

    async def _coro():
        await _temporal_client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    GreetingWorkflow.run, "Scheduled",
                    id=f"{schedule_id}-run", task_queue=tq,
                ),
                spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(hours=24))]),
            ),
        )

    try:
        _run(_coro())
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@then(parsers.parse('I delete the schedule "{schedule_id}"'))
def delete_schedule(ctx, schedule_id: str):
    async def _coro():
        try:
            handle = await _temporal_client.get_schedule_handle(schedule_id)
            await handle.delete()
        except Exception:
            pass

    _run(_coro())


# ---------------------------------------------------------------------------
# When steps — concurrent
# ---------------------------------------------------------------------------


@when("I execute 5 greeting workflows concurrently")
def execute_5_workflows_concurrently(ctx):
    tq = ctx.task_queue

    async def _coro():
        tasks = [
            _temporal_client.execute_workflow(
                GreetingWorkflow.run, f"User{i}", id=f"wf-concurrent-{i}", task_queue=tq
            )
            for i in range(5)
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    try:
        results = _run(_coro())
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                ctx.concurrent_errors.append(result)
                ctx.concurrent_results.append({"success": False, "index": i, "error": result})
            else:
                ctx.concurrent_results.append({"success": True, "index": i, "result": result})
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


@when("I execute 6 workflows concurrently with some invalid inputs")
def execute_6_workflows_mixed(ctx):
    tq = ctx.task_queue

    async def _coro():
        async def run_one(i: int):
            valid = i % 3 != 2
            name = f"ValidUser{i}" if valid else ""
            try:
                result = await _temporal_client.execute_workflow(
                    GreetingWorkflow.run, name, id=f"wf-mixed-{i}", task_queue=tq
                )
                return {"success": True, "valid": valid, "index": i, "result": result}
            except Exception as e:
                return {"success": False, "valid": valid, "index": i, "error": e}

        return await asyncio.gather(*[run_one(i) for i in range(6)])

    try:
        results = _run(_coro())
        for result in results:
            ctx.concurrent_results.append(result)
            if not result["success"]:
                ctx.concurrent_errors.append(result.get("error"))
        ctx.last_error = None
    except Exception as e:
        ctx.last_error = e


# ---------------------------------------------------------------------------
# Then steps — success
# ---------------------------------------------------------------------------


@then("the workflow should complete successfully")
def workflow_completes_successfully(ctx):
    assert ctx.last_error is None, f"Workflow failed: {ctx.last_error}"


@then("the second workflow should complete successfully")
def second_workflow_completes_successfully(ctx):
    assert ctx.last_error is None, f"Second workflow failed: {ctx.last_error}"


@then(parsers.parse('the result should be "{expected}"'))
def result_should_be(ctx, expected: str):
    assert ctx.result == expected, f"Expected '{expected}' but got '{ctx.result}'"


@then("the workflow handle should be returned")
def workflow_handle_returned(ctx):
    assert ctx.handle is not None


@then("the schedule should be created successfully")
def schedule_created_successfully(ctx):
    assert ctx.last_error is None, f"Schedule creation failed: {ctx.last_error}"


@then("all concurrent workflows should complete successfully")
def all_concurrent_workflows_succeed(ctx):
    assert len(ctx.concurrent_errors) == 0, \
        f"Expected all to succeed, got {len(ctx.concurrent_errors)} errors: {ctx.concurrent_errors}"


@then("no errors should occur during concurrent execution")
def no_concurrent_errors(ctx):
    all_concurrent_workflows_succeed(ctx)


@then(parsers.parse("the workflow list should contain at least {count:d} entries"))
def workflow_list_has_entries(ctx, count: int):
    assert isinstance(ctx.result, list)
    assert len(ctx.result) >= count, f"Expected >={count} entries, got {len(ctx.result)}"


@then("the activity should have been retried")
def activity_was_retried(ctx):
    assert ctx.result == "recovered", f"Expected 'recovered' but got '{ctx.result}'"


@then(parsers.parse('the query result should be "{expected}"'))
def query_result_should_be(ctx, expected: str):
    assert ctx.query_result == expected, f"Expected '{expected}' but got '{ctx.query_result}'"


@then("the workflow should be cancelled")
def workflow_is_cancelled(ctx):
    assert ctx.last_error is None, f"Cancel failed: {ctx.last_error}"


@then("the workflow should be terminated")
def workflow_is_terminated(ctx):
    assert ctx.last_error is None, f"Terminate failed: {ctx.last_error}"


# ---------------------------------------------------------------------------
# Then steps — error assertions
# ---------------------------------------------------------------------------


@then("the execution should fail with a timeout error")
def execution_fails_with_timeout(ctx):
    assert ctx.last_error is not None, "Expected a timeout error but workflow succeeded"
    # WorkflowFailureError wraps the actual TimeoutError in __cause__
    err = ctx.last_error
    cause = getattr(err, "__cause__", None)
    timeout_keywords = ["timeout", "timed out", "deadline", "cancel"]
    err_text = (str(err) + str(cause) + type(err).__name__ + type(cause).__name__).lower() if cause else (str(err) + type(err).__name__).lower()
    assert any(t in err_text for t in timeout_keywords), \
        f"Expected timeout error but got: {type(err).__name__}: {err} (cause: {cause})"


@then("the client creation should fail with a configuration error")
def client_creation_fails_with_config_error(ctx):
    assert ctx.last_error is not None
    assert isinstance(ctx.last_error, (ClientCreationError, ConfigurationError)), \
        f"Expected config error but got: {type(ctx.last_error).__name__}: {ctx.last_error}"


@then("the worker creation should fail with a validation error")
def worker_creation_fails_with_validation_error(ctx):
    assert ctx.last_error is not None
    assert isinstance(ctx.last_error, WorkerCreationError), \
        f"Expected WorkerCreationError but got: {type(ctx.last_error).__name__}: {ctx.last_error}"


# ---------------------------------------------------------------------------
# Then steps — concurrent mixed
# ---------------------------------------------------------------------------


@then("the valid workflows should complete successfully")
def valid_workflows_succeed(ctx):
    valid_successful = [r for r in ctx.concurrent_results if r.get("valid") and r.get("success")]
    valid_total = [r for r in ctx.concurrent_results if r.get("valid")]
    assert len(valid_successful) == len(valid_total), \
        f"Expected all {len(valid_total)} valid to succeed, only {len(valid_successful)} did"


@then("the invalid workflows should fail with errors")
def invalid_workflows_fail(ctx):
    invalid_failed = [r for r in ctx.concurrent_results if not r.get("valid") and not r.get("success")]
    invalid_total = [r for r in ctx.concurrent_results if not r.get("valid")]
    assert len(invalid_failed) == len(invalid_total), \
        f"Expected all {len(invalid_total)} invalid to fail, only {len(invalid_failed)} did"


@then("no data inconsistencies should occur")
def no_data_inconsistencies(ctx):
    for result in ctx.concurrent_results:
        assert "success" in result
        assert isinstance(result["success"], bool)
        if not result["success"]:
            assert "error" in result
