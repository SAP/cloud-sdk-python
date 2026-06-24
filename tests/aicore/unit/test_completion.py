"""Unit tests for sap_cloud_sdk.aicore.completion / acompletion wrappers
and the extract_filter_blocked deprecation path.

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
- ``extract_filter_blocked`` still works for back-compat but emits a
  ``DeprecationWarning``.
"""

from __future__ import annotations

import asyncio
import json
import warnings
from unittest.mock import patch

import pytest

from sap_cloud_sdk.aicore import acompletion, completion
from sap_cloud_sdk.aicore.filtering.exceptions import ContentFilteredError
from sap_cloud_sdk.aicore.filtering.filters import extract_filter_blocked


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

        async def fake_acompletion(**kwargs):
            raise raised

        with patch(
            "sap_cloud_sdk.aicore.completion.litellm.acompletion",
            side_effect=fake_acompletion,
        ):
            with pytest.raises(_FakeAPIConnectionError) as ei:
                asyncio.run(acompletion(model="sap/x", messages=[]))
        assert ei.value is raised


# ---------------------------------------------------------------------------
# extract_filter_blocked deprecation
# ---------------------------------------------------------------------------


class TestExtractFilterBlockedDeprecation:
    def test_emits_deprecation_warning(self):
        exc = _FakeAPIConnectionError(_input_filter_apiconn_message())
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            result = extract_filter_blocked(exc)
        deprecations = [
            w for w in recorded if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecations) == 1
        assert "deprecated" in str(deprecations[0].message)
        # Behaviour preserved — still returns the parsed error.
        assert isinstance(result, ContentFilteredError)
        assert result.direction == "input"

    def test_returns_none_for_non_filter_exception(self):
        exc = ValueError("not a filter rejection")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = extract_filter_blocked(exc)
        assert result is None

    def test_not_exported_from_aicore_top_level(self):
        # Symbol stays importable from the deep path (back-compat) but is
        # removed from sap_cloud_sdk.aicore.__all__.
        import sap_cloud_sdk.aicore as aicore

        assert "extract_filter_blocked" not in aicore.__all__
