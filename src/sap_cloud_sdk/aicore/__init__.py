"""AI Core configuration module.

This module provides utilities to load AI Core credentials from mounted secrets or environment
variables and configure them for use with LiteLLM.
"""

import json
import logging
import os
import threading
from typing import Optional

from sap_cloud_sdk.core.secret_resolver import resolve_base_mount
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation
from .completion import acompletion, completion
from .filtering import (
    AzureContentFilter,
    ContentFilter,
    ContentFilteredError,
    ContentFiltering,
    InputFiltering,
    LlamaGuard38bFilter,
    OrchestrationError,
    OutputFiltering,
    Severity,
    disable_filtering,
    set_filtering,
)

logger = logging.getLogger(__name__)

# When set, the infrastructure sidecar adds the mTLS certificate transparently.
# The SDK calls the XSUAA token endpoint over plain HTTPS with only client_id.
# No client_secret or certificate material is required in the service binding.
TRANSPARENT_TLS_ENV_VAR = "AICORE_TRANSPARENT_TLS"

# Option 3 — transparent proxy routing.
# Deployer injects these; agent code is identical in all environments.
_PROXY_URL_ENV = "AICORE_PROXY_URL"
_PROXY_API_KEY_ENV = "AICORE_PROXY_API_KEY"
_DESTINATION_NAME_ENV = "AICORE_DESTINATION_NAME"


