"""mTLS (X.509 client certificate) authentication strategy for BTP services.

BTP Business Services that use the ``accessStrategy: sap:cmp-mtls:v1`` trust
model (SPII, Destination service, UCL callbacks) require the **calling
application to present a client certificate** signed by the SAP Cloud Root CA.

This module provides :class:`MTLSStrategy` — a single object that wraps a
PEM-encoded client certificate + private key and applies it to either a
``requests.Session`` (sync) or an ``httpx.AsyncClient`` (async).

Service binding layout (Kyma / Cloud Foundry):
    The client cert and key are typically delivered as files in the service
    binding's mounted secret directory.  The exact key names vary by service:

    * Destination service (CF):     ``clientid``, ``certificate``, ``key``
    * SPII / UCL mTLS endpoint:     ``tls.crt``, ``tls.key``
    * SAP Connectivity service:      ``onpremise_proxy_certificate``, ``onpremise_proxy_key``

    :meth:`MTLSStrategy.from_binding_path` handles the common ``certificate``/``key``
    naming used by the CF Destination service.  For custom naming, use
    :meth:`MTLSStrategy.from_pem` directly.

Usage::

    from sap_cloud_sdk.core.auth import MTLSStrategy

    # Load from Kubernetes / CF mounted secret directory
    strategy = MTLSStrategy.from_binding_path("/etc/secrets/appfnd/destination/default")

    # Apply to a sync requests.Session
    import requests
    session = strategy.apply_to_session(requests.Session())
    resp = session.get("https://destination-configuration.cfapps.eu20.hana.ondemand.com/...")

    # Apply to an async httpx.AsyncClient
    import httpx
    async with strategy.apply_to_async_client() as client:
        resp = await client.get("...")

    # Or load directly from PEM strings / file paths
    strategy = MTLSStrategy.from_pem(cert_pem="-----BEGIN CERTIFICATE...", key_pem="...")
    strategy = MTLSStrategy.from_files(cert_path="/var/certs/tls.crt", key_path="/var/certs/tls.key")
"""

from __future__ import annotations

import os
import ssl
import tempfile
from dataclasses import dataclass
from typing import Optional

import httpx
import requests


@dataclass(frozen=True)
class MTLSConfig:
    """Immutable holder for a client certificate + private key pair.

    Attributes:
        cert_pem: PEM-encoded client certificate (``-----BEGIN CERTIFICATE-----...``).
        key_pem:  PEM-encoded private key (``-----BEGIN PRIVATE KEY-----...`` or
                  ``-----BEGIN RSA PRIVATE KEY-----...``).
        server_ca_pem: Optional PEM-encoded CA bundle to pin the server's CA.
                       When ``None``, the system default CA store is used.
    """

    cert_pem: str
    key_pem: str
    server_ca_pem: Optional[str] = None


