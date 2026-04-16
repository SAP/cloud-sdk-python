"""Data models and enums for the SAP Destination Service (v1).

This module defines:
- Enums for selecting destination scope and access strategy
- Dataclasses for representing service bindings (OAuth and base URLs)
- Dataclasses for the Destination, Fragment and Certificate entities with basic parsing and serialization helpers
- Dataclass for ListOptions to configure list operations

These models are used by the Destination client and HTTP utilities to:
- Normalize credentials and service endpoints (DestinationConfig from sap_cloud_sdk.destination.config)
- Represent Destination entities returned by the API (Destination)
- Provide helper methods to parse API payloads and serialize payloads
  while preserving unknown string-valued properties.

Example:
    ```python
    from sap_cloud_sdk.destination._models import Destination, Level

    # Build a payload to create a simple HTTP destination
    dest = Destination(
        name="my-destination",
        type="HTTP",
        url="https://api.example.com",
        proxy_type="Internet",
        authentication="NoAuthentication",
        description="Sample destination",
        properties={"x-custom": "value"}  # extra string props are preserved
    )

    payload = dest.to_dict()  # ready to send to the service
    ```

Notes:
    - The Destination dataclass performs minimal validation in from_dict to
      ensure required fields are present. The server schema is the ultimate
      source of truth.
    - Unknown string-valued fields are captured in `properties` and round-tripped
      by to_dict without overriding known fields.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Dict, List

from sap_cloud_sdk.destination.utils._params import (
    Params,
    build_pagination_params,
    build_filter_param,
)
from sap_cloud_sdk.destination.exceptions import DestinationOperationError


class Level(Enum):
    """Destination level selection for API operations.

    Selects the scope where the destination resides or should be managed.

    Attributes:
        SERVICE_INSTANCE: Operate on destinations bound to the service instance
        SUB_ACCOUNT: Operate on destinations bound to the subaccount
    """

    SERVICE_INSTANCE = "SERVICE_INSTANCE"
    SUB_ACCOUNT = "SUB_ACCOUNT"


class AccessStrategy(Enum):
    """Access strategy controlling precedence between subscriber and provider.

    This strategy is used primarily when reading subaccount destinations where both
    subscriber and provider scopes may be available.

    Attributes:
        SUBSCRIBER_ONLY: Read from subscriber context only (tenant required)
        PROVIDER_ONLY: Read from provider context only
        SUBSCRIBER_FIRST: Try subscriber first, then fallback to provider
        PROVIDER_FIRST: Try provider first, then fallback to subscriber
    """

    SUBSCRIBER_ONLY = "SUBSCRIBER_ONLY"
    PROVIDER_ONLY = "PROVIDER_ONLY"
    SUBSCRIBER_FIRST = "SUBSCRIBER_FIRST"
    PROVIDER_FIRST = "PROVIDER_FIRST"


class DestinationType(Enum):
    """Destination type (subset of v1)."""

    HTTP = "HTTP"
    RFC = "RFC"
    MAIL = "MAIL"
    LDAP = "LDAP"
    TCP = "TCP"


class ProxyType(Enum):
    """Proxy type for HTTP destinations."""

    INTERNET = "Internet"
    ON_PREMISE = "OnPremise"
    PRIVATE_LINK = "PrivateLink"


class Authentication(Enum):
    """Authentication method for destinations (subset of v1)."""

    NO_AUTHENTICATION = "NoAuthentication"
    BASIC_AUTHENTICATION = "BasicAuthentication"
    CLIENT_CERTIFICATE_AUTHENTICATION = "ClientCertificateAuthentication"
    PRINCIPAL_PROPAGATION = "PrincipalPropagation"
    OAUTH2_CLIENT_CREDENTIALS = "OAuth2ClientCredentials"
    OAUTH2_JWT_BEARER = "OAuth2JWTBearer"
    OAUTH2_PASSWORD = "OAuth2Password"
    OAUTH2_REFRESH_TOKEN = "OAuth2RefreshToken"
    OAUTH2_SAML_BEARER_ASSERTION = "OAuth2SAMLBearerAssertion"
    OAUTH2_USER_TOKEN_EXCHANGE = "OAuth2UserTokenExchange"
    OAUTH2_TOKEN_EXCHANGE = "OAuth2TokenExchange"
    OAUTH2_AUTHORIZATION_CODE = "OAuth2AuthorizationCode"
    OAUTH2_TECHNICAL_USER_PROPAGATION = "OAuth2TechnicalUserPropagation"
    SAML_ASSERTION = "SAMLAssertion"


def _parse_destination_type(value: Any) -> DestinationType | str | None:
    if value is None:
        return None
    if isinstance(value, DestinationType):
        return value
    if isinstance(value, str):
        for m in DestinationType:
            if m.value == value:
                return m
        return value
    return None


def _parse_proxy_type(value: Any) -> ProxyType | str | None:
    if value is None:
        return None
    if isinstance(value, ProxyType):
        return value
    if isinstance(value, str):
        for m in ProxyType:
            if m.value == value:
                return m
        return value
    return None


def _parse_authentication(value: Any) -> Authentication | str | None:
    if value is None:
        return None
    if isinstance(value, Authentication):
        return value
    if isinstance(value, str):
        for m in Authentication:
            if m.value == value:
                return m
        return value
    return None


@dataclass
class Destination:
    """Unified destination entity supporting both v1 admin API and v2 consumption API.

    Fields:
        name: Destination name (required)
        type: Destination type (e.g., "HTTP") (required)
        url: Target URL for HTTP destinations
        proxy_type: Proxy type (e.g., "Internet")
        authentication: Authentication type (e.g., "NoAuthentication")
        description: Optional human-readable description
        properties: Unknown string-valued fields preserved from API payloads
        auth_tokens: List of authentication tokens (v2 consumption API only)
        certificates: List of certificates (v2 consumption API only)

    The class provides:
      - from_dict: Parses a raw dict into Destination, accepting both lower and upper
        camel-case variants for well-known keys and capturing extra string-valued properties
      - to_dict: Serializes the dataclass back into a payload compatible with the API
        (subset), merging unknown properties without overriding known fields
    """

    name: str
    # Core attributes (subset of v1 schema)
    type: DestinationType | str
    url: Optional[str] = None
    proxy_type: ProxyType | str | None = None
    authentication: Authentication | str | None = None
    description: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)
    # V2 consumption API fields (populated when consuming destinations)
    auth_tokens: List["AuthToken"] = field(default_factory=list)
    certificates: List["Certificate"] = field(default_factory=list)

    @classmethod
    def from_dict(
        cls, obj: Dict[str, Any], include_runtime_data: bool = False
    ) -> "Destination":
        """Parse a raw destination dict into a Destination dataclass.

        Accepts both lower and upper camel-case variants for some fields (best-effort).
        Unknown string-valued fields are captured into `properties` with their original key casing.

        Args:
            obj: Raw dict returned by the Destination Service.
            include_runtime_data: If True, parse auth_tokens and certificates from v2 response.

        Returns:
            Destination: Parsed destination dataclass.

        Raises:
            DestinationOperationError: If required fields are missing (name/type).
        """
        # Extract core fields
        name, type_, url, proxy_type, authentication, description = (
            cls._extract_core_fields(obj)
        )

        # Validate required fields
        cls._validate_required_fields(name, type_)

        # Extract unknown properties
        properties = cls._extract_unknown_properties(obj)

        # Parse V2 runtime data if requested
        auth_tokens, certificates = cls._parse_runtime_data(obj, include_runtime_data)

        return cls(
            name=name,
            type=type_,
            url=url,
            proxy_type=proxy_type,
            authentication=authentication,
            description=description,
            properties=properties,
            auth_tokens=auth_tokens,
            certificates=certificates,
        )

    @staticmethod
    def _extract_core_fields(obj: Dict[str, Any]) -> tuple:
        """Extract core destination fields from dict."""
        name = obj.get("name") or obj.get("Name") or ""
        type_ = _parse_destination_type(obj.get("type") or obj.get("Type"))
        url = obj.get("url") or obj.get("URL")
        proxy_type = _parse_proxy_type(obj.get("proxyType") or obj.get("ProxyType"))
        authentication = _parse_authentication(
            obj.get("authentication") or obj.get("Authentication")
        )
        description = obj.get("description") or obj.get("Description")
        return name, type_, url, proxy_type, authentication, description

    @staticmethod
    def _validate_required_fields(name: str, type_: Any) -> None:
        """Validate required destination fields."""
        if type_ is None:
            raise DestinationOperationError(
                "destination is missing required fields (name/type)"
            )

        type_str = type_.value if isinstance(type_, DestinationType) else str(type_)

        if not name.strip() or not str(type_str).strip():
            raise DestinationOperationError(
                "destination is missing required fields (name/type)"
            )

    @staticmethod
    def _extract_unknown_properties(obj: Dict[str, Any]) -> Dict[str, str]:
        """Extract unknown string-valued properties from dict."""
        known_keys = {
            "name",
            "Name",
            "type",
            "Type",
            "url",
            "URL",
            "proxyType",
            "ProxyType",
            "authentication",
            "Authentication",
            "description",
            "Description",
            "authTokens",
            "auth_tokens",
            "certificates",
        }
        properties: Dict[str, str] = {}
        for k, v in obj.items():
            if k not in known_keys and isinstance(v, str):
                properties[k] = v
        return properties

    @staticmethod
    def _parse_runtime_data(obj: Dict[str, Any], include_runtime_data: bool) -> tuple:
        """Parse V2 runtime data (auth_tokens and certificates) if requested."""
        auth_tokens: List[AuthToken] = []
        certificates: List[Certificate] = []

        if include_runtime_data:
            auth_tokens_data = obj.get("authTokens") or obj.get("auth_tokens") or []
            auth_tokens = [AuthToken.from_dict(t) for t in auth_tokens_data]

            certs_data = obj.get("certificates") or []
            certificates = [Certificate.from_dict(c) for c in certs_data]

        return auth_tokens, certificates

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Destination to API payload (subset).

        Known fields are serialized with their respective API-casing. Any unknown
        string-valued fields stored in `properties` are merged without overriding
        the known fields present in the payload.

        Returns:
            Dict[str, Any]: API payload dictionary representing this destination.
        """
        payload: Dict[str, Any] = {
            "Name": self.name,
            "Type": self.type.value
            if isinstance(self.type, DestinationType)
            else self.type,
        }
        if self.url is not None:
            payload["URL"] = self.url
        if self.proxy_type is not None:
            payload["ProxyType"] = (
                self.proxy_type.value
                if isinstance(self.proxy_type, ProxyType)
                else self.proxy_type
            )
        if self.authentication is not None:
            payload["Authentication"] = (
                self.authentication.value
                if isinstance(self.authentication, Authentication)
                else self.authentication
            )
        if self.description is not None:
            payload["Description"] = self.description
        # Merge any unknown string properties without overriding known fields (case-sensitive)
        if self.properties:
            for k, v in self.properties.items():
                if k not in payload:
                    payload[k] = v
        return payload


