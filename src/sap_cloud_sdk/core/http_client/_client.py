"""General-purpose HTTP client."""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.exceptions import RequestException

from sap_cloud_sdk.core.http_client.exceptions import (
    HttpConnectionError,
    HttpNotFoundError,
    HttpResponseError,
    HttpUnauthorizedError,
)
from sap_cloud_sdk.core.odata._constants import DELETE, GET, PATCH, POST, PUT
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


def _raise_for_status(response: requests.Response) -> None:
    if response.status_code == 404:
        raise HttpNotFoundError(response)
    if response.status_code in (401, 403):
        raise HttpUnauthorizedError(response)
    if not response.ok:
        raise HttpResponseError(response)


class HttpClient:
    """General-purpose HTTP client with typed convenience methods.

    Wraps a pre-configured ``requests.Session`` and raises typed exceptions on
    non-2xx responses.

    Use :func:`~sap_cloud_sdk.core.http_client.http_client_for_destination`
    to construct an instance from a resolved BTP ``Destination``.  For advanced
    use, inject any ``requests.Session`` directly.

    Args:
        base_url: Root URL of the target system.
        session: Pre-configured ``requests.Session`` (auth pre-baked by caller).

    Example::

        from sap_cloud_sdk.destination import create_client
        from sap_cloud_sdk.core.http_client import http_client_for_destination

        dest = create_client().get_destination("MY_API")
        client = http_client_for_destination(dest)
        response = client.get("/api/v1/resources")
    """

    def __init__(self, base_url: str, session: requests.Session) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    def request(
        self,
        method: str,
        path: str = "",
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send an HTTP request and return the raw response.

        Unlike the convenience methods (:meth:`get`, :meth:`post`, etc.) this
        method does **not** raise on non-2xx status codes — the caller is
        responsible for inspecting the response.

        Args:
            method: HTTP verb (``"GET"``, ``"POST"``, ``"PUT"``, etc.).
            path: Path relative to the base URL.  Empty string sends to the
                base URL itself.
            params: Query parameters.
            json: Request body serialised as JSON.
            data: Raw request body.
            headers: Extra headers merged with the session defaults.
            **kwargs: Forwarded to ``requests.Session.request``.

        Returns:
            The raw ``requests.Response`` object.

        Raises:
            HttpConnectionError: If a network-level error prevents the request
                from reaching the server.
        """
        url = self._base_url + "/" + path.lstrip("/") if path else self._base_url
        logger.debug("%s %s params=%s", method.upper(), url, params)
        try:
            return self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                **kwargs,
            )
        except RequestException as exc:
            raise HttpConnectionError(str(exc)) from exc

    @record_metrics(Module.HTTP_CLIENT, Operation.HTTP_CLIENT_GET)
    def get(
        self,
        path: str = "",
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a GET request.

        Args:
            path: Path relative to the base URL.
            params: Query parameters.
            headers: Extra headers.
            **kwargs: Forwarded to ``requests.Session.request``.

        Returns:
            ``requests.Response`` on success (2xx).

        Raises:
            HttpNotFoundError: On HTTP 404.
            HttpUnauthorizedError: On HTTP 401 or 403.
            HttpResponseError: On any other non-2xx status.
            HttpConnectionError: On network failure.
        """
        resp = self.request(GET, path, params=params, headers=headers, **kwargs)
        _raise_for_status(resp)
        return resp

    @record_metrics(Module.HTTP_CLIENT, Operation.HTTP_CLIENT_POST)
    def post(
        self,
        path: str = "",
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a POST request.

        Args:
            path: Path relative to the base URL.
            json: Body serialised as JSON.
            data: Raw body.
            headers: Extra headers.
            **kwargs: Forwarded to ``requests.Session.request``.

        Returns:
            ``requests.Response`` on success (2xx).

        Raises:
            HttpNotFoundError: On HTTP 404.
            HttpUnauthorizedError: On HTTP 401 or 403.
            HttpResponseError: On any other non-2xx status.
            HttpConnectionError: On network failure.
        """
        resp = self.request(POST, path, json=json, data=data, headers=headers, **kwargs)
        _raise_for_status(resp)
        return resp

    @record_metrics(Module.HTTP_CLIENT, Operation.HTTP_CLIENT_PUT)
    def put(
        self,
        path: str = "",
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a PUT request.

        Args:
            path: Path relative to the base URL.
            json: Body serialised as JSON.
            data: Raw body.
            headers: Extra headers.
            **kwargs: Forwarded to ``requests.Session.request``.

        Returns:
            ``requests.Response`` on success (2xx).

        Raises:
            HttpNotFoundError: On HTTP 404.
            HttpUnauthorizedError: On HTTP 401 or 403.
            HttpResponseError: On any other non-2xx status.
            HttpConnectionError: On network failure.
        """
        resp = self.request(PUT, path, json=json, data=data, headers=headers, **kwargs)
        _raise_for_status(resp)
        return resp

    @record_metrics(Module.HTTP_CLIENT, Operation.HTTP_CLIENT_PATCH)
    def patch(
        self,
        path: str = "",
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a PATCH request.

        Args:
            path: Path relative to the base URL.
            json: Body serialised as JSON.
            data: Raw body.
            headers: Extra headers.
            **kwargs: Forwarded to ``requests.Session.request``.

        Returns:
            ``requests.Response`` on success (2xx).

        Raises:
            HttpNotFoundError: On HTTP 404.
            HttpUnauthorizedError: On HTTP 401 or 403.
            HttpResponseError: On any other non-2xx status.
            HttpConnectionError: On network failure.
        """
        resp = self.request(PATCH, path, json=json, data=data, headers=headers, **kwargs)
        _raise_for_status(resp)
        return resp

    @record_metrics(Module.HTTP_CLIENT, Operation.HTTP_CLIENT_DELETE)
    def delete(
        self,
        path: str = "",
        *,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a DELETE request.

        Args:
            path: Path relative to the base URL.
            headers: Extra headers.
            **kwargs: Forwarded to ``requests.Session.request``.

        Returns:
            ``requests.Response`` on success (2xx).

        Raises:
            HttpNotFoundError: On HTTP 404.
            HttpUnauthorizedError: On HTTP 401 or 403.
            HttpResponseError: On any other non-2xx status.
            HttpConnectionError: On network failure.
        """
        resp = self.request(DELETE, path, headers=headers, **kwargs)
        _raise_for_status(resp)
        return resp
