from typing import Any, Optional
from sap_cloud_sdk.dms.model.model import DMSCredentials, InternalRepoRequest
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms._http import HttpInvoker
from sap_cloud_sdk.dms import _endpoints as endpoints

class DMSClient:
    """Client for interacting with the DMS service."""

    def __init__(
        self,
        credentials: DMSCredentials,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ) -> None:
        auth = Auth(credentials)
        self._http : HttpInvoker = HttpInvoker(
            auth=auth,
            base_url=credentials.uri,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

    def onboard_repository(
        self,
        request: InternalRepoRequest,
        tenant: Optional[str] = None,
    ) -> Any:
        """Create a new internal repository."""
        return self._http.post(endpoints.REPOSITORIES, request.to_dict(), tenant)

