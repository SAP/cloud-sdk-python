"""HTTP client for calling the target system described by a Destination."""

from __future__ import annotations

import ssl
from typing import Any, Dict, Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter

from sap_cloud_sdk.destination._cert_loader import build_client_cert_context
from sap_cloud_sdk.destination._models import Destination, DestinationType


class _ClientCertAdapter(HTTPAdapter):
    """requests HTTPAdapter that injects a stdlib SSLContext for mTLS."""

    def __init__(self, ssl_ctx: ssl.SSLContext, **kwargs: Any) -> None:
        self._ssl_ctx = ssl_ctx
        super().__init__(**kwargs)

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs["ssl_context"] = self._ssl_ctx
        super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["ssl_context"] = self._ssl_ctx
        return super().proxy_manager_for(*args, **kwargs)


class DestinationHttpClient:
    """Wraps requests.Session to call the target system described by a Destination.

    Pre-bakes headers derived from the destination — ERP headers (sap-client,
    sap-language), URL.headers.* properties, and auth tokens. Certificates from the
    destination's certificate list are mounted into the session.

    Use as a context manager to ensure the underlying session is closed:

        with DestinationHttpClient(dest) as http:
            response = http.request("GET", "/api/resource")
    """

    def __init__(self, destination: Destination) -> None:
        if destination.type != DestinationType.HTTP:
            raise ValueError(
                f"DestinationHttpClient only supports HTTP destinations, got: {destination.type}"
            )

        self._session = requests.Session()
        self._session.headers.update(destination.get_headers())
        self._base_url = destination.url.rstrip("/") if destination.url else ""

        ssl_ctx = build_client_cert_context(destination)
        if ssl_ctx is not None:
            self._session.mount("https://", _ClientCertAdapter(ssl_ctx))

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

    def __enter__(self) -> "DestinationHttpClient":
        return self

    def __exit__(self, *exc: Any) -> bool:
        self._session.close()
        return False
