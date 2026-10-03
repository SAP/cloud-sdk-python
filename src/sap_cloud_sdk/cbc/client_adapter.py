"""Platform adapter for the CBC (Central Business Configuration) module.

This is a thin convenience layer over the generic client in
:mod:`sap_cloud_sdk.cbc.client`. It encodes the SAP application-platform
provisioning convention, where the pieces a CBC call needs are standard:

- the app's own provider-level **Destination**, holding the mTLS certificate;
- the tenant-mapping **Fragment**, carrying the CBC URL (written by the
  platform during tenant provisioning).

The adapter adds **no** capability to the core client — it only supplies the
``base_url`` / ``app_tenant_id`` resolvers and the mTLS ``ssl.SSLContext`` from
those conventions, then delegates to
:func:`~sap_cloud_sdk.cbc.client.create_client`. Agents are the typical
consumer, but any app that follows the same provisioning convention can use it.
Every default is overridable.

Two ContextVars are **defined here and owned by the SDK**; the app populates
them — e.g. from the IAS JWT ``app_tid`` claim and the ``dwc-subdomain``
header, though the SDK does not mandate the source. The SDK deliberately does
not know *how* those values are obtained — authentication and the request
pipeline stay with the app.

The mTLS certificate is loaded **once** when the client is built. Platform
certificates are typically short-lived, so recreate the client before the
certificate expires to pick up the rotated certificate.

Quick start::

    from sap_cloud_sdk import cbc

    cbc_client = cbc.create_agent_client()   # once, at startup

    # per request:
    cbc.app_tenant_id_var.set(parse_token(bearer).app_tid)
    cbc.tenant_subdomain_var.set(request.headers["dwc-subdomain"])
"""

from __future__ import annotations

import os
import ssl
from contextvars import ContextVar

from sap_cloud_sdk.cbc.client import CBCClient, create_client
from sap_cloud_sdk.cbc.exceptions import CBCConfigError

# ---------------------------------------------------------------------------
# SDK-owned context
# ---------------------------------------------------------------------------

#: Application tenant id for the current context (typically the IAS ``app_tid``
#: claim, but the SDK does not mandate the source).
app_tenant_id_var: ContextVar[str] = ContextVar("cbc_app_tenant_id", default="")

#: Tenant subdomain for the current context (typically the ``dwc-subdomain``
#: header, but the SDK does not mandate the source).
tenant_subdomain_var: ContextVar[str] = ContextVar("cbc_tenant_subdomain", default="")

# ---------------------------------------------------------------------------
# Platform conventions
# ---------------------------------------------------------------------------
# The fragment name and certificate name below follow the application-platform
# convention; they are not arbitrary. Override via the args / env vars if your
# setup differs.

#: Prefix of the Destination Fragment that maps a subdomain to its CBC tenant
#: (platform convention).
CBC_FRAGMENT_PREFIX = "CBC_TenantMapping_"

#: Template for the app's own provider-level mTLS certificate name
#: (platform convention).
_CERT_NAME_TEMPLATE = "sap-managed-runtime-ias-{landscape}.pem"

# Env overrides — the defaults cover the common case; set these only to override.

#: The ``instance`` passed to the destination ``create_fragment_client`` /
#: ``create_certificate_client`` (used for secret resolution in cloud mode,
#: defaults to "default"); it is not the individual destination / cert /
#: fragment, which are selected by name.
ENV_DESTINATION_INSTANCE = "CLOUD_SDK_CBC_DESTINATION_INSTANCE"

#: Explicit certificate name, overriding the landscape-derived default.
ENV_CERT_NAME = "CLOUD_SDK_CBC_CERTIFICATE_NAME"

#: Password for the certificate keystore, if encrypted (default: none).
ENV_P12_PASSWORD = "CLOUD_SDK_CBC_P12_PASSWORD"

#: Platform landscape, used to derive the default certificate name.
ENV_LANDSCAPE = "APPFND_CONHOS_LANDSCAPE"


