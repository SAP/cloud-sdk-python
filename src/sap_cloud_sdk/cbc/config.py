"""Configuration object for the CBC (Central Business Configuration) module."""

from __future__ import annotations

import ssl
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CBCConfig:
    """Overrides for :func:`~sap_cloud_sdk.cbc.client.create_client`.

    Every field is optional. Left unset, :func:`create_client` infers the value
    from the SAP application-platform provisioning conventions (runtime context,
    tenant-mapping Fragment, Destination Service certificate). A value set here
    wins over its ``CLOUD_SDK_CBC_*`` env var, which in turn falls back to the
    platform default.

    The first three fields replace a whole default resolver; the last three steer
    the default certificate / fragment lookup.

    Attributes:
        base_url: CBC service base URL, as a string or a per-request callable.
            Overrides the tenant-mapping Fragment lookup.
        app_tenant_id: Application tenant id, as a string or a per-request
            callable. Overrides reading ``APP_TENANT_ID`` from the runtime context.
        ssl_context: Callable returning a freshly-built :class:`ssl.SSLContext`
            with mTLS loaded. Overrides loading the certificate from the
            Destination Service. ``None`` falls back to the default loader; use
            this to inject a pre-built context (startup injection or tests), or a
            plain-HTTP / local-mock path by returning an unauthenticated context.
        destination_instance: The ``instance`` passed to the destination
            ``create_fragment_client`` / ``create_certificate_client`` (used for
            secret resolution in cloud mode). Falls back to the
            ``CLOUD_SDK_CBC_DESTINATION_INSTANCE`` env var, else ``"default"``.
        cbc_cert_name: Name of the app's mTLS certificate. Falls back to the
            ``CLOUD_SDK_CBC_CERTIFICATE_NAME`` env var, else derived from the
            platform landscape (``APPFND_CONHOS_LANDSCAPE``).
        p12_password: Certificate keystore password. Falls back to the
            ``CLOUD_SDK_CBC_P12_PASSWORD`` env var, else ``None``.
    """

    base_url: str | Callable[[], str] | None = None
    app_tenant_id: str | Callable[[], str] | None = None
    ssl_context: Callable[[], ssl.SSLContext] | None = None
    destination_instance: str | None = None
    cbc_cert_name: str | None = None
    p12_password: bytes | None = None
