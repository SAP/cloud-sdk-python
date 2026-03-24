from typing import Any, Optional
import requests
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms.exceptions import HttpError
from sap_cloud_sdk.dms.model.model import UserClaim


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

    def get(
        self,
        path: str,
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Any:
        response = requests.get(
            f"{self._base_url}{path}",
            headers=self._merged_headers(tenant_subdomain, headers, user_claim),
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._handle(response)

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Any:
        response = requests.post(
            f"{self._base_url}{path}",
            headers=self._merged_headers(tenant_subdomain, headers, user_claim),
            json=payload,
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._handle(response)

    def delete(
        self,
        path: str,
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Any:
        response = requests.delete(
            f"{self._base_url}{path}",
            headers=self._merged_headers(tenant_subdomain, headers, user_claim),
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._handle(response)

    def _default_headers(self, tenant_subdomain: Optional[str] = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._auth.get_token(tenant_subdomain)}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _user_claim_headers(self, user_claim: Optional[UserClaim]) -> dict[str, str]:
        if not user_claim:
            return {}
        headers: dict[str, str] = {}
        if user_claim.x_ecm_user_enc:
            headers["X-EcmUserEnc"] = user_claim.x_ecm_user_enc
        if user_claim.x_ecm_add_principals:
            headers["X-EcmAddPrincipals"] = ";".join(user_claim.x_ecm_add_principals)
        return headers

    def _merged_headers(
        self,
        tenant_subdomain: Optional[str],
        overrides: Optional[dict[str, str]],
        user_claim: Optional[UserClaim] = None,
    ) -> dict[str, str]:
        return {
            **self._default_headers(tenant_subdomain),
            **self._user_claim_headers(user_claim),
            **(overrides or {}),
        }

    def _handle(self, response: requests.Response) -> Any:
        if response.status_code in (200, 201, 204):
            return response.json() if response.content else None

        raise HttpError(
            message=response.text,
            status_code=response.status_code,
            response_text=response.text,
        )