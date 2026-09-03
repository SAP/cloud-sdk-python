"""HTTP utilities shared across all Destination Service clients."""

from __future__ import annotations

from typing import Any, Optional

from requests import Response
from requests.exceptions import RequestException

from sap_cloud_sdk.core._http_client import HttpClient, HttpMethod
from sap_cloud_sdk.destination.exceptions import HttpError

API_V1 = "v1"
API_V2 = "v2"


def _request(
    http: HttpClient,
    method: HttpMethod,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
    tenant_subdomain: Optional[str] = None,
) -> Response:

    all_headers: dict = {"Accept": "application/json"}
    if headers:
        all_headers.update(headers)

    normalized_path = f"/{path.lstrip('/')}"
    try:
        resp = http.request(
            method,
            normalized_path,
            tenant_subdomain=tenant_subdomain,
            params=params,
            json=json,
            headers=all_headers,
        )
    except RequestException as e:
        raise HttpError(f"request failed: {e}")
    if isinstance(resp.status_code, int) and 200 <= resp.status_code < 300:
        return resp
    text: str = ""
    try:
        text = resp.text
    except Exception:
        text = "<failed to read response body>"
    raise HttpError(
        f"HTTP {resp.status_code} for {method.value} {normalized_path}",
        status_code=resp.status_code,
        response_text=text,
    )
