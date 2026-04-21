"""Configuration resolution for the SAP Cloud SDK Temporal module.

Socket discovery order:
    1. ``WORKLOAD_API_SOCKET`` env var (plain path)
    2. ``SPIFFE_ENDPOINT_SOCKET`` env var (``unix://`` prefixed or plain path)
    3. ``/spiffe-workload-api/spire-agent.sock``  (Kyma / Kubernetes default)
    4. ``/tmp/spire-agent/public/api.sock``  (Cloud Foundry default)

Local-dev mode is activated when ``APPFND_LOCALDEV_TEMPORAL=true``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

_K8S_SOCKET = "/spiffe-workload-api/spire-agent.sock"
_CF_SOCKET = "/tmp/spire-agent/public/api.sock"

_ENV_WORKLOAD_API_SOCKET = "WORKLOAD_API_SOCKET"
_ENV_SPIFFE_ENDPOINT_SOCKET = "SPIFFE_ENDPOINT_SOCKET"
_ENV_TEMPORAL_CALL_URL = "TEMPORAL_CALL_URL"
_ENV_TEMPORAL_NAMESPACE = "TEMPORAL_NAMESPACE"
_ENV_LOCALDEV = "APPFND_LOCALDEV_TEMPORAL"

_LOCALDEV_TARGET = "localhost:7233"
_LOCALDEV_NAMESPACE = "default"


@dataclass(frozen=True)
class TemporalConfig:
    """Resolved configuration for connecting to SAP Managed Temporal.

    Attributes:
        target: The ``host:port`` address of the Temporal frontend service.
        namespace: The Temporal namespace to operate in.
        is_local_dev: When ``True`` the connection uses plain-text (no TLS).
        spiffe_socket_path: Absolute path to the SPIFFE Workload API socket.
            ``None`` in local-dev mode.
    """

    target: str
    namespace: str
    is_local_dev: bool = False
    spiffe_socket_path: str | None = None


def _strip_unix_prefix(value: str) -> str:
    if value.startswith("unix://"):
        return value[len("unix://"):]
    return value


def _discover_spiffe_socket() -> str | None:
    env_workload = os.environ.get(_ENV_WORKLOAD_API_SOCKET)
    if env_workload:
        path = env_workload if env_workload.startswith("/") else "/" + env_workload
        logger.debug("Using SPIFFE socket from %s: %s", _ENV_WORKLOAD_API_SOCKET, path)
        return path

    env_spiffe = os.environ.get(_ENV_SPIFFE_ENDPOINT_SOCKET)
    if env_spiffe:
        path = _strip_unix_prefix(env_spiffe)
        logger.debug("Using SPIFFE socket from %s: %s", _ENV_SPIFFE_ENDPOINT_SOCKET, path)
        return path

    if Path(_K8S_SOCKET).exists():
        logger.debug("Discovered Kyma SPIFFE socket at %s", _K8S_SOCKET)
        return _K8S_SOCKET

    if Path(_CF_SOCKET).exists():
        logger.debug("Discovered CF SPIFFE socket at %s", _CF_SOCKET)
        return _CF_SOCKET

    return None


def resolve_config(
    *,
    target: str | None = None,
    namespace: str | None = None,
) -> TemporalConfig:
    """Build a :class:`TemporalConfig` from the environment.

    Explicit *target* and *namespace* take precedence over environment variables.
    In local-dev mode (``APPFND_LOCALDEV_TEMPORAL=true``) connects to
    ``localhost:7233`` without TLS or SPIFFE credentials.

    Raises:
        ConfigurationError: When required values are missing.
    """
    local_dev = os.environ.get(_ENV_LOCALDEV, "").strip().lower() == "true"

    if local_dev:
        resolved_target = target or os.environ.get(_ENV_TEMPORAL_CALL_URL) or _LOCALDEV_TARGET
        resolved_ns = namespace or os.environ.get(_ENV_TEMPORAL_NAMESPACE) or _LOCALDEV_NAMESPACE
        logger.info("Local-dev mode  target=%s  namespace=%s", resolved_target, resolved_ns)
        return TemporalConfig(
            target=resolved_target,
            namespace=resolved_ns,
            is_local_dev=True,
            spiffe_socket_path=None,
        )

    resolved_target = target or os.environ.get(_ENV_TEMPORAL_CALL_URL)
    if not resolved_target:
        raise ConfigurationError(
            f"Temporal target address not configured. "
            f"Set {_ENV_TEMPORAL_CALL_URL} or pass 'target' explicitly. "
            f"For local development set {_ENV_LOCALDEV}=true."
        )

    resolved_ns = namespace or os.environ.get(_ENV_TEMPORAL_NAMESPACE)
    if not resolved_ns:
        raise ConfigurationError(
            f"Temporal namespace not configured. "
            f"Set {_ENV_TEMPORAL_NAMESPACE} or pass 'namespace' explicitly."
        )

    socket_path = _discover_spiffe_socket()
    if socket_path is None:
        raise ConfigurationError(
            "No SPIFFE Workload API socket found. "
            f"Set {_ENV_WORKLOAD_API_SOCKET} or {_ENV_SPIFFE_ENDPOINT_SOCKET}, "
            "or ensure the SPIRE agent socket is mounted at a well-known location."
        )

    logger.info(
        "Resolved config  target=%s  namespace=%s  socket=%s",
        resolved_target,
        resolved_ns,
        socket_path,
    )
    return TemporalConfig(
        target=resolved_target,
        namespace=resolved_ns,
        is_local_dev=False,
        spiffe_socket_path=socket_path,
    )