def _default_cert_name() -> str:
    """Return the name of the app's provider-level mTLS certificate.

    This is the certificate the app presents to CBC for the mTLS handshake; its
    name follows the platform convention :data:`_CERT_NAME_TEMPLATE`, with the
    landscape filled in from :data:`ENV_LANDSCAPE`.

    Raises:
        CBCConfigError: If :data:`ENV_LANDSCAPE` is not set, so the name cannot
            be derived.
    """
    landscape = os.environ.get(ENV_LANDSCAPE)
    if not landscape:
        raise CBCConfigError(
            f"Cannot derive the CBC certificate name: {ENV_LANDSCAPE} is not set. "
            f"Set it, or pass cbc_cert_name / ssl_context to create_agent_client()."
        )
    return _CERT_NAME_TEMPLATE.format(landscape=landscape)


def _cert_password_from_env() -> bytes | None:
    """Return the cert keystore password from :data:`ENV_P12_PASSWORD`, or ``None``."""
    raw = os.environ.get(ENV_P12_PASSWORD)
    return raw.encode() if raw else None


# ---------------------------------------------------------------------------
# Default resolvers
# ---------------------------------------------------------------------------


def _resolve_app_tenant_id() -> str:
    """Return the application tenant id from :data:`app_tenant_id_var`.

    The application tenant id identifies the subscriber tenant to CBC — e.g. the
    subscriber's subaccount id, carried in the IAS JWT ``app_tid`` claim.

    Raises:
        CBCConfigError: If the ContextVar is empty.
    """
    app_tid = app_tenant_id_var.get()
    if not app_tid:
        raise CBCConfigError(
            "cbc_app_tenant_id ContextVar is empty — set app_tenant_id_var from "
            "the IAS app_tid claim."
        )
    return app_tid


def _resolve_base_url(destination_instance: str) -> str:
    """Return the CBC base URL for the current tenant.

    Reads :data:`tenant_subdomain_var` and :data:`app_tenant_id_var`, lists the
    tenant-mapping Fragments in the subscriber's subaccount, finds the one whose
    ``appTenantId`` property matches, and returns its ``cbcUrl`` verbatim.

    The fragments are named ``CBC_TenantMapping_<cbcTenantId>``, so they cannot be
    fetched directly by subdomain; the subaccount is listed and matched on the
    ``appTenantId`` property instead. (Once the fragment is keyed by subdomain
    upstream, this becomes a single direct ``get_subaccount_fragment`` lookup.)

    Args:
        destination_instance: The ``instance`` passed to the destination
            ``create_fragment_client`` (selects which Destination Service binding
            to read, used for secret resolution in cloud mode).

    Raises:
        CBCConfigError: If either ContextVar is empty, no matching fragment is
            found, or the matched fragment has no ``cbcUrl`` property.
    """
    from sap_cloud_sdk.destination import create_fragment_client

    subdomain = tenant_subdomain_var.get()
    if not subdomain:
        raise CBCConfigError(
            "cbc_tenant_subdomain ContextVar is empty — set tenant_subdomain_var "
            "from the dwc-subdomain header."
        )
    app_tenant_id = _resolve_app_tenant_id()

    client = create_fragment_client(instance=destination_instance)
    fragments = client.list_subaccount_fragments(tenant=subdomain)
    fragment = next(
        (
            f
            for f in fragments
            if f.name.startswith(CBC_FRAGMENT_PREFIX)
            and f.properties.get("appTenantId") == app_tenant_id
        ),
        None,
    )
    if fragment is None:
        raise CBCConfigError(
            f"No CBC mapping fragment for appTenantId={app_tenant_id!r} in "
            f"subdomain={subdomain!r} (looked for {CBC_FRAGMENT_PREFIX}* fragments)."
        )
    cbc_url = fragment.properties.get("cbcUrl")
    if not cbc_url:
        raise CBCConfigError(
            f"CBC mapping fragment {fragment.name!r} has no 'cbcUrl' property."
        )
    return cbc_url  # cbcTid already baked in — used verbatim


