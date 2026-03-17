from sap_cloud_sdk.dms.model.dms_credentials import DMSCredentials
from sap_cloud_sdk.dms.services.AdminService import AdminService
from typing import Optional

class DMSClient:
    """Client for interacting with the DMS service."""

    def __init__(
        self,
        credentials: DMSCredentials,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ):
        """Initialize the DMS client with provided credentials and optional timeouts.

        Args:
            credentials: DMSCredentials constructed from either BindingData or directly with required fields.
            connect_timeout: Optional connect timeout in seconds.
            read_timeout: Optional read timeout in seconds.
        """
        # fetch access token
        try:
            credentials.access_token
        except Exception as e:
            raise ValueError(f"Failed to fetch access token: {e}")

        self.credentials = credentials
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self._admin = AdminService(
            self.credentials,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
        )

    @property
    def admin(self) -> AdminService:
        return self._admin
    
    