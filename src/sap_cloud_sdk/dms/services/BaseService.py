import logging
import requests
from typing import Any, Dict, Optional
from sap_cloud_sdk.dms.model.dms_credentials import DMSCredentials
from sap_cloud_sdk.dms.exceptions import DmsException

logger = logging.getLogger(__name__)


class BaseService:
    DEFAULT_CONNECT_TIMEOUT: int = 30
    DEFAULT_READ_TIMEOUT: int = 600

    def __init__(
        self,
        dms_credentials: DMSCredentials,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ) -> None:
        self._credentials = dms_credentials
        self._session = requests.Session()
        self._connect_timeout: int = connect_timeout or self.DEFAULT_CONNECT_TIMEOUT
        self._read_timeout: int = read_timeout or self.DEFAULT_READ_TIMEOUT

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._credentials.access_token}",
            "User-Agent": "sap-cloud-sdk-python",
        }

    def _get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        req_headers = self._auth_headers().copy()
        if headers:
            req_headers.update(headers)
        resp = self._session.get(
            f"{self._credentials.uri}{path}",
            headers=req_headers,
            params=params,
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._parse_response(resp)

    def _post(
        self,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        #merge headers like Content-Type with auth headers if provided
        req_headers = self._auth_headers().copy()
        if headers:
            req_headers.update(headers)
        resp = self._session.post(
            f"{self._credentials.uri}{path}",
            headers=req_headers,
            json=json_data,
            data=data,
            files=files,
            timeout=(self._connect_timeout, self._read_timeout),
        )
        return self._parse_response(resp)

    def _delete(self, path: str) -> None:
        resp = self._session.delete(
            f"{self._credentials.uri}{path}",
            headers=self._auth_headers(),
            timeout=(self._connect_timeout, self._read_timeout),
        )
        self._parse_response(resp)

    def _parse_response(self, response: requests.Response) -> Any:

        if response.ok:
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise DmsException( #TODO make this more specific by parsing error details from response if available
            message=response.reason or f"HTTP {response.status_code}",
            status_code=response.status_code,
            error_content=response.text or None,
        )