@dataclass
class AuthToken:
    """Authentication token returned by v2 consumption API.

    Based on the AuthToken schema from the Destination Service OpenAPI spec.
    The v2 API retrieves and caches authentication tokens automatically.

    Fields:
        type: Token type (e.g., "Bearer", "Basic")
        value: Base64 encoded token binary content
        http_header: Dictionary with 'key' and 'value' for the prepared HTTP header
        refresh_token: Optional base64 encoded refresh token
        scope: Optional token scopes as space-delimited string
    """

    type: str
    value: str
    http_header: Dict[str, str]
    refresh_token: Optional[str] = None
    scope: Optional[str] = None

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "AuthToken":
        """Parse a raw auth token dict into an AuthToken dataclass.

        Args:
            obj: Raw dict returned by the Destination Service v2 API.

        Returns:
            AuthToken: Parsed auth token dataclass.

        Raises:
            DestinationOperationError: If required fields are missing.
        """
        token_type = obj.get("type") or ""
        value = obj.get("value") or ""
        http_header = obj.get("http_header") or {}
        refresh_token = obj.get("refresh_token")
        scope = obj.get("scope")

        if not token_type or not value or not http_header:
            raise DestinationOperationError(
                "auth token is missing required fields (type/value/http_header)"
            )

        return cls(
            type=token_type,
            value=value,
            http_header=http_header,
            refresh_token=refresh_token,
            scope=scope,
        )


