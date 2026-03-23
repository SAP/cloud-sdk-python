from typing import Any, Optional
import requests
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms.exceptions import HttpError


class HttpInvoker:
    """Low-level HTTP layer. Injects auth headers and enforces timeouts."""

    def __init__(
        self,
        auth: Auth,
        base_url: str,
        connect_timeout: int | None = None,
        read_timeout: int | None = None,
    ) -> None:
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._connect_timeout = connect_timeout or 10
        self._read_timeout = read_timeout or 30

    def get(self, path: str, tenant_subdomain: Optional[str] = None) -> Any:
        response = requests.get(
            f"{self._base_url}{path}",
            headers=self._headers(tenant_subdomain),
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._handle(response)

    def post(self, path: str, payload: dict[str, Any], tenant_subdomain: Optional[str] = None) -> Any:
        response = requests.post(
            f"{self._base_url}{path}",
            headers=self._headers(tenant_subdomain),
            json=payload,
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._handle(response)

    def delete(self, path: str, tenant_subdomain: Optional[str] = None) -> Any:
        response = requests.delete(
            f"{self._base_url}{path}",
            headers=self._headers(tenant_subdomain),
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._handle(response)

    def _headers(self, tenant_subdomain: Optional[str] = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._auth.get_token(tenant_subdomain)}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle(self, response: requests.Response) -> Any:
        if response.status_code in (200, 201, 204):
            return response.json() if response.content else None

        raise HttpError(
            message=response.text,
            status_code=response.status_code,
            response_text=response.text,
        )