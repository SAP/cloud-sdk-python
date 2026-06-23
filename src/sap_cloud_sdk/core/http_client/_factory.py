"""Factory for building HttpClient from BTP Destinations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from sap_cloud_sdk.core.http_client._client import HttpClient

if TYPE_CHECKING:
    from sap_cloud_sdk.destination._models import Destination


def http_client_for_destination(
    destination: "Destination",
    *,
    sub_path: str = "",
) -> HttpClient:
    """Build an :class:`HttpClient` from a resolved BTP Destination.

    The destination's auth tokens and ERP headers are pre-baked into the
    underlying ``requests.Session``, so no manual header management is needed.
    Mirrors the pattern of
    :func:`~sap_cloud_sdk.core.odata._factory.odata_transport_from_destination`.

    Args:
        destination: A fully-resolved ``Destination`` object (i.e. returned by
            ``DestinationClient.get_destination()`` so ``auth_tokens`` are
            populated).
        sub_path: Optional sub-path appended to the destination URL to form
            the service root (e.g. ``"api/v1"``).  Useful when the destination
            URL points to the host root rather than the service root directly.

    Returns:
        :class:`HttpClient` ready to call the target system.

    Raises:
        ValueError: If the destination is not an HTTP destination or has no URL.

    Example::

        from sap_cloud_sdk.destination import create_client
        from sap_cloud_sdk.core.http_client import http_client_for_destination

        dest = create_client().get_destination("MY_API")
        client = http_client_for_destination(dest, sub_path="api/v1")
        response = client.get("/resources")
    """
    from sap_cloud_sdk.destination._models import DestinationType

    if destination.type != DestinationType.HTTP:
        raise ValueError(
            f"http_client_for_destination only supports HTTP destinations, "
            f"got: {destination.type}"
        )
    if not destination.url:
        raise ValueError(
            f"Destination '{destination.name}' has no URL — cannot build HTTP client"
        )

    base_url = destination.url.rstrip("/")
    if sub_path:
        base_url = base_url + "/" + sub_path.strip("/")

    session = requests.Session()
    session.headers.update(destination.get_headers())

    return HttpClient(base_url=base_url, session=session)