@dataclass
class ConsumptionOptions:
    """Options for consuming a destination via the v2 runtime API.

    This class encapsulates optional parameters for destination consumption.

    Fields:
        fragment_name: Optional fragment name for property merging via X-fragment-name header
        tenant: Optional subscriber tenant subdomain for user token exchange

    Example:
        ```python
        from sap_cloud_sdk.destination import create_client, ConsumptionOptions

        client = create_client()

        # Simple consumption
        dest = client.get_destination("my-api")

        # With options
        options = ConsumptionOptions(fragment_name="production", tenant="tenant-1")
        dest = client.get_destination("my-api", options=options)

        # Or inline
        dest = client.get_destination(
            "my-api",
            options=ConsumptionOptions(fragment_name="prod")
        )
        ```
    """

    fragment_name: Optional[str] = None
    tenant: Optional[str] = None


@dataclass
class ListOptions:
    """Filter configuration for listing destinations and certificates.

    This class encapsulates query parameters for the list API endpoints
    (destinations, certificates, etc.). Supports filtering by name and pagination.

    Based on the Destination Service API specification:
    - $filter: Filter entities by name (in-list)
    - $page: Enable pagination and specify page number
    - $pageSize: Number of items per page
    - $pageCount: Include total page count in response
    - $entityCount: Include total entity count in response

    Example:
        ```python
        # Filter by names
        filter_obj = ListOptions(
            filter_names=["name1", "name2", "name3"]
        )

        # Pagination with page size
        filter_obj = ListOptions(
            page=1,
            page_size=10,
            page_count=True,
            entity_count=True
        )
        ```

    """

    # Filter options
    filter_names: Optional[List[str]] = None

    # Pagination options
    page: Optional[int] = None
    page_size: Optional[int] = None
    page_count: bool = False
    entity_count: bool = False

    def to_query_params(self) -> Dict[str, str]:
        """Convert filter configuration to query parameters.

        Returns:
            Dict[str, str]: Query parameters ready to be added to the HTTP request.

        Raises:
            DestinationOperationError: If filter configuration is invalid.
        """
        params: Dict[str, str] = {}

        # Build $filter parameter
        if self.filter_names:
            params[Params.FILTER.value] = build_filter_param("Name", self.filter_names)

        has_filter = self.filter_names is not None

        # Build pagination parameters using shared utility
        pagination_params = build_pagination_params(
            self.page,
            self.page_size,
            self.page_count,
            self.entity_count,
            has_select=False,
            has_filter=has_filter,
        )
        params.update(pagination_params)

        return params