def _load_ssl_context(
    destination_instance: str, cert_name: str, p12_password: bytes | None
) -> ssl.SSLContext:
    """Fetch the provider certificate and load it into an :class:`ssl.SSLContext`.

    Args:
        destination_instance: The ``instance`` passed to the destination
            ``create_certificate_client`` (selects which Destination Service
            binding to read, used for secret resolution in cloud mode).
        cert_name: Name of the subaccount certificate to fetch.
        p12_password: Certificate keystore password, or ``None`` if unencrypted.

    Raises:
        CBCConfigError: If the certificate is not found.
    """
    from sap_cloud_sdk.destination import AccessStrategy, create_certificate_client
    from sap_cloud_sdk.destination._cert_loader import _load_pem

    cert = create_certificate_client(
        instance=destination_instance
    ).get_subaccount_certificate(
        cert_name, access_strategy=AccessStrategy.PROVIDER_ONLY
    )
    if cert is None:
        raise CBCConfigError(
            f"Subaccount certificate {cert_name!r} not found in Destination "
            f"Service instance {destination_instance!r}."
        )
    return _load_pem(cert.content, p12_password, cert.name)


# ---------------------------------------------------------------------------
# Platform constructor
# ---------------------------------------------------------------------------


def create_agent_client(
    *,
    ssl_context: ssl.SSLContext | None = None,
    destination_instance: str | None = None,
    cbc_cert_name: str | None = None,
    p12_password: bytes | None = None,
) -> CBCClient:
    """Create a CBC client wired for the application platform.

    Resolves ``base_url`` and ``app_tenant_id`` from the two SDK-owned
    ContextVars (:data:`app_tenant_id_var`, :data:`tenant_subdomain_var`) each
    time a request is made, and loads the mTLS certificate once from the
    Destination Service. Because the certificate is loaded once, recreate the
    client before the certificate expires so it picks up the rotated
    certificate.

    Args:
        ssl_context: Pre-built :class:`ssl.SSLContext`. When given, the
            certificate load is skipped entirely (use for startup injection or
            tests).
        destination_instance: The ``instance`` passed to the destination
            ``create_fragment_client`` / ``create_certificate_client`` (used for
            secret resolution in cloud mode). Defaults to the
            ``CLOUD_SDK_CBC_DESTINATION_INSTANCE`` env var, else ``"default"``.
        cbc_cert_name: Name of the app's mTLS certificate. Defaults to the
            ``CLOUD_SDK_CBC_CERTIFICATE_NAME`` env var, else derived from the
            platform landscape (``APPFND_CONHOS_LANDSCAPE``).
        p12_password: Certificate keystore password. Defaults to the
            ``CLOUD_SDK_CBC_P12_PASSWORD`` env var, else ``None``.

    Returns:
        A configured CBC client.

    Raises:
        CBCConfigError: If the certificate cannot be resolved at construction
            time (unless ``ssl_context`` is supplied), or — when a request is
            made — if a ContextVar is empty or the tenant-mapping fragment is
            missing.
    """
    if destination_instance is None:
        destination_instance = os.environ.get(ENV_DESTINATION_INSTANCE, "default")

    if ssl_context is None:
        resolved_cert_name = (
            cbc_cert_name or os.environ.get(ENV_CERT_NAME) or _default_cert_name()
        )
        resolved_password = (
            p12_password if p12_password is not None else _cert_password_from_env()
        )
        ssl_context = _load_ssl_context(
            destination_instance, resolved_cert_name, resolved_password
        )

    return create_client(
        base_url=lambda: _resolve_base_url(destination_instance),
        app_tenant_id=_resolve_app_tenant_id,
        ssl_context=ssl_context,
    )
