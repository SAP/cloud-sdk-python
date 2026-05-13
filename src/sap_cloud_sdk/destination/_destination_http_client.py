"""HTTP client for calling the target system described by a Destination."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests
from requests import Response

from sap_cloud_sdk.destination._models import Destination, DestinationType


class DestinationHttpClient:
    """Wraps requests.Session to call the target system described by a Destination.

    Pre-bakes SAP ERP headers (sap-client, sap-language) and auth headers from
    the destination so callers never have to set them manually.

    Usage::

        dest = client.get_destination("my-erp")
        http = DestinationHttpClient(dest)
        response = http.get("/sap/opu/odata/sap/API_BUSINESS_PARTNER")
    """

    def __init__(self, destination: Destination) -> None:
        if destination.type not in (DestinationType.HTTP, "HTTP"):
            raise ValueError(
                f"DestinationHttpClient only supports HTTP destinations, got: {destination.type}"
            )

        self._destination = destination
        self._session = requests.Session()

        # Pre-bake sap-client / sap-language — relevant mainly for OnPremise destinations
        self._session.headers.update(destination.get_erp_headers())

        # Pre-bake auth headers — BTP may return multiple tokens, skip empty ones
        for token in destination.auth_tokens:
            key = token.http_header.get("key")
            value = token.http_header.get("value")
            if key and value:
                self._session.headers[key] = value

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

    def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        return self.request("GET", path, params=params, headers=headers, **kwargs)

    def post(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        return self.request("POST", path, json=json, headers=headers, **kwargs)

    def put(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        return self.request("PUT", path, json=json, headers=headers, **kwargs)

    def patch(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        return self.request("PATCH", path, json=json, headers=headers, **kwargs)

    def delete(
        self,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        return self.request("DELETE", path, headers=headers, **kwargs)