def _is_transparent_tls() -> bool:
    """Return True when transparent TLS proxy mode is active."""
    return os.environ.get(TRANSPARENT_TLS_ENV_VAR, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _get_secret(
    env_var_name: str,
    file_name: Optional[str] = None,
    default: str = "",
    instance_name: str = "aicore-instance",
) -> str:
    """
    Get a secret value with the following priority:
    1. Try to read from /etc/secrets/appfnd/aicore/{instance_name}/{file_name}
    2. Fall back to environment variable {env_var_name}
    3. Return default value if neither exists

    Args:
        env_var_name: Name of the environment variable
        file_name: Name of the secret file (if None, uses env_var_name)
        default: Default value if neither source has the secret
        instance_name: Name of the aicore instance defined in app.yaml. Defaults to aicore-instance

    """
    resolved_base_path = resolve_base_mount()
    secrets_base_path = f"{resolved_base_path}/aicore/{instance_name}"
    secret_file_name = file_name if file_name else env_var_name
    secret_file_path = os.path.join(secrets_base_path, secret_file_name)

    # Try reading from file first
    if os.path.exists(secret_file_path):
        try:
            with open(secret_file_path, "r") as f:
                value = f.read().strip()
                if value:
                    logger.info(f"Loaded {env_var_name} from file: {secret_file_path}")
                    return value
        except Exception as e:
            logger.warning(
                f"Failed to read {env_var_name} from {secret_file_path}: {e}"
            )

    # Fall back to environment variable
    value = os.environ.get(env_var_name, default)
    if value:
        logger.info(f"Loaded {env_var_name} from environment variable")
    else:
        logger.warning(f"No value found for {env_var_name}, using default")

    return value


def _get_aicore_base_url(instance_name: str = "aicore-instance") -> str:
    """
    Get AICORE_BASE_URL with special handling for serviceurls JSON structure.
    The serviceurls file contains a JSON object with AI_API_URL field.

    Returns:
        Base URL for AI Core service
    """
    resolved_base_path = resolve_base_mount()
    secrets_base_path = f"{resolved_base_path}/aicore/{instance_name}"
    serviceurls_file = os.path.join(secrets_base_path, "serviceurls")

    # Try reading from serviceurls file
    if os.path.exists(serviceurls_file):
        try:
            with open(serviceurls_file, "r") as f:
                serviceurls_data = json.loads(f.read().strip())
                ai_api_url = serviceurls_data.get("AI_API_URL", "")
                if ai_api_url:
                    logger.info(f"Loaded AICORE_BASE_URL from file: {serviceurls_file}")
                    return ai_api_url
        except Exception as e:
            logger.warning(
                f"Failed to read AICORE_BASE_URL from {serviceurls_file}: {e}"
            )

    # Fall back to environment variable
    value = os.environ.get("AICORE_BASE_URL", "")
    if value:
        logger.info("Loaded AICORE_BASE_URL from environment variable")
    else:
        logger.warning("No value found for AICORE_BASE_URL")

    return value


@record_metrics(Module.AICORE, Operation.AICORE_SET_CONFIG)
def set_aicore_config(instance_name: str = "aicore-instance") -> None:
    """Load AI Core credentials and activate content filtering.

    Detects which routing mode is active based on environment variables:

    - ``AICORE_PROXY_URL`` set → **proxy mode**: routes all LiteLLM calls
      through a LiteLLM proxy via ``litellm.api_base``; model strings are
      passed verbatim. No AI Core credentials are written to the process
      environment.

    - ``AICORE_DESTINATION_NAME`` set → **destination mode**: loads AI Core
      credentials from a BTP Destination Service destination at startup.
      The deployer only needs to inject Destination Service binding credentials;
      the AI Core ``client_secret`` never needs to be in the K8s Secret.

    - Neither set → **direct mode** (existing behaviour): credentials are
      loaded from a mounted K8s secret volume or environment variables.
      ``AICORE_TRANSPARENT_TLS=true`` suppresses ``client_secret`` and
      relies on an mTLS sidecar.

    Agent code is identical in all three modes — the deployer controls
    routing by choosing which env vars to inject.

    After credentials are loaded, content filtering is activated on every
    ``sap/*`` LiteLLM call at the configured thresholds (default: severity
    ``MEDIUM`` on all categories + prompt shield enabled). Override via
    ``AICORE_FILTER_*`` env vars set *before* calling this function, or
    call :func:`set_filtering` afterward. Use :func:`disable_filtering`
    to turn filtering off at runtime, or set ``AICORE_FILTER_ENABLED=false``
    to keep it off entirely.
    """
    proxy_url = os.environ.get(_PROXY_URL_ENV, "")
    destination_name = os.environ.get(_DESTINATION_NAME_ENV, "")

    if proxy_url:
        _configure_proxy_mode(proxy_url)
    elif destination_name:
        _configure_destination_mode(destination_name)
    else:
        _configure_direct_mode(instance_name)

    set_filtering()


def _configure_proxy_mode(proxy_url: str) -> None:
    """Configure LiteLLM to route calls through an external proxy.

    Sets ``litellm.api_base`` / ``litellm.api_key`` globally.
    Model strings (e.g. ``sap/<model>``) are passed verbatim — no rewrite.
    No AI Core credentials are written to env.
    """
    import litellm as _litellm

    api_key = os.environ.get(_PROXY_API_KEY_ENV, "")
    _litellm.api_base = proxy_url
    if api_key:
        _litellm.api_key = api_key
    logger.info("AI Core proxy mode active — routing via %s", proxy_url)


def _configure_destination_mode(name: str) -> None:
    """Load AI Core credentials from a BTP Destination Service destination.

    Calls the Destination Service at startup to resolve the named destination
    and extracts ``clientId``, ``clientSecret``, ``tokenServiceURL``, and the
    AI Core ``URL`` from the destination configuration properties. These are
    written to the standard ``AICORE_*`` env vars so that LiteLLM can fetch
    an OAuth token from XSUAA as usual.

    Security: The deployer does NOT need to inject ``AICORE_CLIENT_SECRET``
    directly — only Destination Service binding credentials are required in
    the agent environment.

    Raises ``RuntimeError`` if the destination is not found or does not
    return ``clientId`` / ``clientSecret``.
    """
    from sap_cloud_sdk.destination import create_client  # lazy import

    client = create_client()
    dest = client.get_destination(name)

    if dest is None:
        raise RuntimeError(
            f"AI Core destination '{name}' not found in Destination Service. "
            "Check that the destination exists and the binding has access."
        )

    base_url = dest.url or ""
    if base_url and not base_url.endswith("/v2"):
        base_url = base_url.rstrip("/") + "/v2"
    if base_url:
        os.environ["AICORE_BASE_URL"] = base_url

    resource_group = dest.properties.get("resource_group", "default")
    os.environ["AICORE_RESOURCE_GROUP"] = resource_group

    client_id = dest.properties.get("clientId", "")
    client_secret = dest.properties.get("clientSecret", "")
    token_service_url = dest.properties.get("tokenServiceURL", "")

    if not client_id or not client_secret:
        raise RuntimeError(
            f"Destination '{name}' did not return clientId/clientSecret. "
            "Ensure the destination uses OAuth2ClientCredentials authentication "
            "and the calling app has the Destination Service technical-user scope."
        )

    os.environ["AICORE_CLIENT_ID"] = client_id
    os.environ["AICORE_CLIENT_SECRET"] = client_secret

    if token_service_url:
        if not token_service_url.endswith("/oauth/token"):
            token_service_url = token_service_url.rstrip("/") + "/oauth/token"
        os.environ["AICORE_AUTH_URL"] = token_service_url

    logger.info("AI Core destination mode active — credentials loaded from '%s'", name)


def _configure_direct_mode(instance_name: str) -> None:
    """Load AI Core credentials directly from mounted secrets or env vars."""
    transparent_tls = _is_transparent_tls()

    client_id = _get_secret("AICORE_CLIENT_ID", "clientid", instance_name=instance_name)
    auth_url = _get_secret("AICORE_AUTH_URL", "url", instance_name=instance_name)
    base_url = _get_aicore_base_url(instance_name)
    resource_group = _get_secret(
        "AICORE_RESOURCE_GROUP", default="default", instance_name=instance_name
    )

    if auth_url and not auth_url.endswith("/oauth/token"):
        auth_url = auth_url.rstrip("/") + "/oauth/token"

    if base_url and not base_url.endswith("/v2"):
        base_url = base_url.rstrip("/") + "/v2"

    if client_id:
        os.environ["AICORE_CLIENT_ID"] = client_id
    if auth_url:
        os.environ["AICORE_AUTH_URL"] = auth_url
    if base_url:
        os.environ["AICORE_BASE_URL"] = base_url
    if resource_group:
        os.environ["AICORE_RESOURCE_GROUP"] = resource_group

    if transparent_tls:
        os.environ.pop("AICORE_CLIENT_SECRET", None)
        logger.info("AI Core transparent TLS mode active — client_secret not required")
    else:
        client_secret = _get_secret(
            "AICORE_CLIENT_SECRET", "clientsecret", instance_name=instance_name
        )
        if client_secret:
            os.environ["AICORE_CLIENT_SECRET"] = client_secret

    logger.info("AI Core configuration has been set successfully")


def _get_secret_dir_mtime(instance_name: str = "aicore-instance") -> float:
    """Return the mtime of the AI Core secret directory, or 0.0 if it does not exist."""
    secret_dir = os.path.join(resolve_base_mount(), "aicore", instance_name)
    try:
        return os.stat(secret_dir).st_mtime
    except OSError:
        return 0.0


@record_metrics(Module.AICORE, Operation.AICORE_PROACTIVE_RELOAD)
def _reload_proactive(instance_name: str = "aicore-instance") -> None:
    set_aicore_config(instance_name=instance_name)


@record_metrics(Module.AICORE, Operation.AICORE_REACTIVE_RELOAD)
def _reload_reactive() -> None:
    set_aicore_config()


def watch_aicore_config(
    instance_name: str = "aicore-instance",
    interval: float = 60.0,
    stop_event: threading.Event | None = None,
) -> threading.Thread:
    """Start a daemon thread that proactively reloads AI Core credentials
    when the mounted secret volume changes.

    Polls the secret directory mtime every ``interval`` seconds. On change,
    calls :func:`set_aicore_config` before LiteLLM's cached OAuth token
    expires — avoiding 401 errors entirely rather than recovering from them.

    Kubernetes projected volumes perform an atomic symlink swap on rotation,
    which changes the directory mtime. Both ``secret`` and ``projected``
    volume types are covered.

    Returns the daemon thread. Stop it cleanly via ``stop_event.set()``.

    Each call starts a new daemon thread — avoid calling more than once per process.

    Typical usage::

        import threading
        from sap_cloud_sdk.aicore import set_aicore_config, watch_aicore_config

        set_aicore_config()

        _stop = threading.Event()
        watch_aicore_config(stop_event=_stop)
        # at shutdown: _stop.set()
    """
    if stop_event is None:
        stop_event = threading.Event()

    last_mtime = _get_secret_dir_mtime(instance_name)

    def _watch() -> None:
        nonlocal last_mtime
        while not stop_event.wait(timeout=interval):
            try:
                current_mtime = _get_secret_dir_mtime(instance_name)
                if current_mtime != last_mtime:
                    logger.info(
                        "AI Core secret volume changed — proactively reloading credentials"
                    )
                    _reload_proactive(instance_name=instance_name)
                    last_mtime = current_mtime
            except Exception:
                logger.exception("Error during proactive AI Core credential reload")

    thread = threading.Thread(target=_watch, daemon=True, name="aicore-secret-watcher")
    thread.start()
    return thread


@record_metrics(Module.AICORE, Operation.AICORE_PATCH_LITELLM)
def patch_litellm_for_credential_rotation() -> None:
    """Patch ``litellm.completion`` / ``litellm.acompletion`` globally so ALL callers
    get transparent credential reload on ``AuthenticationError``.

    LangGraph agents typically call ``litellm.completion`` through ``ChatLiteLLM``
    (LangChain), bypassing the SDK's own ``completion()`` wrapper and its built-in
    401-reload handler. Call this function once at agent startup to extend the same
    reactive reload behaviour to **every** litellm caller in the process.

    Idempotent — calling more than once has no additional effect.

    Recommended startup pattern for LangGraph / ChatLiteLLM agents::

        from sap_cloud_sdk.aicore import (
            set_aicore_config,
            patch_litellm_for_credential_rotation,
            watch_aicore_config,
        )

        set_aicore_config()                       # load credentials
        patch_litellm_for_credential_rotation()   # reactive reload for ChatLiteLLM
        watch_aicore_config()                     # proactive reload on secret rotation

    Agents that already use the SDK's ``completion()`` / ``acompletion()`` wrappers
    do not need this — those wrappers already handle 401s transparently.
    """
    import litellm as _litellm

    if getattr(_litellm, "_sap_aicore_patched", False):
        return

    _orig_completion = _litellm.completion
    _orig_acompletion = _litellm.acompletion

    def _completion(*args, **kwargs):
        try:
            return _orig_completion(*args, **kwargs)
        except _litellm.AuthenticationError:
            _reload_reactive()
            return _orig_completion(*args, **kwargs)

    async def _acompletion(*args, **kwargs):
        try:
            return await _orig_acompletion(*args, **kwargs)
        except _litellm.AuthenticationError:
            _reload_reactive()
            return await _orig_acompletion(*args, **kwargs)

    _litellm.completion = _completion
    _litellm.acompletion = _acompletion
    _litellm._sap_aicore_patched = True
    logger.info(
        "litellm patched for AI Core credential rotation — applies to all callers"
    )


__all__ = [
    "set_aicore_config",
    "watch_aicore_config",
    "patch_litellm_for_credential_rotation",
    "set_filtering",
    "disable_filtering",
    "completion",
    "acompletion",
    "ContentFiltering",
    "InputFiltering",
    "OutputFiltering",
    "AzureContentFilter",
    "LlamaGuard38bFilter",
    "ContentFilter",
    "Severity",
    "ContentFilteredError",
    "OrchestrationError",
]
