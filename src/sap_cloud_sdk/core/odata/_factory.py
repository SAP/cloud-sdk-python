"""Factory for building OData transports from BTP Destinations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from sap_cloud_sdk.core.odata._transport import ODataHttpTransport

if TYPE_CHECKING:
    from sap_cloud_sdk.destination._models import Destination


def odata_transport_from_destination(
    destination: "Destination",
    *,
    odata_path: str = "",
    csrf_enabled: bool = True,
) -> ODataHttpTransport:
    """Build an :class:`ODataHttpTransport` from a resolved BTP Destination.

    The destination's auth tokens and ERP headers are pre-baked into the
    underlying ``requests.Session`` exactly as ``http_client_for_destination`` does,
    so the transport inherits whatever authentication the destination carries
    (Bearer, Basic, mTLS, …).

    Args:
        destination: A fully-resolved ``Destination`` object (i.e. returned by
            ``DestinationClient.get_destination()`` so ``auth_tokens`` are
            populated).
        odata_path: Optional sub-path appended to the destination URL to form
            the OData service root (e.g. ``"sap/opu/odata4/svc/"``).  Useful
            when the destination URL points to the host root rather than the
            service root directly.
        csrf_enabled: Whether to fetch and attach CSRF tokens on mutating
            requests.  Defaults to ``True``.

    Returns:
        :class:`ODataHttpTransport` ready to pass into any request builder.

    Raises:
        ValueError: If the destination has no URL or is not an HTTP destination.

    Example::

        from sap_cloud_sdk.destination import create_client
        from sap_cloud_sdk.core.odata._factory import odata_transport_from_destination
        from sap_cloud_sdk.core.odata._request_builders import GetAllRequestBuilder

        dest_client = create_client()
        destination = dest_client.get_destination("S4HANA_OData")

        transport = odata_transport_from_destination(destination)
        results = GetAllRequestBuilder(transport, BusinessPartner).top(10).execute()
    """
    from sap_cloud_sdk.destination._models import DestinationType

    if destination.type != DestinationType.HTTP:
        raise ValueError(
            f"odata_transport_from_destination only supports HTTP destinations, "
            f"got: {destination.type}"
        )
    if not destination.url:
        raise ValueError(
            f"Destination '{destination.name}' has no URL — cannot build OData transport"
        )

    base_url = destination.url.rstrip("/")
    if odata_path:
        base_url = base_url + "/" + odata_path.strip("/")

    session = requests.Session()
    session.headers.update(destination.get_headers())

    return ODataHttpTransport(
        base_url=base_url,
        session=session,
        csrf_enabled=csrf_enabled,
    )
