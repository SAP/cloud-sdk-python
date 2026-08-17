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

Credential handling
-------------------
CLIENT_SECRET minimisation (AFSDK-4291):
After the first successful LiteLLM call, ``AICORE_CLIENT_SECRET`` is removed
from ``os.environ``. LiteLLM has already captured the secret inside its token
creator closure at that point and no longer needs the env var. This minimises
the window of exposure to child processes and container introspection.

Credential rotation (reactive reload):
When a credential is rotated while the pod is running, LiteLLM's cached token
becomes invalid and the next token refresh raises ``litellm.AuthenticationError``.
The wrappers intercept this, reload credentials from the mounted secret volume
via :func:`reload_aicore_credentials`, and retry once. The secret is cleared
again after the retry succeeds.

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
import os
import threading
from typing import Any

import litellm

from .filtering.filters import _parse_input_filter_error

logger = logging.getLogger(__name__)

# Tracks whether AICORE_CLIENT_SECRET has already been cleared after the first
# successful LiteLLM call. Reset when credentials are reloaded so the secret
# is cleared again after the retry succeeds.
_secret_lock = threading.Lock()
_secret_cleared = False

# Proxy mode state — set by _configure_proxy_mode() in __init__.py.
# When active, completion() rewrites sap/<model> → litellm_proxy/<model>.
_proxy_lock = threading.Lock()
_proxy_active: bool = False


def _set_proxy_active(value: bool) -> None:
    """Activate or deactivate proxy model aliasing (called by set_aicore_config)."""
    global _proxy_active
    with _proxy_lock:
        _proxy_active = value


def _rewrite_model_for_proxy(kwargs: dict) -> dict:
    """Rewrite sap/<model> to litellm_proxy/<model> when proxy mode is active."""
    model = kwargs.get("model", "")
    if isinstance(model, str) and model.startswith("sap/"):
        return {**kwargs, "model": "litellm_proxy/" + model[4:]}
    return kwargs


def _clear_client_secret() -> None:
    """Remove AICORE_CLIENT_SECRET from env after LiteLLM has cached the token.

    Safe to call multiple times — subsequent calls are no-ops once cleared.
    No-op in transparent TLS mode (secret was never written).
    """
    global _secret_cleared
    with _secret_lock:
        if not _secret_cleared:
            if os.environ.pop("AICORE_CLIENT_SECRET", None) is not None:
                logger.info(
                    "AICORE_CLIENT_SECRET cleared from environment "
                    "after token acquisition (AFSDK-4291)"
                )
            _secret_cleared = True


def _reset_secret_cleared() -> None:
    """Allow _clear_client_secret() to fire again after a credential reload."""
    global _secret_cleared
    with _secret_lock:
        _secret_cleared = False


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
    _reset_secret_cleared()
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

    After the first successful call, ``AICORE_CLIENT_SECRET`` is removed from
    ``os.environ`` — LiteLLM has captured it in its token creator closure and
    no longer needs the env var (AFSDK-4291).

    On ``AuthenticationError`` (e.g. rotated client_secret or mTLS cert),
    reloads credentials from the mounted secret volume and retries once.

    When proxy mode is active (``AICORE_PROXY_URL`` set), rewrites
    ``sap/<model>`` to ``litellm_proxy/<model>`` transparently.
    """
    with _proxy_lock:
        proxy = _proxy_active
    if proxy:
        kwargs = _rewrite_model_for_proxy(kwargs)
    try:
        result = litellm.completion(*args, **kwargs)
        _clear_client_secret()
        return result
    except litellm.AuthenticationError:
        reload_aicore_credentials()
        with _proxy_lock:
            proxy = _proxy_active
        if proxy:
            kwargs = _rewrite_model_for_proxy(kwargs)
        result = litellm.completion(*args, **kwargs)
        _clear_client_secret()
        return result
    except Exception as exc:
        translated = _maybe_translate_filter_error(exc)
        if translated is exc:
            raise
        raise translated from exc


async def acompletion(*args: Any, **kwargs: Any) -> Any:
    """Async wrapper around :func:`litellm.acompletion`.

    Same credential-minimisation, rotation, and proxy aliasing semantics as
    :func:`completion`.
    """
    with _proxy_lock:
        proxy = _proxy_active
    if proxy:
        kwargs = _rewrite_model_for_proxy(kwargs)
    try:
        result = await litellm.acompletion(*args, **kwargs)
        _clear_client_secret()
        return result
    except litellm.AuthenticationError:
        reload_aicore_credentials()
        with _proxy_lock:
            proxy = _proxy_active
        if proxy:
            kwargs = _rewrite_model_for_proxy(kwargs)
        result = await litellm.acompletion(*args, **kwargs)
        _clear_client_secret()
        return result
    except Exception as exc:
        translated = _maybe_translate_filter_error(exc)
        if translated is exc:
            raise
        raise translated from exc


__all__ = ["completion", "acompletion", "reload_aicore_credentials"]