class MTLSStrategy:
    """Applies X.509 client certificate authentication to HTTP clients.

    Construct via one of the factory class methods:

    * :meth:`from_pem` — from PEM strings already in memory.
    * :meth:`from_files` — from cert/key file paths on disk.
    * :meth:`from_binding_path` — from a SAP BTP service binding directory.
    * :meth:`from_env` — from environment variable names that contain paths.

    Then call :meth:`apply_to_session` or :meth:`apply_to_async_client` to
    create an HTTP client pre-configured with the certificate.
    """

    def __init__(self, config: MTLSConfig) -> None:
        self._config = config
        self._session_temp_files: list[str] = []

    def __del__(self) -> None:
        """Delete any temp files written for requests.Session cert paths."""
        for path in self._session_temp_files:
            try:
                os.unlink(path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_pem(
        cls,
        cert_pem: str,
        key_pem: str,
        server_ca_pem: Optional[str] = None,
    ) -> "MTLSStrategy":
        """Create from PEM-encoded certificate and key strings.

        Args:
            cert_pem: PEM-encoded client certificate.
            key_pem: PEM-encoded private key.
            server_ca_pem: Optional PEM CA bundle to pin the server certificate.
        """
        return cls(
            MTLSConfig(cert_pem=cert_pem, key_pem=key_pem, server_ca_pem=server_ca_pem)
        )

    @classmethod
    def from_files(
        cls,
        cert_path: str,
        key_path: str,
        server_ca_path: Optional[str] = None,
    ) -> "MTLSStrategy":
        """Create from certificate and key file paths.

        Args:
            cert_path: Path to the PEM-encoded client certificate file.
            key_path:  Path to the PEM-encoded private key file.
            server_ca_path: Optional path to the server CA bundle PEM file.
        """
        cert_pem = _read_file(cert_path, "certificate")
        key_pem = _read_file(key_path, "private key")
        server_ca_pem = (
            _read_file(server_ca_path, "server CA") if server_ca_path else None
        )
        return cls(
            MTLSConfig(cert_pem=cert_pem, key_pem=key_pem, server_ca_pem=server_ca_pem)
        )

    @classmethod
    def from_binding_path(
        cls,
        binding_dir: str,
        cert_key: str = "certificate",
        key_key: str = "key",
        server_ca_key: Optional[str] = None,
    ) -> "MTLSStrategy":
        """Create from a SAP BTP service binding directory.

        Reads files named *cert_key* and *key_key* from *binding_dir*.

        Default key names match the CF Destination service binding layout
        (``certificate`` and ``key``).  Override for other services, e.g.::

            # Kubernetes TLS secret layout
            strategy = MTLSStrategy.from_binding_path(
                "/var/bindings/compass-mtls",
                cert_key="tls.crt",
                key_key="tls.key",
            )

        Args:
            binding_dir: Path to the service binding directory.
            cert_key: File name of the certificate inside *binding_dir*.
            key_key: File name of the private key inside *binding_dir*.
            server_ca_key: Optional file name for a custom server CA bundle.
        """
        cert_pem = _read_file(os.path.join(binding_dir, cert_key), "certificate")
        key_pem = _read_file(os.path.join(binding_dir, key_key), "private key")
        server_ca_pem: Optional[str] = None
        if server_ca_key:
            server_ca_pem = _read_file(
                os.path.join(binding_dir, server_ca_key), "server CA"
            )
        return cls(
            MTLSConfig(cert_pem=cert_pem, key_pem=key_pem, server_ca_pem=server_ca_pem)
        )

    @classmethod
    def from_env(
        cls,
        cert_env: str,
        key_env: str,
        server_ca_env: Optional[str] = None,
    ) -> "MTLSStrategy":
        """Create using environment variable names that hold file paths.

        Useful when the cert/key paths are injected via env vars (e.g. in
        Docker Compose or local development setups).

        Args:
            cert_env: Name of the env var holding the certificate file path.
            key_env:  Name of the env var holding the private key file path.
            server_ca_env: Optional env var name for the server CA bundle path.

        Raises:
            ValueError: If a required environment variable is not set.
        """
        cert_path = _require_env(cert_env)
        key_path = _require_env(key_env)
        server_ca_path = os.environ.get(server_ca_env) if server_ca_env else None
        return cls.from_files(cert_path, key_path, server_ca_path or None)

    # ------------------------------------------------------------------
    # Apply to HTTP clients
    # ------------------------------------------------------------------

    def apply_to_session(
        self, session: Optional[requests.Session] = None
    ) -> requests.Session:
        """Return a ``requests.Session`` configured with this client certificate.

        The session performs mTLS on every request.

        Args:
            session: An existing session to configure (mutated in-place).
                     A new session is created when omitted.

        Returns:
            The configured session.
        """
        if session is None:
            session = requests.Session()

        # ``requests`` needs cert/key as file paths or a (cert_path, key_path) tuple.
        # Write PEMs to temp files tracked on the instance so __del__ can clean them up.
        cert_path = self._write_temp_tracked(self._config.cert_pem, "cert")
        key_path = self._write_temp_tracked(self._config.key_pem, "key")
        session.cert = (cert_path, key_path)

        if self._config.server_ca_pem:
            ca_path = self._write_temp_tracked(self._config.server_ca_pem, "ca")
            session.verify = ca_path

        return session

    def apply_to_async_client(self) -> httpx.AsyncClient:
        """Return an ``httpx.AsyncClient`` configured with this client certificate.

        ``httpx`` does not support mutating an existing client's SSL context, so
        a new client is always constructed with a fresh ``ssl.SSLContext``.

        Returns:
            A new ``httpx.AsyncClient`` with mTLS configured.
        """
        ssl_ctx = self._build_ssl_context()
        return httpx.AsyncClient(verify=ssl_ctx, timeout=30.0)

    def build_ssl_context(self) -> ssl.SSLContext:
        """Return a ready-to-use :class:`ssl.SSLContext` with the client cert loaded.

        Useful when you need to configure a custom HTTP framework directly.
        """
        return self._build_ssl_context()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_ssl_context(self) -> ssl.SSLContext:
        """Build an SSL context, writing PEM material to temp files that are
        deleted immediately after being loaded into the context."""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if self._config.server_ca_pem:
            ca_path = _write_temp(self._config.server_ca_pem, "ca")
            try:
                ctx.load_verify_locations(ca_path)
            finally:
                os.unlink(ca_path)
        else:
            ctx.load_default_certs()

        cert_path = _write_temp(self._config.cert_pem, "cert")
        key_path = _write_temp(self._config.key_pem, "key")
        try:
            ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)
        return ctx

    def _write_temp_tracked(self, content: str, suffix: str) -> str:
        """Write *content* to a temp file, track the path for later cleanup."""
        path = _write_temp(content, suffix)
        self._session_temp_files.append(path)
        return path


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _write_temp(content: str, suffix: str) -> str:
    """Write *content* to a named temp file and return the path.

    The file is created with mode 0o600 (owner read/write only) to
    protect private key material.  Callers are responsible for deleting
    the file when it is no longer needed.
    """
    fd, path = tempfile.mkstemp(suffix=f"_{suffix}.pem")
    os.close(fd)
    os.chmod(path, 0o600)
    with open(path, "w") as f:
        f.write(content)
    return path


def _read_file(path: str, label: str) -> str:
    """Read a text file, raising a descriptive error if it is missing."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"MTLSStrategy: {label} file not found at '{path}'"
        ) from exc
    except OSError as exc:
        raise OSError(
            f"MTLSStrategy: cannot read {label} file at '{path}': {exc}"
        ) from exc


def _require_env(name: str) -> str:
    """Return the value of env var *name* or raise :exc:`ValueError`."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(
            f"MTLSStrategy: required environment variable '{name}' is not set"
        )
    return value
