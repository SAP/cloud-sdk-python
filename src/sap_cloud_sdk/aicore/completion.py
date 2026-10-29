"""Thin LiteLLM ``completion`` / ``acompletion`` wrappers for SAP AI Core.

The orchestration v2 server signals input-filter rejection with HTTP 400 +
``error.location = "Filtering Module - Input Filter"``. LiteLLM's transport
calls ``raise_for_status()`` on 4xx responses **before** our patched
``transform_response`` runs, so the 400 surfaces in user code as a
``litellm.APIConnectionError`` whose ``str(exc)`` contains the JSON body of
the rejection. Output-filter rejections in buffered (non-streaming) mode
(HTTP 200 with ``finish_reason == "content_filter"``) go through
``transform_response`` and surface as :class:`ContentFilteredError`.

That asymmetry would force callers to catch two exception types — these
wrappers fix it by catching the wrapped exception inside the SDK and
re-raising as :class:`ContentFilteredError` so callers can rely on a
single exception type for "filter blocked you."

Streaming + output filtering
----------------------------
When output filtering is active and ``stream=True``, the v2 API streams
chunks normally and signals a filter rejection via an in-stream error event
(no ``[DONE]``). LiteLLM's ``SAPStreamIterator`` surfaces this as a
``ValueError`` raised from inside the iterator. These wrappers detect when
output filtering is active and return a *filtering wrapper* around the
iterator that catches that ``ValueError`` and re-raises it as
:class:`ContentFilteredError`.

Agent frameworks (``ChatLiteLLM``, LangGraph, etc.) that call
``litellm.completion`` directly — bypassing this wrapper — will see the raw
``ValueError`` from the iterator. They must use
:func:`sap_cloud_sdk.aicore.completion` to get the typed :class:`ContentFilteredError`.

Credential rotation handling
----------------------------
When a credential (client_secret) is rotated while the pod is running,
LiteLLM's cached token becomes invalid and the next token refresh attempt
raises ``litellm.AuthenticationError``. The wrappers intercept this error,
reload credentials from the mounted secret volume via
:func:`sap_cloud_sdk.aicore.set_aicore_config`, and retry the call once.
The caller is unaffected — rotation is transparent. If the retry also
fails, the ``AuthenticationError`` propagates normally.

Usage::

    from sap_cloud_sdk.aicore import completion, ContentFilteredError

    try:
        response = completion(
            model="sap/anthropic--claude-4.5-sonnet",
            messages=[{"role": "user", "content": "Hello!"}],
        )
    except ContentFilteredError as e:
        # e.direction: "input" or "output"
        # e.details: severity scores from the server (safe to log)
        # e.request_id: for debugging
        ...

These are intentionally thin — every other keyword argument is forwarded
verbatim to ``litellm.completion`` / ``litellm.acompletion``.

No telemetry is recorded here; the wrappers fire on every LLM call and a
counter at this level would be both noisy and uninformative about
adoption of the SDK.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

import litellm

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation
from .filtering.filters import _parse_input_filter_error
from .filtering import _patch as _filtering_patch
from .filtering._patch import _parse_output_filter_stream_error

logger = logging.getLogger(__name__)


@record_metrics(Module.AICORE, Operation.AICORE_REACTIVE_RELOAD)
def _reload_reactive() -> None:
    # Local import avoids circular dep: completion ← __init__ ← completion
    from sap_cloud_sdk.aicore import set_aicore_config

    logger.info("AI Core credentials reloading after authentication failure")
    set_aicore_config()


def _maybe_translate_filter_error(exc: BaseException) -> BaseException:
    """Return a :class:`ContentFilteredError` if ``exc`` is a wrapped
    input-filter rejection, otherwise return ``exc`` unchanged.

    Uses ``BaseException`` so non-Exception derivatives flowing through here
    (e.g. ``KeyboardInterrupt``) pass through without parser invocation.
    """
    if not isinstance(exc, Exception):
        return exc
    blocked = _parse_input_filter_error(exc)
    return blocked if blocked is not None else exc


def _output_filtering_active() -> bool:
    cfg = _filtering_patch._active_cfg
    return cfg is not None and cfg.output_filtering is not None


class _FilteringStreamWrapper:
    """Sync iterator wrapper that converts in-stream output-filter errors."""

    def __init__(self, stream: Iterator) -> None:
        self._stream = stream

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Any:
        try:
            return next(self._stream)
        except StopIteration:
            raise
        except ValueError as exc:
            translated = _parse_output_filter_stream_error(exc)
            if translated is not None:
                raise translated from exc
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class _AsyncFilteringStreamWrapper:
    """Async iterator wrapper that converts in-stream output-filter errors."""

    def __init__(self, stream: AsyncIterator) -> None:
        self._stream = stream

    def __aiter__(self) -> AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        try:
            return await self._stream.__anext__()
        except StopAsyncIteration:
            raise
        except (ValueError, Exception) as exc:
            translated = _parse_output_filter_stream_error(exc)
            if translated is not None:
                raise translated from exc
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


def completion(*args: Any, **kwargs: Any) -> Any:
    """Wrapper around :func:`litellm.completion` that normalises filter errors
    and handles credential rotation transparently.

    On ``AuthenticationError`` (e.g. rotated client_secret or mTLS cert),
    reloads credentials from the mounted secret volume and retries once.

    When output filtering is active and ``stream=True``, wraps the returned
    iterator so that in-stream output-filter rejections surface as
    :class:`ContentFilteredError` rather than a raw ``ValueError``.

    Model strings (e.g. ``sap/<model>``) are passed verbatim to LiteLLM in all
    routing modes — proxy routing is handled by ``litellm.api_base`` configured
    in :func:`set_aicore_config`, not by rewriting the model name.
    """
    is_streaming = kwargs.get("stream", False)
    try:
        result = litellm.completion(*args, **kwargs)
    except litellm.AuthenticationError:
        _reload_reactive()
        result = litellm.completion(*args, **kwargs)
    except Exception as exc:
        translated = _maybe_translate_filter_error(exc)
        if translated is exc:
            raise
        raise translated from exc

    if is_streaming and _output_filtering_active():
        return _FilteringStreamWrapper(result)
    return result


async def acompletion(*args: Any, **kwargs: Any) -> Any:
    """Async wrapper around :func:`litellm.acompletion`.

    Same credential-rotation and output-filter stream-wrapping semantics as
    :func:`completion`.
    Model strings are passed verbatim to LiteLLM in all routing modes.
    """
    is_streaming = kwargs.get("stream", False)
    try:
        result = await litellm.acompletion(*args, **kwargs)
    except litellm.AuthenticationError:
        _reload_reactive()
        result = await litellm.acompletion(*args, **kwargs)
    except Exception as exc:
        translated = _maybe_translate_filter_error(exc)
        if translated is exc:
            raise
        raise translated from exc

    if is_streaming and _output_filtering_active():
        return _AsyncFilteringStreamWrapper(result)
    return result


__all__ = ["completion", "acompletion"]
