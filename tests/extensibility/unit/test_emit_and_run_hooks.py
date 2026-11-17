"""Tests for ExtensibilityClient.emit_instruction_spans and run_hooks."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sap_cloud_sdk.extensibility._models import (
    ExtensionCapabilityImplementation,
    ExtensionSourceInfo,
    ExtensionSourceMapping,
    Hook,
    HookType,
    N8nWorkflowConfig,
    OnFailure,
    ExecutionMode,
    DeploymentType,
)
from sap_cloud_sdk.extensibility.client import ExtensibilityClient
from sap_cloud_sdk.extensibility.exceptions import HookShortCircuit
from http import HTTPMethod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hook(
    hook_id: str = "h-1",
    hook_type: HookType = HookType.BEFORE,
    can_short_circuit: bool = True,
    on_failure: OnFailure = OnFailure.CONTINUE,
    name: str = "my-hook",
) -> Hook:
    return Hook(
        id=hook_id,
        hook_id=hook_id,
        n8n_workflow_config=N8nWorkflowConfig(
            ord_id="sap.n8n:api:wf:v1",
            card_ord_id="card-ord",
            tool_name="execute_workflow",
            global_tenant_id="gtid",
            method=HTTPMethod.POST,
        ),
        name=name,
        type=hook_type,
        deployment_type=DeploymentType.N8N,
        timeout=30,
        execution_mode=ExecutionMode.SYNC,
        on_failure=on_failure,
        order=0,
        can_short_circuit=can_short_circuit,
    )


def _make_source_info(solution_id: str = "sol-1") -> ExtensionSourceInfo:
    return ExtensionSourceInfo(
        extension_name="ext-a",
        extension_version="1.0",
        extension_id="ext-id-a",
        solution_id=solution_id,
    )


def _make_client(call_hook_agw_return=None) -> ExtensibilityClient:
    transport = MagicMock()
    client = ExtensibilityClient(transport)
    client.call_hook_agw = AsyncMock(return_value=call_hook_agw_return)  # type: ignore[method-assign]
    return client


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# emit_instruction_spans
# ---------------------------------------------------------------------------


class TestEmitInstructionSpans:
    def test_no_op_on_none_ext_impl(self):
        client = _make_client()
        client.emit_instruction_spans(None)  # should not raise

    def test_no_op_when_no_source(self):
        impl = ExtensionCapabilityImplementation(capability_id="default")
        client = _make_client()
        client.emit_instruction_spans(impl)

    def test_no_op_when_empty_instructions(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(tools={}, hooks={}, instructions={}),
        )
        client = _make_client()
        client.emit_instruction_spans(impl)

    def test_one_span_per_instruction(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="cap-1",
            source=ExtensionSourceMapping(
                tools={},
                hooks={},
                instructions={
                    "ext-1": _make_source_info("sol-1"),
                    "ext-2": _make_source_info("sol-2"),
                },
            ),
        )
        client = _make_client()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with patch(
            "sap_cloud_sdk.extensibility.client._otel_trace"
            if False
            else "opentelemetry.trace.get_tracer",
            return_value=mock_tracer,
        ):
            with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer):
                client.emit_instruction_spans(impl)
                assert mock_tracer.start_as_current_span.call_count == 2
                calls = mock_tracer.start_as_current_span.call_args_list
                names = [c[0][0] for c in calls]
                assert all(n == "extension_instruction" for n in names)


# ---------------------------------------------------------------------------
# run_hooks
# ---------------------------------------------------------------------------


class TestRunHooksFiltering:
    def test_only_matching_type_runs(self):
        before_hook = _make_hook(hook_id="b-1", hook_type=HookType.BEFORE)
        after_hook = _make_hook(hook_id="a-1", hook_type=HookType.AFTER)
        client = _make_client()
        message = MagicMock()
        message.parts = []

        _run(
            client.run_hooks(
                [before_hook, after_hook],
                HookType.BEFORE,
                message,
            )
        )
        assert client.call_hook_agw.call_count == 1  # type: ignore[union-attr]  # ty: ignore[unresolved-attribute]
        call_hook_arg = client.call_hook_agw.call_args[1]["hook"]  # type: ignore[union-attr]  # ty: ignore[unresolved-attribute]
        assert call_hook_arg.id == "b-1"

    def test_empty_hooks_returns_zero_duration(self):
        client = _make_client()
        message = MagicMock()
        message.parts = []
        duration = _run(client.run_hooks([], HookType.BEFORE, message))
        assert duration == 0.0

    def test_no_hooks_of_type_returns_zero(self):
        hook = _make_hook(hook_type=HookType.AFTER)
        client = _make_client()
        message = MagicMock()
        message.parts = []
        duration = _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert duration == 0.0
        assert client.call_hook_agw.call_count == 0  # type: ignore[union-attr]  # ty: ignore[unresolved-attribute]


class TestRunHooksReturnsDuration:
    def test_positive_duration_returned(self):
        hook = _make_hook(hook_type=HookType.BEFORE)
        client = _make_client(call_hook_agw_return=None)
        message = MagicMock()
        message.parts = []
        duration = _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert duration >= 0.0


class TestRunHooksCallbacks:
    def test_status_callback_called_per_hook(self):
        hook1 = _make_hook(hook_id="h1", name="hook-one")
        hook2 = _make_hook(hook_id="h2", name="hook-two")
        client = _make_client()
        message = MagicMock()
        message.parts = []
        callback = AsyncMock()

        _run(
            client.run_hooks(
                [hook1, hook2],
                HookType.BEFORE,
                message,
                status_callback=callback,
            )
        )
        assert callback.call_count == 2
        texts = [c[0][0] for c in callback.call_args_list]
        assert all("pre-execution hook" in t for t in texts)

    def test_audit_emitted_when_channel_id_set(self):
        hook = _make_hook()
        client = _make_client()
        client._audit_channel_id = "my-agent"
        client._audit_service_name = "my-agent"
        message = MagicMock()
        message.parts = []

        with patch(
            "sap_cloud_sdk.extensibility._audit._emit_hook_executed",
            new=AsyncMock(),
        ) as mock_emit:
            _run(
                client.run_hooks(
                    [hook],
                    HookType.BEFORE,
                    message,
                    tenant_subdomain="t-sub",
                    tenant_id="t-id",
                    user_id="u-id",
                    ext_impl=ExtensionCapabilityImplementation(capability_id="cap-1"),
                )
            )
        assert mock_emit.call_count == 1
        kw = mock_emit.call_args[1]
        assert kw["phase"] == "pre"
        assert kw["hook_name"] == "my-hook"
        assert kw["capability_id"] == "cap-1"
        assert kw["channel_id"] == "my-agent"

    def test_audit_not_emitted_when_no_channel_id(self):
        hook = _make_hook()
        client = _make_client()  # _audit_channel_id == "" by default
        message = MagicMock()
        message.parts = []

        with patch(
            "sap_cloud_sdk.extensibility._audit._emit_hook_executed",
            new=AsyncMock(),
        ) as mock_emit:
            _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert mock_emit.call_count == 0

    def test_no_callback_does_not_raise(self):
        hook = _make_hook()
        client = _make_client()
        message = MagicMock()
        message.parts = []
        _run(client.run_hooks([hook], HookType.BEFORE, message))


class TestRunHooksShortCircuit:
    def test_raises_on_stop_execution_with_can_short_circuit(self):
        hook = _make_hook(can_short_circuit=True)
        response = MagicMock()
        response.parts = []
        response.metadata = {
            "stop_execution": True,
            "stop_execution_reason": "blocked",
        }
        client = _make_client(call_hook_agw_return=response)
        message = MagicMock()
        message.parts = []

        with pytest.raises(HookShortCircuit) as exc_info:
            _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert "blocked" in str(exc_info.value)

    def test_no_short_circuit_when_can_short_circuit_false(self):
        hook = _make_hook(can_short_circuit=False)
        response = MagicMock()
        response.parts = []
        response.metadata = {"stop_execution": True}
        client = _make_client(call_hook_agw_return=response)
        message = MagicMock()
        message.parts = []
        _run(client.run_hooks([hook], HookType.BEFORE, message))

    def test_short_circuit_audit_emitted_before_raise(self):
        hook = _make_hook(can_short_circuit=True)
        response = MagicMock()
        response.parts = []
        response.metadata = {"stop_execution": True, "stop_execution_reason": "blocked"}
        client = _make_client(call_hook_agw_return=response)
        client._audit_channel_id = "my-agent"
        client._audit_service_name = "my-agent"
        message = MagicMock()
        message.parts = []

        with patch(
            "sap_cloud_sdk.extensibility._audit._emit_hook_short_circuit",
            new=AsyncMock(),
        ) as mock_emit:
            with pytest.raises(HookShortCircuit):
                _run(
                    client.run_hooks(
                        [hook],
                        HookType.BEFORE,
                        message,
                        ext_impl=ExtensionCapabilityImplementation(capability_id="cap"),
                    )
                )
        assert mock_emit.call_count == 1

    def test_raises_on_timeout_with_block_policy(self):
        hook = _make_hook(on_failure=OnFailure.BLOCK)
        client = _make_client()
        client.call_hook_agw = AsyncMock(side_effect=asyncio.TimeoutError())
        message = MagicMock()
        message.parts = []

        with pytest.raises(HookShortCircuit) as exc_info:
            _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert "timed out" in str(exc_info.value)

    def test_continues_on_timeout_with_continue_policy(self):
        hook = _make_hook(on_failure=OnFailure.CONTINUE)
        client = _make_client()
        client.call_hook_agw = AsyncMock(side_effect=asyncio.TimeoutError())
        message = MagicMock()
        message.parts = []
        _run(client.run_hooks([hook], HookType.BEFORE, message))

    def test_raises_on_exception_with_block_policy(self):
        hook = _make_hook(on_failure=OnFailure.BLOCK)
        client = _make_client()
        client.call_hook_agw = AsyncMock(side_effect=RuntimeError("network error"))
        message = MagicMock()
        message.parts = []

        with pytest.raises(HookShortCircuit) as exc_info:
            _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert "failed" in str(exc_info.value)

    def test_continues_on_exception_with_continue_policy(self):
        hook = _make_hook(on_failure=OnFailure.CONTINUE)
        client = _make_client()
        client.call_hook_agw = AsyncMock(side_effect=RuntimeError("network error"))
        message = MagicMock()
        message.parts = []
        _run(client.run_hooks([hook], HookType.BEFORE, message))


class TestRunHooksPartsAppended:
    def test_response_parts_appended_to_message(self):
        hook = _make_hook()
        response = MagicMock()
        part = MagicMock()
        response.parts = [part]
        response.metadata = {}
        client = _make_client(call_hook_agw_return=response)
        message = MagicMock()
        message.parts = []

        _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert part in message.parts

    def test_none_response_parts_not_extended(self):
        hook = _make_hook()
        client = _make_client(call_hook_agw_return=None)
        message = MagicMock()
        message.parts = []

        _run(client.run_hooks([hook], HookType.BEFORE, message))
        assert message.parts == []
