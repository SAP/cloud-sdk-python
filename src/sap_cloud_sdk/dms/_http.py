import logging
from typing import Any, Optional
from requests import Response
from requests.exceptions import RequestException
from sap_cloud_sdk.core.protocol.http import HttpClient, HttpMethod, XsuaaAuthProvider
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
    """Low-level HTTP layer for DMS. Wraps HttpClient with DMS error mapping."""

    def __init__(
        self,
        auth_provider: XsuaaAuthProvider,
        base_url: str,
        connect_timeout: int | None = None,
        read_timeout: int | None = None,
    ) -> None:
        timeout = float(read_timeout or 30)
        self._http = HttpClient(base_url, auth_provider, timeout=timeout)
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
        return self._handle(
            self._execute(
                lambda: self._http.request(
                    HttpMethod.GET,
                    path,
                    tenant_subdomain=tenant_subdomain,
                    headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                    params=params,
                )
            )
        )

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        logger.debug("POST %s", path)
        return self._handle(
            self._execute(
                lambda: self._http.request(
                    HttpMethod.POST,
                    path,
                    tenant_subdomain=tenant_subdomain,
                    headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                    json=payload,
                )
            )
        )

    def put(
        self,
        path: str,
        payload: dict[str, Any],
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        logger.debug("PUT %s", path)
        return self._handle(
            self._execute(
                lambda: self._http.request(
                    HttpMethod.PUT,
                    path,
                    tenant_subdomain=tenant_subdomain,
                    headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                    json=payload,
                )
            )
        )

    def delete(
        self,
        path: str,
        tenant_subdomain: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        logger.debug("DELETE %s", path)
        return self._handle(
            self._execute(
                lambda: self._http.request(
                    HttpMethod.DELETE,
                    path,
                    tenant_subdomain=tenant_subdomain,
                    headers=self._merged_headers(tenant_subdomain, headers, user_claim),
                )
            )
        )

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
        return self._handle(
            self._execute(
                lambda: self._http.request(
                    HttpMethod.POST,
                    path,
                    tenant_subdomain=tenant_subdomain,
                    headers=self._auth_header(tenant_subdomain, user_claim),
                    data=data,
                    files=files,
                )
            )
        )

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
        return self._handle(
            self._execute(
                lambda: self._http.request(
                    HttpMethod.GET,
                    path,
                    tenant_subdomain=tenant_subdomain,
                    headers=self._merged_headers(tenant_subdomain, None, user_claim),
                    params=params,
                    stream=True,
                )
            )
        )

    def _execute(self, fn: Any) -> Response:
        try:
            return fn()
        except RequestException as e:
            logger.error("Connection error during HTTP request")
            raise DMSConnectionError("Failed to connect to the DMS service") from e

    def _auth_header(
        self,
        tenant_subdomain: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> dict[str, str]:
        return {
            **self._user_claim_headers(user_claim),
        }

    def _default_headers(
        self, tenant_subdomain: Optional[str] = None
    ) -> dict[str, str]:
        return {
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

        error_content = response.text
        logger.warning("Request failed with status %s", response.status_code)

        try:
            body = response.json()
            server_message = body.get("message", "") if isinstance(body, dict) else ""
        except Exception:
            server_message = ""

        match response.status_code:
            case 400:
                raise DMSInvalidArgumentException(
                    server_message
                    or "Request contains invalid or disallowed parameters",
                    400,
                    error_content,
                )
            case 401 | 403:
                raise DMSPermissionDeniedException(
                    server_message or "Access denied — invalid or expired token",
                    response.status_code,
                    error_content,
                )
            case 404:
                raise DMSObjectNotFoundException(
                    server_message or "The requested resource was not found",
                    404,
                    error_content,
                )
            case 409:
                raise DMSConflictException(
                    server_message
                    or "The request conflicts with the current state of the resource",
                    409,
                    error_content,
                )
            case 500:
                raise DMSRuntimeException(
                    server_message or "The DMS service encountered an internal error",
                    500,
                    error_content,
                )
            case _:
                raise DMSError(
                    f"Unexpected response from DMS service: {error_content}",
                    response.status_code,
                    error_content,
                )
