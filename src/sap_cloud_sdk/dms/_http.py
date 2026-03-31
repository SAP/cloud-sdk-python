import logging
from typing import Any, Optional
from requests import Response
import requests
from requests.exceptions import RequestException
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms.exceptions import (
    DMSError,
    DMSConflictException,
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
        params: Optional[dict[str, str]] = None,
    ) -> Response:
        logger.debug("GET %s", path)
        return self._handle(self._execute(
            lambda: requests.get(
                f"{self._base_url}{path}",
                headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                params=params,
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

    def post_form(
        self,
        path: str,
        *,
        data: dict[str, str],
        files: Optional[dict[str, Any]] = None,
        tenant_subdomain: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        """POST with form-encoded data and optional multipart file uploads.

        Does not set Content-Type — ``requests`` sets it automatically
        to ``application/x-www-form-urlencoded`` or ``multipart/form-data``.
        """
        logger.debug("POST_FORM %s", path)
        return self._handle(self._execute(
            lambda: requests.post(
                f"{self._base_url}{path}",
                headers=self._auth_header(tenant_subdomain, user_claim),
                data=data,
                files=files,
                timeout=(self._connect_timeout, self._read_timeout),
            )
        ))

    def get_stream(
        self,
        path: str,
        *,
        params: Optional[dict[str, str]] = None,
        tenant_subdomain: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        """GET that returns a raw streaming Response for binary content.

        The caller is responsible for closing the response.
        On non-2xx status the usual typed exception is raised.
        """
        logger.debug("GET_STREAM %s", path)
        return self._handle(self._execute(
            lambda: requests.get(
                f"{self._base_url}{path}",
                headers=self._merged_headers(tenant_subdomain, None, user_claim),
                params=params,
                stream=True,
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

    def _auth_header(
        self,
        tenant_subdomain: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> dict[str, str]:
        """Auth-only headers (no Content-Type). Used by post_form."""
        return {
            "Authorization": f"Bearer {self._auth.get_token(tenant_subdomain)}",
            **self._user_claim_headers(user_claim),
        }

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

        # Try to extract the server's error message from the JSON body
        try:
            body = response.json()
            server_message = body.get("message", "") if isinstance(body, dict) else ""
        except Exception:
            server_message = ""

        match response.status_code:
            case 400:
                raise DMSInvalidArgumentException(
                    server_message or "Request contains invalid or disallowed parameters", 400, error_content
                )
            case 401 | 403:
                raise DMSPermissionDeniedException(
                    server_message or "Access denied — invalid or expired token", response.status_code, error_content
                )
            case 404:
                raise DMSObjectNotFoundException(
                    server_message or "The requested resource was not found", 404, error_content
                )
            case 409:
                raise DMSConflictException(
                    server_message or "The request conflicts with the current state of the resource", 409, error_content
                )
            case 500:
                raise DMSRuntimeException(
                    server_message or "The DMS service encountered an internal error", 500, error_content
                )
            case _:
                raise DMSError(
                    f"Unexpected response from DMS service: {error_content}", response.status_code, error_content
                )