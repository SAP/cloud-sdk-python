import logging
from typing import Any, Optional
from requests import Response
import requests
from requests.exceptions import RequestException
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms.exceptions import (
    DMSError,
    DMSConnectionError,
    DMSInvalidArgumentException,
    DMSObjectNotFoundException,
    DMSPermissionDeniedException,
    DMSRuntimeException,
)
from sap_cloud_sdk.dms.model import UserClaim

logger = logging.getLogger(__name__)


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
    ) -> Response:
        logger.debug("GET %s", path)
        return self._handle(self._execute(
            lambda: requests.get(
                f"{self._base_url}{path}",
                headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                timeout=(self._connect_timeout, self._read_timeout),
            )
        ))

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        logger.debug("POST %s", path)
        return self._handle(self._execute(
            lambda: requests.post(
                f"{self._base_url}{path}",
                headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                json=payload,
                timeout=(self._connect_timeout, self._read_timeout),
            )
        ))

    def put(
        self,
        path: str,
        payload: dict[str, Any],
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        logger.debug("PUT %s", path)
        return self._handle(self._execute(
            lambda: requests.put(
                f"{self._base_url}{path}",
                headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                json=payload,
                timeout=(self._connect_timeout, self._read_timeout),
            )
        ))

    def delete(
        self,
        path: str,
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        logger.debug("DELETE %s", path)
        return self._handle(self._execute(
            lambda: requests.delete(
                f"{self._base_url}{path}",
                headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                timeout=(self._connect_timeout, self._read_timeout),
            )
        ))

    def _execute(self, fn: Any) -> Response:
        """Execute an HTTP call, wrapping network errors into DMSConnectionError."""
        try:
            return fn()
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error during HTTP request")
            raise DMSConnectionError("Failed to connect to the DMS service") from e
        except requests.exceptions.Timeout as e:
            logger.error("Request timed out")
            raise DMSConnectionError("Request to DMS service timed out") from e
        except RequestException as e:
            logger.error("Unexpected network error")
            raise DMSConnectionError("Unexpected network error") from e

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

    def _handle(self, response: Response) -> Response:
        logger.debug("Response status: %s", response.status_code)
        if response.status_code in (200, 201, 204):
            return response

        # error_content kept for debugging but not surfaced in the exception message
        error_content = response.text
        logger.warning("Request failed with status %s", response.status_code)

        match response.status_code:
            case 400:
                raise DMSInvalidArgumentException(
                    "Request contains invalid or disallowed parameters", 400, error_content
                )
            case 401 | 403:
                raise DMSPermissionDeniedException(
                    "Access denied — invalid or expired token", response.status_code, error_content
                )
            case 404:
                raise DMSObjectNotFoundException(
                    "The requested resource was not found", 404, error_content
                )
            case 500:
                raise DMSRuntimeException(
                    "The DMS service encountered an internal error", 500, error_content
                )
            case _:
                raise DMSError(
                    f"Unexpected response from DMS service : "+error_content, response.status_code, error_content
                )