"""HTTP client for calling the target system described by a Destination."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests
from requests import Response

from sap_cloud_sdk.destination._models import Destination, DestinationType


class DestinationHttpClient:
    """Wraps requests.Session to call the target system described by a Destination.

    Pre-bakes headers derived from the destination — ERP headers (sap-client,
    sap-language), URL.headers.* properties, and auth tokens.

    Usage::

        dest = client.get_destination("my-erp")
        http = DestinationHttpClient(dest)
        response = http.request("GET", "/api/resource")
    """

    def __init__(self, destination: Destination) -> None:
        if destination.type not in (DestinationType.HTTP, "HTTP"):
            raise ValueError(
                f"DestinationHttpClient only supports HTTP destinations, got: {destination.type}"
            )

        self._destination = destination
        self._session = requests.Session()
        self._session.headers.update(destination.get_headers())
        self._base_url = destination.url.rstrip("/") if destination.url else ""

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Send an HTTP request to the target system.

        Args:
            method: HTTP verb (GET, POST, PUT, PATCH, DELETE).
            path: Path relative to the destination URL.
            params: Optional query parameters.
            json: Optional JSON body.
            headers: Optional additional headers merged on top of pre-baked ones.
            **kwargs: Passed through to requests.Session.request.

        Returns:
            requests.Response from the target system.
        """
        url = f"{self._base_url}/{path.lstrip('/')}" if path else self._base_url
        return self._session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            headers=headers,
            **kwargs,
        )

