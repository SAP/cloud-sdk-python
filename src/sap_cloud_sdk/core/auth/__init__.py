"""SAP Cloud SDK — core authentication and authorization primitives.

Provides generic, service-agnostic building blocks for all SDK modules:

Token cache:
    - :class:`TokenCache` — abstract pluggable cache interface
    - :class:`InMemoryTokenCache` — default single-process implementation
    - :class:`RedisTokenCache` — shared cache for multi-instance deployments

IAS token fetching:
    - :class:`IasTokenFetcher` — client_credentials + jwt-bearer (OBO) against SAP IAS
    - :data:`AuthError` — raised on token acquisition failures

mTLS:
    - :class:`MTLSStrategy` — apply X.509 client cert to requests.Session / httpx.AsyncClient
    - :class:`MTLSConfig` — immutable holder for cert + key PEM material
"""

from sap_cloud_sdk.core.auth._token_cache import (
    InMemoryTokenCache,
    RedisTokenCache,
    TokenCache,
)
from sap_cloud_sdk.core.auth._ias_fetcher import (
    AuthError,
    IasTokenFetcher,
)
from sap_cloud_sdk.core.auth._mtls import (
    MTLSConfig,
    MTLSStrategy,
)

__all__ = [
    # token cache
    "TokenCache",
    "InMemoryTokenCache",
    "RedisTokenCache",
    # IAS auth
    "AuthError",
    "IasTokenFetcher",
    # mTLS
    "MTLSConfig",
    "MTLSStrategy",
]
