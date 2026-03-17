from sap_cloud_sdk.dms._models import DMSCredentials


class DMSClient:
    """Client for interacting with the DMS service."""

    def __init__(self, credentials: DMSCredentials):
        """Initialize the DMS client with provided credentials.

        Args:
            credentials: DMSCredentials constructed from either BindingData or directly with required fields.
        """
        #fetch access token
        try:
            credentials.access_token
        except Exception as e:
            raise ValueError(f"Failed to fetch access token: {e}")
        
        credentials = credentials