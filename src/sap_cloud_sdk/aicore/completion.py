"""Thin LiteLLM ``completion`` / ``acompletion`` wrappers for SAP AI Core.

The orchestration v2 server signals input-filter rejection with HTTP 400 +
``error.location = "Filtering Module - Input Filter"``. LiteLLM's transport
calls ``raise_for_status()`` on 4xx responses **before** our patched
``transform_response`` runs, so the 400 surfaces in user code as a
``litellm.APIConnectionError`` whose ``str(exc)`` contains the JSON body of
the rejection. Output-filter rejections (HTTP 200 with
``finish_reason == "content_filter"``) go through ``transform_response``
and surface as :class:`ContentFilteredError`.

That asymmetry would force callers to catch two exception types — these
wrappers fix it by catching the wrapped exception inside the SDK and
re-raising as :class:`ContentFilteredError` so callers can rely on a
single exception type for "filter blocked you."

Credential rotation handling
----------------------------
When a credential (client_secret or mTLS certificate) is rotated while the
pod is running, LiteLLM's cached token becomes invalid and the next token
refresh attempt raises ``litellm.AuthenticationError``. The wrappers
intercept this error, reload credentials from the mounted secret volume via
:func:`reload_aicore_credentials`, and retry the call once. The caller is
unaffected — rotation is transparent. If the retry also fails, the
``AuthenticationError`` propagates normally.

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
verbatim to ``litellm.completion`` / ``litellm.acompletion``, including
``stream=True`` (the streaming iterator is returned unchanged). No
telemetry is recorded here; the wrappers fire on every LLM call and a
counter at this level would be both noisy and uninformative about
adoption of the SDK.
"""

from __future__ import annotations

import logging
from typing import Any

import litellm

from .filtering.filters import _parse_input_filter_error

logger = logging.getLogger(__name__)


def reload_aicore_credentials() -> None:
    """Re-read AI Core credentials from the mounted secret volume.

    Called automatically by :func:`completion` and :func:`acompletion` when
    LiteLLM raises ``AuthenticationError`` — covers credential rotation
    (client_secret or mTLS certificate) without requiring a pod restart.

    Safe to call manually if the application needs to force a reload, e.g.
    after a deliberate secret rotation triggered by the operator.
    """
    # Import here to avoid a circular import: completion ← __init__ ← completion
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


def completion(*args: Any, **kwargs: Any) -> Any:
    """Wrapper around :func:`litellm.completion` that normalises filter errors
    and handles credential rotation transparently.

    On ``AuthenticationError`` (e.g. rotated client_secret or mTLS cert),
    reloads credentials from the mounted secret volume and retries once.
    All other exceptions surface verbatim after the filter-error translation.
    """
    try:
        return litellm.completion(*args, **kwargs)
    except litellm.AuthenticationError:
        reload_aicore_credentials()
        return litellm.completion(*args, **kwargs)
    except Exception as exc:
        translated = _maybe_translate_filter_error(exc)
        if translated is exc:
            raise
        raise translated from exc


async def acompletion(*args: Any, **kwargs: Any) -> Any:
    """Async wrapper around :func:`litellm.acompletion`.

    Same translation and credential-rotation semantics as :func:`completion`.
    """
    try:
        return await litellm.acompletion(*args, **kwargs)
    except litellm.AuthenticationError:
        reload_aicore_credentials()
        return await litellm.acompletion(*args, **kwargs)
    except Exception as exc:
        translated = _maybe_translate_filter_error(exc)
        if translated is exc:
            raise
        raise translated from exc


__all__ = ["completion", "acompletion", "reload_aicore_credentials"]
