"""IAS token management for the ADMS module — thin ADMS adapter over core auth.

All token-fetching logic lives in :mod:`sap_cloud_sdk.core.auth._ias_fetcher`.
This module provides ADMS-specific wrappers that:

* Accept :class:`~sap_cloud_sdk.adms.config.AdmsConfig` instead of raw URL/credentials.
* Re-raise :class:`~sap_cloud_sdk.core.auth.AuthError` as ADMS's own
  :class:`~sap_cloud_sdk.adms.exceptions.AuthError` (a subclass of
  ``AdmsError``) so that callers using ``except AdmsError`` still catch auth failures.

The public symbols exported here match what the existing ADMS unit-tests import,
so no test changes are required.
"""

from __future__ import annotations

import requests

# Core implementations — real logic lives here
from sap_cloud_sdk.core.auth import (
    IasTokenFetcher as _CoreIasTokenFetcher,
    AuthError as _CoreAuthError,
    TokenCache,
)
from sap_cloud_sdk.adms.exceptions import AuthError

__all__ = [
    "IasTokenFetcher",
]


class IasTokenFetcher(_CoreIasTokenFetcher):
    """ADMS-flavoured IAS token fetcher that accepts :class:`AdmsConfig`.

    Inherits all caching / fetching logic from the core layer.  Converts
    :class:`~sap_cloud_sdk.core.auth.AuthError` to
    :class:`~sap_cloud_sdk.adms.exceptions.AuthError` (a ``AdmsError`` subclass)
    so existing ``except AdmsError / AuthError`` handlers are unaffected.

    Args:
        config: :class:`~sap_cloud_sdk.adms.config.AdmsConfig` with IAS credentials.
        session: Optional ``requests.Session`` to reuse (useful for testing).
        cache: Pluggable :class:`~sap_cloud_sdk.core.auth.TokenCache`.
            Defaults to :class:`~sap_cloud_sdk.core.auth.InMemoryTokenCache`.
            Pass a :class:`~sap_cloud_sdk.core.auth.RedisTokenCache` for
            multi-instance deployments.
    """

    def __init__(
        self,
        config,  # AdmsConfig — not type-annotated to avoid circular import at module level
        session: requests.Session | None = None,
        cache: TokenCache | None = None,
    ) -> None:
        super().__init__(
            ias_url=config.ias_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            session=session,
            cache=cache,
            resource=getattr(config, "resource", None),
        )

    def get_token(self) -> str:
        try:
            return super().get_token()
        except _CoreAuthError as exc:
            raise AuthError(str(exc)) from exc

    def exchange_token(self, user_jwt: str) -> str:
        try:
            return super().exchange_token(user_jwt)
        except _CoreAuthError as exc:
            raise AuthError(str(exc)) from exc
