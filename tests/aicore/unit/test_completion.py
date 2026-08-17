"""Unit tests for sap_cloud_sdk.aicore.completion / acompletion wrappers.

The wrappers exist so callers can rely on a single exception type
(:class:`ContentFilteredError`) for "filter blocked you" regardless of
whether the rejection happened on input (litellm wraps it in
``APIConnectionError`` because the 4xx triggers ``raise_for_status()``
before our transport patch runs) or output (already raised by the
transport patch as :class:`ContentFilteredError`). Test focus:

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
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import litellm
import pytest

from sap_cloud_sdk.aicore import acompletion, completion
from sap_cloud_sdk.aicore.completion import (
    reload_aicore_credentials,
    _clear_client_secret,
    _reset_secret_cleared,
)
from sap_cloud_sdk.aicore.filtering.exceptions import ContentFilteredError


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
# reload_aicore_credentials()
# ---------------------------------------------------------------------------


class TestReloadAICoreCredentials:
    def test_calls_set_aicore_config(self):
        with patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_config:
            reload_aicore_credentials()
        mock_config.assert_called_once_with()

    def test_resets_secret_cleared_flag(self):
        """After reload, _clear_client_secret() must be able to clear the secret again."""
        # Simulate: secret was cleared once already
        with patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "old"}):
            _clear_client_secret()
        # Flag is now True — a second clear would be a no-op
        with patch("sap_cloud_sdk.aicore.set_aicore_config"):
            reload_aicore_credentials()
        # After reload the flag is reset — clearing works again
        with patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "new"}):
            _clear_client_secret()
            assert "AICORE_CLIENT_SECRET" not in os.environ


# ---------------------------------------------------------------------------
# CLIENT_SECRET minimisation — _clear_client_secret()
# ---------------------------------------------------------------------------


class TestClearClientSecret:
    def setup_method(self):
        _reset_secret_cleared()

    def test_removes_secret_from_env(self):
        with patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "s3cr3t"}):
            _clear_client_secret()
            assert "AICORE_CLIENT_SECRET" not in os.environ

    def test_noop_when_secret_absent(self):
        env = {}
        with patch.dict("os.environ", env, clear=True):
            _clear_client_secret()  # must not raise

    def test_idempotent_second_call_is_noop(self):
        with patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "s3cr3t"}):
            _clear_client_secret()
            os.environ["AICORE_CLIENT_SECRET"] = "restored"
            _clear_client_secret()
            # second call must not remove the restored value
            assert os.environ.get("AICORE_CLIENT_SECRET") == "restored"

    def test_reset_allows_clear_again(self):
        with patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "s3cr3t"}):
            _clear_client_secret()
            _reset_secret_cleared()
            os.environ["AICORE_CLIENT_SECRET"] = "new-secret"
            _clear_client_secret()
            assert "AICORE_CLIENT_SECRET" not in os.environ


# ---------------------------------------------------------------------------
# completion() clears secret on success
# ---------------------------------------------------------------------------


class TestCompletionClearsSecret:
    def setup_method(self):
        _reset_secret_cleared()

    def test_secret_cleared_after_successful_call(self):
        sentinel = object()
        with (
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", return_value=sentinel),
            patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "s3cr3t"}),
        ):
            result = completion(model="sap/x", messages=[])
        assert result is sentinel
        assert "AICORE_CLIENT_SECRET" not in os.environ

    def test_secret_not_cleared_on_filter_error(self):
        """Filter errors are not successful calls — secret stays until next success."""
        from sap_cloud_sdk.aicore.filtering.exceptions import ContentFilteredError
        raised = ContentFilteredError(direction="input", details={}, request_id="r")
        secret_present_after = {}
        with patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "s3cr3t"}):
            with pytest.raises(ContentFilteredError):
                with patch(
                    "sap_cloud_sdk.aicore.completion.litellm.completion",
                    side_effect=raised,
                ):
                    completion(model="sap/x", messages=[])
            secret_present_after["value"] = os.environ.get("AICORE_CLIENT_SECRET")
        assert secret_present_after["value"] == "s3cr3t"

    def test_secret_cleared_after_auth_error_and_retry(self):
        """After reload + successful retry, secret must be cleared."""
        sentinel = object()
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        call_returns = [auth_err, sentinel]

        def fake_completion(*args, **kwargs):
            result = call_returns.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with (
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=fake_completion),
            patch("sap_cloud_sdk.aicore.set_aicore_config"),
            patch.dict("os.environ", {"AICORE_CLIENT_SECRET": "s3cr3t"}),
        ):
            result = completion(model="sap/x", messages=[])

        assert result is sentinel
        assert "AICORE_CLIENT_SECRET" not in os.environ


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
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=fake_completion),
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
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=auth_err),
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
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=raised),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_reload,
        ):
            with pytest.raises(ValueError):
                completion(model="sap/x", messages=[])

        mock_reload.assert_not_called()


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
            patch("sap_cloud_sdk.aicore.completion.litellm.acompletion", side_effect=fake_acompletion),
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
            patch("sap_cloud_sdk.aicore.completion.litellm.acompletion", side_effect=fake_acompletion),
            patch("sap_cloud_sdk.aicore.set_aicore_config"),
        ):
            with pytest.raises(litellm.AuthenticationError):
                asyncio.run(acompletion(model="sap/x", messages=[]))


# ---------------------------------------------------------------------------
# Proxy mode — model aliasing in completion() / acompletion()
# ---------------------------------------------------------------------------


class TestCompletionProxyModeAliasing:
    """completion() rewrites sap/<model> → litellm_proxy/<model> when proxy is active."""

    def setup_method(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(False)

    def teardown_method(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(False)

    def test_sap_model_rewritten_when_proxy_active(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(True)
        sentinel = object()
        captured = {}

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=lambda *a, **kw: captured.update(kw) or sentinel,
        ):
            result = completion(model="sap/gpt-4o", messages=[])

        assert result is sentinel
        assert captured["model"] == "litellm_proxy/gpt-4o"

    def test_model_unchanged_when_proxy_not_active(self):
        sentinel = object()
        captured = {}

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=lambda *a, **kw: captured.update(kw) or sentinel,
        ):
            result = completion(model="sap/gpt-4o", messages=[])

        assert result is sentinel
        assert captured["model"] == "sap/gpt-4o"

    def test_non_sap_model_unchanged_even_when_proxy_active(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(True)
        sentinel = object()
        captured = {}

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.completion",
            side_effect=lambda *a, **kw: captured.update(kw) or sentinel,
        ):
            result = completion(model="openai/gpt-4o", messages=[])

        assert result is sentinel
        assert captured["model"] == "openai/gpt-4o"

    def test_proxy_rewrite_on_auth_error_retry(self):
        """Model aliasing is applied on both the initial call and the retry."""
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(True)

        sentinel = object()
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        call_models = []

        def fake_completion(*args, **kwargs):
            call_models.append(kwargs.get("model"))
            if len(call_models) == 1:
                raise auth_err
            return sentinel

        with (
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=fake_completion),
            patch("sap_cloud_sdk.aicore.set_aicore_config"),
        ):
            result = completion(model="sap/gpt-4o", messages=[])

        assert result is sentinel
        assert call_models == ["litellm_proxy/gpt-4o", "litellm_proxy/gpt-4o"]


class TestACompletionProxyModeAliasing:
    """acompletion() proxy aliasing — async path."""

    def setup_method(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(False)

    def teardown_method(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(False)

    def test_sap_model_rewritten_when_proxy_active(self):
        from sap_cloud_sdk.aicore.completion import _set_proxy_active
        _set_proxy_active(True)
        sentinel = object()
        captured = {}

        async def fake_acompletion(*args, **kwargs):
            captured.update(kwargs)
            return sentinel

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion,
        ):
            result = asyncio.run(acompletion(model="sap/gpt-4o", messages=[]))

        assert result is sentinel
        assert captured["model"] == "litellm_proxy/gpt-4o"

    def test_model_unchanged_when_proxy_not_active(self):
        sentinel = object()
        captured = {}

        async def fake_acompletion(*args, **kwargs):
            captured.update(kwargs)
            return sentinel

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion,
        ):
            result = asyncio.run(acompletion(model="sap/gpt-4o", messages=[]))

        assert result is sentinel
        assert captured["model"] == "sap/gpt-4o"