@dataclass
class Certificate:
    """Certificate entity (subset of v1 schema).

    Certificates are used to store keystores and certificates for mTLS and other authentication.

    Fields:
        name: Certificate name (required)
        content: Base64 encoded certificate/keystore binary content (required)
        type: Type of the object (e.g., "PEM", "JKS", "PKCS12") (optional)
        properties: String-valued fields representing additional certificate properties

    The class provides:
      - from_dict: Parses a raw dict into Certificate
      - to_dict: Serializes the dataclass back into a payload compatible with the API
    """

    name: str
    content: str
    type: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "Certificate":
        """Parse a raw certificate dict into a Certificate dataclass.

        Accepts both lower and upper camel-case variants for known fields.
        All other string-valued fields are captured into `properties`.

        Args:
            obj: Raw dict returned by the Destination Service.

        Returns:
            Certificate: Parsed certificate dataclass.

        Raises:
            DestinationOperationError: If required fields (name/content) are missing.
        """
        name = obj.get("Name") or obj.get("name") or ""
        content = obj.get("Content") or obj.get("content") or ""
        type_ = obj.get("Type") or obj.get("type")

        if not name.strip() or not content.strip():
            raise DestinationOperationError(
                "certificate is missing required fields (Name/Content)"
            )

        known_keys = {"Name", "name", "Content", "content", "Type", "type"}
        properties: Dict[str, str] = {}
        for k, v in obj.items():
            if k not in known_keys and isinstance(v, str):
                properties[k] = v

        return cls(
            name=name,
            content=content,
            type=type_,
            properties=properties,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Certificate to API payload.

        Returns:
            Dict[str, Any]: API payload dictionary representing this certificate.
        """
        payload: Dict[str, Any] = {
            "Name": self.name,
            "Content": self.content,
        }
        if self.type is not None:
            payload["Type"] = self.type
        # Merge any unknown string properties without overriding known fields
        if self.properties:
            for k, v in self.properties.items():
                if k not in payload:
                    payload[k] = v
        return payload


@dataclass
class Fragment:
    """Fragment entity for destination fragments (subset of v1 schema).

    Fragments are used to override and/or extend destination properties.

    Fields:
        name: Fragment name (required)
        properties: String-valued fields representing fragment properties

    The class provides:
      - from_dict: Parses a raw dict into Fragment
      - to_dict: Serializes the dataclass back into a payload compatible with the API
    """

    name: str
    properties: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "Fragment":
        """Parse a raw fragment dict into a Fragment dataclass.

        Accepts both lower and upper camel-case variants for the fragment name field.
        All other string-valued fields are captured into `properties`.

        Args:
            obj: Raw dict returned by the Destination Service.

        Returns:
            Fragment: Parsed fragment dataclass.

        Raises:
            DestinationOperationError: If required field (name) is missing.
        """
        name = obj.get("FragmentName") or obj.get("fragmentName") or ""

        if not name.strip():
            raise DestinationOperationError(
                "fragment is missing required field (FragmentName)"
            )

        known_keys = {"FragmentName", "fragmentName"}
        properties: Dict[str, str] = {}
        for k, v in obj.items():
            if k not in known_keys and isinstance(v, str):
                properties[k] = v

        return cls(
            name=name,
            properties=properties,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Fragment to API payload.

        Returns:
            Dict[str, Any]: API payload dictionary representing this fragment.
        """
        payload: Dict[str, Any] = {
            "FragmentName": self.name,
        }
        # Merge any unknown string properties without overriding known fields
        if self.properties:
            for k, v in self.properties.items():
                if k not in payload:
                    payload[k] = v
        return payload


class TransparentProxyHeader(Enum):
    """Valid headers for Transparent Proxy destinations.

    Attributes:
        X_DESTINATION_NAME: Header for specifying the destination name
        AUTHORIZATION: Header for authorization
        X_FRAGMENT_NAME: Header for specifying the fragment name
        X_TENANT_SUBDOMAIN: Header for tenant subdomain
        X_TENANT_ID: Header for tenant ID
        X_FRAGMENT_OPTIONAL: Header for optional fragment flag
        X_DESTINATION_LEVEL: Header for destination level
        X_FRAGMENT_LEVEL: Header for fragment level
        X_TOKEN_SERVICE_TENANT: Header for token service tenant
        X_CLIENT_ASSERTION: Header for client assertion
        X_CLIENT_ASSERTION_TYPE: Header for client assertion type
        X_CLIENT_ASSERTION_DESTINATION_NAME: Header for client assertion destination name
        X_SUBJECT_TOKEN_TYPE: Header for subject token type
        X_ACTOR_TOKEN: Header for actor token
        X_ACTOR_TOKEN_TYPE: Header for actor token type
        X_REDIRECT_URI: Header for redirect URI
        X_CODE_VERIFIER: Header for code verifier
        X_CHAIN_NAME: Header for chain name
        X_CHAIN_VAR_SUBJECT_TOKEN: Header for chain variable subject token
        X_CHAIN_VAR_SUBJECT_TOKEN_TYPE: Header for chain variable subject token type
        X_CHAIN_VAR_SAML_PROVIDER_DESTINATION_NAME: Header for chain variable SAML provider destination name
    """

    X_DESTINATION_NAME = "X-destination-name"
    AUTHORIZATION = "Authorization"
    X_FRAGMENT_NAME = "x-fragment-name"
    X_TENANT_SUBDOMAIN = "x-tenant-subdomain"
    X_TENANT_ID = "x-tenant-id"
    X_FRAGMENT_OPTIONAL = "x-fragment-optional"
    X_DESTINATION_LEVEL = "x-destination-level"
    X_FRAGMENT_LEVEL = "x-fragment-level"
    X_TOKEN_SERVICE_TENANT = "x-token-service-tenant"
    X_CLIENT_ASSERTION = "x-client-assertion"
    X_CLIENT_ASSERTION_TYPE = "x-client-assertion-type"
    X_CLIENT_ASSERTION_DESTINATION_NAME = "x-client-assertion-destination-name"
    X_SUBJECT_TOKEN_TYPE = "x-subject-token-type"
    X_ACTOR_TOKEN = "x-actor-token"
    X_ACTOR_TOKEN_TYPE = "x-actor-token-type"
    X_REDIRECT_URI = "x-redirect-uri"
    X_CODE_VERIFIER = "x-code-verifier"
    X_CHAIN_NAME = "x-chain-name"
    X_CHAIN_VAR_SUBJECT_TOKEN = "x-chain-var-subjectToken"
    X_CHAIN_VAR_SUBJECT_TOKEN_TYPE = "x-chain-var-subjectTokenType"
    X_CHAIN_VAR_SAML_PROVIDER_DESTINATION_NAME = (
        "x-chain-var-samlProviderDestinationName"
    )


@dataclass
class TransparentProxy:
    """Transparent Proxy configuration for Destination Client.

    Fields:
        proxy_name: The proxy name for the transparent proxy (required)
        namespace: The namespace associated with the transparent proxy (required)
    """

    proxy_name: str
    namespace: str


@dataclass
class TransparentProxyDestination:
    """Destination entity with Transparent Proxy configuration.

    Fields:
        name: Destination name (required)
        url: Proxy URL (required)
        headers: Headers required for Transparent Proxy access (required)
    """

    name: str
    url: str
    headers: Dict[str, str]

    @staticmethod
    def from_proxy(
        name: str, transparent_proxy: Optional[TransparentProxy] = None
    ) -> "TransparentProxyDestination":
        """Create a TransparentProxyDestination from TransparentProxy configuration.

        Args:
            name: Destination name.
            transparent_proxy: TransparentProxy configuration.
        Returns:
            TransparentProxyDestination: Created destination with transparent proxy settings.

        Raises:
            DestinationOperationError: If transparent_proxy is missing.
        """
        if transparent_proxy is None:
            raise DestinationOperationError(
                "transparent_proxy configuration is required but not provided"
            )

        headers: Dict[str, str] = {
            TransparentProxyHeader.X_DESTINATION_NAME.value: name
        }
        url = "http://{}.{}".format(
            transparent_proxy.proxy_name, transparent_proxy.namespace
        )

        return TransparentProxyDestination(name, url, headers)

    def set_header(self, header: TransparentProxyHeader, value: str) -> None:
        """Set a header for the transparent proxy destination.

        Args:
            header: The header to set (from TransparentProxyHeader enum).
            value: The value for the header.

        Example:
            ```python
            dest = TransparentProxyDestination.from_proxy("my-dest", proxy_config)
            dest.set_header(TransparentProxyHeader.AUTHORIZATION, "Bearer token")
            ```
        """
        self.headers[header.value] = value
