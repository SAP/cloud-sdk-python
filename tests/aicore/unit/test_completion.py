"""Unit tests for sap_cloud_sdk.aicore.completion / acompletion wrappers.

The wrappers exist so callers can rely on a single exception type
(:class:`ContentFilteredError`) for "filter blocked you" regardless of
whether the rejection happened on input (litellm wraps it in
``APIConnectionError`` because the 4xx triggers ``raise_for_status()``
before our transport patch runs) or output (already raised by the
transport patch as :class:`ContentFilteredError` in buffered mode, or
raised from the stream iterator in streaming mode). Test focus:

- Successful calls pass through verbatim.
- An input-filter-shaped ``APIConnectionError`` is re-raised as
  :class:`ContentFilteredError` with the parsed ``direction``, ``details``,
  and ``request_id``.
- Non-filter exceptions surface unchanged (we don't swallow real errors).
- :class:`ContentFilteredError` already raised by the transport patch
  passes through unchanged (we don't double-wrap).
- ``acompletion`` exhibits the same behaviour on the async path.
- On ``AuthenticationError``, credentials are reloaded and the call is
  retried once (credential rotation without pod restart).
- With output filtering active and ``stream=True``, the returned iterator
  catches in-stream ``ValueError`` filter errors and raises
  :class:`ContentFilteredError`.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import litellm
import pytest

from sap_cloud_sdk.aicore import acompletion, completion
from sap_cloud_sdk.aicore.filtering.exceptions import (
    ContentFilteredError,
    ContentFilteringNotConfiguredError,
)


@pytest.fixture(autouse=True)
def _reset_filtering_state(monkeypatch):
    """Isolate each test from ambient AICORE_FILTER_* env and module state.

    The completion wrappers run a filtering-readiness pre-flight check that
    reads ``AICORE_FILTER_STRICT`` and module-level patch state; reset both so
    tests are hermetic regardless of order or developer environment.
    """
    import sys

    from sap_cloud_sdk.aicore.filtering import _patch as _p

    # The module is already loaded by the top-level `from sap_cloud_sdk.aicore
    # import completion` import above.  We must NOT use a bare
    # `import sap_cloud_sdk.aicore.completion` here — that shadows the function
    # name at module level and causes ty to resolve `completion(...)` calls as
    # the submodule (not callable).  Access via sys.modules instead.
    _comp_mod = sys.modules["sap_cloud_sdk.aicore.completion"]

    for k in list(os.environ):
        if k.startswith("AICORE_FILTER"):
            monkeypatch.delenv(k, raising=False)
    _p._active_cfg = None
    _p._strict_mode = False
    _p._configured = False
    # Use setattr so ty doesn't complain about an unknown attribute on ModuleType.
    setattr(_comp_mod, "_unconfigured_warned", False)
    yield


# ---------------------------------------------------------------------------
# Helpers — fake litellm responses / exceptions
# ---------------------------------------------------------------------------


class _FakeAPIConnectionError(Exception):
    """Stand-in for ``litellm.APIConnectionError``.

    We only care about ``str(exc)`` matching litellm's wrapping pattern —
    the parser keys on the embedded JSON body, not on the exception class.
    """


def _input_filter_apiconn_message() -> str:
    body = {
        "error": {
            "request_id": "req-input-filter",
            "code": 400,
            "message": "Content filtered.",
            "location": "Filtering Module - Input Filter",
            "intermediate_results": {
                "input_filtering": {
                    "data": {
                        "azure_content_safety": {
                            "Hate": 0,
                            "Violence": 4,
                            "SelfHarm": 0,
                            "Sexual": 0,
                        }
                    }
                }
            },
        }
    }
    # Matches the real shape: "SapException - {…json…}"
    return f"SapException - {json.dumps(body)}"


# ---------------------------------------------------------------------------
# completion() — sync wrapper
# ---------------------------------------------------------------------------


class TestCompletionWrapper:
    def test_success_returns_litellm_response_verbatim(self):
        sentinel = object()
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            return_value=sentinel,
        ) as mock_litellm:
            result = completion(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[{"role": "user", "content": "Hi"}],
            )
        assert result is sentinel
        mock_litellm.assert_called_once_with(
            model="sap/anthropic--claude-4.5-sonnet",
            messages=[{"role": "user", "content": "Hi"}],
        )

    def test_input_filter_wrapped_error_becomes_content_filtered_error(self):
        raised = _FakeAPIConnectionError(_input_filter_apiconn_message())
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=raised,
        ):
            with pytest.raises(ContentFilteredError) as ei:
                completion(model="sap/x", messages=[])
        err = ei.value
        assert err.direction == "input"
        assert err.request_id == "req-input-filter"
        assert err.details["azure_content_safety"]["Violence"] == 4
        # Original exception chained via __cause__ for forensics.
        assert err.__cause__ is raised

    def test_output_filter_error_passes_through_unchanged(self):
        # Output filter rejections are raised by the transport patch as
        # ContentFilteredError directly — the wrapper must not wrap them
        # again or otherwise interfere.
        original = ContentFilteredError(
            direction="output",
            details={"choices": [{"index": 0}]},
            request_id="req-output",
        )
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=original,
        ):
            with pytest.raises(ContentFilteredError) as ei:
                completion(model="sap/x", messages=[])
        # Same instance — no wrapping, no chaining.
        assert ei.value is original

    def test_non_filter_exception_surfaces_verbatim(self):
        # A real connection/transport error from litellm must not be
        # rewritten into ContentFilteredError by the parser.
        raised = _FakeAPIConnectionError("SapException - some other transport error")
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=raised,
        ):
            with pytest.raises(_FakeAPIConnectionError) as ei:
                completion(model="sap/x", messages=[])
        assert ei.value is raised

    def test_exception_without_brace_passes_through(self):
        raised = ValueError("plain message, no JSON here")
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=raised,
        ):
            with pytest.raises(ValueError) as ei:
                completion(model="sap/x", messages=[])
        assert ei.value is raised


# ---------------------------------------------------------------------------
# acompletion() — async wrapper
# ---------------------------------------------------------------------------


class TestACompletionWrapper:
    def test_success_returns_litellm_response_verbatim(self):
        sentinel = object()

        async def fake_acompletion(**kwargs):
            return sentinel

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion,
        ):
            result = asyncio.run(
                acompletion(
                    model="sap/anthropic--claude-4.5-sonnet",
                    messages=[{"role": "user", "content": "Hi"}],
                )
            )
        assert result is sentinel

    def test_input_filter_wrapped_error_becomes_content_filtered_error(self):
        raised = _FakeAPIConnectionError(_input_filter_apiconn_message())

        async def fake_acompletion(**kwargs):
            raise raised

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion,
        ):
            with pytest.raises(ContentFilteredError) as ei:
                asyncio.run(acompletion(model="sap/x", messages=[]))
        assert ei.value.direction == "input"
        assert ei.value.request_id == "req-input-filter"

    def test_non_filter_exception_surfaces_verbatim(self):
        raised = _FakeAPIConnectionError("SapException - other transport error")

        async def fake_acompletion_non_filter(**kwargs):
            raise raised

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion_non_filter,
        ):
            with pytest.raises(_FakeAPIConnectionError) as ei:
                asyncio.run(acompletion(model="sap/x", messages=[]))
        assert ei.value is raised


# ---------------------------------------------------------------------------
# Reactive reload on AuthenticationError — sync
# ---------------------------------------------------------------------------


class TestCompletionReactiveReload:
    def test_auth_error_triggers_reload_and_retry_succeeds(self):
        """On AuthenticationError, credentials reload and second call succeeds."""
        sentinel = object()
        auth_err = litellm.AuthenticationError(
            message="401 Unauthorized", llm_provider="sap", model="sap/x"
        )
        call_returns = [auth_err, sentinel]

        def fake_completion(*args, **kwargs):
            result = call_returns.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with (
            patch(
                "sap_cloud_sdk.aicore.completion.litellm.completion",
                side_effect=fake_completion,
            ),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_reload,
        ):
            result = completion(model="sap/x", messages=[])

        assert result is sentinel
        mock_reload.assert_called_once_with()

    def test_auth_error_retry_also_fails_propagates(self):
        """If the retry also raises AuthenticationError, it propagates to the caller."""
        auth_err = litellm.AuthenticationError(
            message="401 Unauthorized", llm_provider="sap", model="sap/x"
        )

        with (
            patch(
                "sap_cloud_sdk.aicore.completion.litellm.completion",
                side_effect=auth_err,
            ),
            patch("sap_cloud_sdk.aicore.set_aicore_config"),
        ):
            with pytest.raises(litellm.AuthenticationError):
                completion(model="sap/x", messages=[])

    def test_auth_error_reload_called_exactly_once(self):
        """Reload is called exactly once — no infinite retry loop."""
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        mock_litellm = MagicMock(side_effect=auth_err)

        with (
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", mock_litellm),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_reload,
        ):
            with pytest.raises(litellm.AuthenticationError):
                completion(model="sap/x", messages=[])

        mock_reload.assert_called_once()
        assert mock_litellm.call_count == 2

    def test_non_auth_error_does_not_trigger_reload(self):
        """Non-authentication errors do not trigger a credential reload."""
        raised = ValueError("some other error")

        with (
            patch(
                "sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=raised
            ),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_reload,
        ):
            with pytest.raises(ValueError):
                completion(model="sap/x", messages=[])

        mock_reload.assert_not_called()


# ---------------------------------------------------------------------------
# Streaming guard — stream=True + output filtering now supported
# ---------------------------------------------------------------------------


class TestStreamingGuard:
    """stream=True is now allowed with output filtering active.
    The returned iterator wraps filter errors into ContentFilteredError.
    Input-only filtering: stream=True passes through unmodified.
    """

    @pytest.fixture(autouse=True)
    def restore_filtering(self):
        from sap_cloud_sdk.aicore.filtering._patch import _install

        _install(None)
        yield
        _install(None)

    def _activate_input_only(self):
        from sap_cloud_sdk.aicore.filtering import (
            AzureContentFilter,
            ContentFiltering,
            InputFiltering,
            set_filtering,
        )

        set_filtering(
            ContentFiltering(
                input_filtering=InputFiltering(filters=[AzureContentFilter()])
            )
        )

    def _activate_output(self):
        from sap_cloud_sdk.aicore.filtering import (
            AzureContentFilter,
            ContentFiltering,
            OutputFiltering,
            set_filtering,
        )

        set_filtering(
            ContentFiltering(
                output_filtering=OutputFiltering(filters=[AzureContentFilter()])
            )
        )

    def _activate_input_and_output(self):
        from sap_cloud_sdk.aicore.filtering import (
            AzureContentFilter,
            ContentFiltering,
            InputFiltering,
            OutputFiltering,
            set_filtering,
        )

        set_filtering(
            ContentFiltering(
                input_filtering=InputFiltering(filters=[AzureContentFilter()]),
                output_filtering=OutputFiltering(filters=[AzureContentFilter()]),
            )
        )

    # --- no filtering or input-only: stream=True passes through --------------------

    def test_no_filtering_stream_allowed(self):
        sentinel = object()
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion", return_value=sentinel
        ):
            result = completion(model="sap/x", messages=[], stream=True)
        assert result is sentinel

    def test_input_only_filtering_stream_allowed(self):
        self._activate_input_only()
        sentinel = object()
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion", return_value=sentinel
        ):
            result = completion(model="sap/x", messages=[], stream=True)
        assert result is sentinel

    def test_acompletion_input_only_stream_allowed(self):
        sentinel = object()

        async def _fake_acompletion(*_, **__):
            return sentinel

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=_fake_acompletion,
        ):
            result = asyncio.run(acompletion(model="sap/x", messages=[], stream=True))
        assert result is sentinel

    # --- output filtering + stream=True: iterator returned (not blocked upfront) --

    def test_output_filter_stream_returns_wrapper(self):
        from sap_cloud_sdk.aicore.completion import _FilteringStreamWrapper

        self._activate_output()
        fake_stream = iter([])
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            return_value=fake_stream,
        ):
            result = completion(model="sap/x", messages=[], stream=True)
        assert isinstance(result, _FilteringStreamWrapper)

    def test_input_and_output_filter_stream_returns_wrapper(self):
        from sap_cloud_sdk.aicore.completion import _FilteringStreamWrapper

        self._activate_input_and_output()
        fake_stream = iter([])
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            return_value=fake_stream,
        ):
            result = completion(model="sap/x", messages=[], stream=True)
        assert isinstance(result, _FilteringStreamWrapper)

    def test_output_filter_no_stream_not_wrapped(self):
        from sap_cloud_sdk.aicore.completion import _FilteringStreamWrapper

        self._activate_output()
        sentinel = object()
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion", return_value=sentinel
        ):
            result = completion(model="sap/x", messages=[])
        assert result is sentinel
        assert not isinstance(result, _FilteringStreamWrapper)

    def test_acompletion_output_filter_stream_returns_async_wrapper(self):
        from sap_cloud_sdk.aicore.completion import _AsyncFilteringStreamWrapper

        self._activate_output()

        async def _fake_stream_aiter():
            return
            yield  # make it an async generator

        async def _fake_acompletion(*_, **__):
            return _fake_stream_aiter()

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=_fake_acompletion,
        ):
            result = asyncio.run(acompletion(model="sap/x", messages=[], stream=True))
        assert isinstance(result, _AsyncFilteringStreamWrapper)


# ---------------------------------------------------------------------------
# Stream output-filter iterator — ValueError from stream → ContentFilteredError
# ---------------------------------------------------------------------------


def _output_filter_stream_error_json() -> str:
    """In-stream error event JSON for an output-filter rejection (v2 shape)."""
    return json.dumps(
        {
            "error": {
                "request_id": "req-stream-out",
                "code": 500,
                "message": "Content filtered by output filter.",
                "location": "Filtering Module - Output Filter",
                "intermediate_results": {
                    "output_filtering": {
                        "data": {"azure_content_safety": {"Violence": 6, "Hate": 0}}
                    }
                },
            }
        }
    )


class TestStreamOutputFilterIterator:
    """The filtering stream wrapper catches output-filter ValueError from the iterator."""

    @pytest.fixture(autouse=True)
    def restore_filtering(self):
        from sap_cloud_sdk.aicore.filtering._patch import _install

        _install(None)
        yield
        _install(None)

    def _activate_output(self):
        from sap_cloud_sdk.aicore.filtering import (
            AzureContentFilter,
            ContentFiltering,
            OutputFiltering,
            set_filtering,
        )

        set_filtering(
            ContentFiltering(
                output_filtering=OutputFiltering(filters=[AzureContentFilter()])
            )
        )

    # --- sync wrapper ---

    def test_sync_wrapper_raises_content_filtered_on_output_filter_error(self):
        from sap_cloud_sdk.aicore.completion import _FilteringStreamWrapper

        def _bad_stream():
            raise ValueError(_output_filter_stream_error_json())
            yield  # make it a generator

        wrapper = _FilteringStreamWrapper(_bad_stream())
        with pytest.raises(ContentFilteredError) as ei:
            next(wrapper)
        assert ei.value.direction == "output"
        assert ei.value.request_id == "req-stream-out"
        assert ei.value.details["azure_content_safety"]["Violence"] == 6

    def test_sync_wrapper_yields_normal_chunks(self):
        from sap_cloud_sdk.aicore.completion import _FilteringStreamWrapper

        chunks = ["chunk1", "chunk2"]
        wrapper = _FilteringStreamWrapper(iter(chunks))
        assert list(wrapper) == chunks

    def test_sync_wrapper_passes_through_non_filter_value_error(self):
        from sap_cloud_sdk.aicore.completion import _FilteringStreamWrapper

        def _bad_stream():
            raise ValueError("some unrelated error")
            yield

        wrapper = _FilteringStreamWrapper(_bad_stream())
        with pytest.raises(ValueError, match="some unrelated error"):
            next(wrapper)

    def test_completion_stream_raises_content_filtered_on_iteration(self):
        """End-to-end: completion() + output filtering + stream=True → ContentFilteredError on next()."""
        self._activate_output()

        def _bad_stream():
            raise ValueError(_output_filter_stream_error_json())
            yield

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            return_value=_bad_stream(),
        ):
            stream = completion(model="sap/x", messages=[], stream=True)

        with pytest.raises(ContentFilteredError) as ei:
            next(stream)
        assert ei.value.direction == "output"
        assert ei.value.request_id == "req-stream-out"

    # --- async wrapper ---

    def test_async_wrapper_raises_content_filtered_on_output_filter_error(self):
        from sap_cloud_sdk.aicore.completion import _AsyncFilteringStreamWrapper

        async def _bad_async_stream():
            raise ValueError(_output_filter_stream_error_json())
            yield  # make it an async generator

        async def _run():
            wrapper = _AsyncFilteringStreamWrapper(_bad_async_stream())
            async for _ in wrapper:
                pass

        with pytest.raises(ContentFilteredError) as ei:
            asyncio.run(_run())
        assert ei.value.direction == "output"
        assert ei.value.request_id == "req-stream-out"

    def test_async_wrapper_yields_normal_chunks(self):
        from sap_cloud_sdk.aicore.completion import _AsyncFilteringStreamWrapper

        async def _good_stream():
            for item in ["a", "b", "c"]:
                yield item

        async def _run():
            result = []
            wrapper = _AsyncFilteringStreamWrapper(_good_stream())
            async for chunk in wrapper:
                result.append(chunk)
            return result

        assert asyncio.run(_run()) == ["a", "b", "c"]

    def test_async_wrapper_passes_through_non_filter_value_error(self):
        from sap_cloud_sdk.aicore.completion import _AsyncFilteringStreamWrapper

        async def _bad_async_stream():
            raise ValueError("unrelated async error")
            yield

        async def _run():
            wrapper = _AsyncFilteringStreamWrapper(_bad_async_stream())
            async for _ in wrapper:
                pass

        with pytest.raises(ValueError, match="unrelated async error"):
            asyncio.run(_run())


# ---------------------------------------------------------------------------
# Reactive reload on AuthenticationError — async
# ---------------------------------------------------------------------------


class TestACompletionReactiveReload:
    def test_auth_error_triggers_reload_and_retry_succeeds(self):
        sentinel = object()
        auth_err = litellm.AuthenticationError(
            message="401 Unauthorized", llm_provider="sap", model="sap/x"
        )
        call_returns = [auth_err, sentinel]

        async def fake_acompletion(*args, **kwargs):
            result = call_returns.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with (
            patch(
                "sap_cloud_sdk.aicore.completion.litellm.acompletion",
                side_effect=fake_acompletion,
            ),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_reload,
        ):
            result = asyncio.run(acompletion(model="sap/x", messages=[]))

        assert result is sentinel
        mock_reload.assert_called_once_with()

    def test_auth_error_retry_also_fails_propagates(self):
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )

        async def fake_acompletion(*args, **kwargs):
            raise auth_err

        with (
            patch(
                "sap_cloud_sdk.aicore.completion.litellm.acompletion",
                side_effect=fake_acompletion,
            ),
            patch("sap_cloud_sdk.aicore.set_aicore_config"),
        ):
            with pytest.raises(litellm.AuthenticationError):
                asyncio.run(acompletion(model="sap/x", messages=[]))


# ---------------------------------------------------------------------------
# Pre-flight filtering-readiness guard (_assert_filtering_ready)
# ---------------------------------------------------------------------------


class TestFilteringReadinessGuard:
    """completion()/acompletion() must not silently run with filtering never set up."""

    def test_never_configured_warns_once_and_proceeds(self, caplog):
        sentinel = object()
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            return_value=sentinel,
        ) as mock_litellm:
            with caplog.at_level("WARNING", logger="sap_cloud_sdk.aicore.completion"):
                r1 = completion(model="sap/x", messages=[])
                r2 = completion(model="sap/x", messages=[])
        assert r1 is sentinel and r2 is sentinel
        assert mock_litellm.call_count == 2
        warnings = [r for r in caplog.records if "never configured" in r.message]
        assert len(warnings) == 1  # one-time only

    def test_never_configured_strict_env_raises(self, monkeypatch):
        monkeypatch.setenv("AICORE_FILTER_STRICT", "true")
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion"
        ) as mock_litellm:
            with pytest.raises(ContentFilteringNotConfiguredError):
                completion(model="sap/x", messages=[])
        mock_litellm.assert_not_called()  # fail closed before the network call

    def test_active_filtering_no_warning(self, monkeypatch, caplog):
        from sap_cloud_sdk.aicore.filtering import set_filtering, disable_filtering
        from sap_cloud_sdk.aicore.filtering import (
            AzureContentFilter,
            ContentFiltering,
            InputFiltering,
        )

        set_filtering(
            ContentFiltering(
                input_filtering=InputFiltering(filters=[AzureContentFilter()])
            )
        )
        try:
            sentinel = object()
            with patch(
                "sap_cloud_sdk.aicore.completion.litellm.completion",
                return_value=sentinel,
            ):
                with caplog.at_level(
                    "WARNING", logger="sap_cloud_sdk.aicore.completion"
                ):
                    result = completion(model="sap/x", messages=[])
            assert result is sentinel
            assert not any("never configured" in r.message for r in caplog.records)
        finally:
            disable_filtering()

    def test_intentional_disable_no_warning(self, monkeypatch, caplog):
        from sap_cloud_sdk.aicore.filtering import disable_filtering

        disable_filtering()  # explicit opt-out → _configured True, active False
        sentinel = object()
        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            return_value=sentinel,
        ):
            with caplog.at_level("WARNING", logger="sap_cloud_sdk.aicore.completion"):
                result = completion(model="sap/x", messages=[])
        assert result is sentinel
        assert not any("never configured" in r.message for r in caplog.records)

    def test_acompletion_never_configured_strict_raises(self, monkeypatch):
        monkeypatch.setenv("AICORE_FILTER_STRICT", "true")

        async def fake_acompletion(*args, **kwargs):
            return object()

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion,
        ):
            with pytest.raises(ContentFilteringNotConfiguredError):
                asyncio.run(acompletion(model="sap/x", messages=[]))
