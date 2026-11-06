"""Exceptions for the aicore.filtering module."""

from __future__ import annotations

from typing import Any, Literal


class OrchestrationError(Exception):
    """Base exception for SAP AI Core orchestration-module errors.

    The orchestration *API surface* (filtering, future grounding/masking) lives
    under ``sap_cloud_sdk.aicore.filtering``. This base class is the catchable
    parent for any orchestration-module error the SDK surfaces.
    """


class ContentFilteredError(OrchestrationError):
    """Raised when the orchestration filtering module rejects input or output.

    Attributes:
        direction: ``"input"`` if the user prompt was rejected (HTTP 4xx,
            ``error.location`` startswith ``"Filtering Module - Input Filter"``),
            or ``"output"`` if the model response was rejected. In non-streaming
            responses this is signalled by ``finish_reason == "content_filter"``
            (HTTP 200). In streaming responses, the server sends an in-stream
            error event which :func:`sap_cloud_sdk.aicore.completion` translates
            into this exception from inside the iterator.
        details: Severity scalars from ``intermediate_results.{input,output}_filtering.data``.
            Safe to log; does NOT include raw prompt or completion content.
        request_id: ``error.request_id`` (input) or top-level ``request_id`` (output).
    """

    direction: Literal["input", "output"]
    details: dict[str, Any]
    request_id: str | None

    def __init__(
        self,
        *,
        direction: Literal["input", "output"],
        details: dict[str, Any],
        request_id: str | None,
    ) -> None:
        self.direction = direction
        self.details = details
        self.request_id = request_id
        super().__init__(
            f"Content filter blocked the {direction} (request_id={request_id})"
        )


class ContentFilteringNotConfiguredError(OrchestrationError):
    """Raised in strict mode when a request would be sent WITHOUT content filtering.

    Strict (fail-closed) mode is opt-in via the ``AICORE_FILTER_STRICT``
    environment variable or the ``strict=`` argument to
    :func:`sap_cloud_sdk.aicore.set_filtering`. When active, the SDK refuses to
    send an unfiltered orchestration request instead of silently failing open.

    This is raised when:

    - ``completion()`` is called but content filtering was never configured
      (neither :func:`set_aicore_config` nor :func:`set_filtering` ran), or
    - the active :class:`ContentFiltering` serialises to an empty wire payload
      (e.g. ``ContentFiltering()`` with no input or output direction).

    In the default (non-strict) mode these conditions emit a
    ``logging.WARNING`` and the request proceeds unfiltered.
    """
