"""Data models for DMS service."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import requests


@dataclass
class DMSCredentials:
    """Credentials for DMS service access.

    Contains the necessary information to authenticate and connect to the DMS service,
    including the service URI and UAA credentials for OAuth2 authentication.
    
    Token lifecycle is managed manually because the service uses OAuth2 client credentials
    grant, which does not issue refresh tokens. Libraries like requests_oauthlib assume
    refresh token flow for token renewal and are not suitable here.
    """
    instance_name: str
    uri: str
    client_id: str
    client_secret: str
    token_url: str
    _access_token: str = field(default="", repr=False)
    _token_expiry: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        repr=False
    )

    @property
    def access_token(self) -> str:
        if not self._access_token or datetime.now(tz=timezone.utc) >= self._token_expiry:
            self._access_token, self._token_expiry = self._retrieve_access_token()
        return self._access_token
    
    def _retrieve_access_token(self) -> tuple[str, datetime]:
        """Fetch a new OAuth2 token using client credentials grant.
        
        Raises:
            RuntimeError: If the token response is missing access_token.
            requests.HTTPError: If the token endpoint returns a non-2xx response.
        """
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        
        token_response = response.json()
        if "access_token" not in token_response:
            raise RuntimeError("access_token missing in response")
        
        expires_in = token_response.get("expires_in", 3600)  # fallback 1hr
        expiry = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in) - timedelta(minutes=5)
        
        return token_response["access_token"], expiry
    