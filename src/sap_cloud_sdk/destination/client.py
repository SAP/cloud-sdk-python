"""Destination client implementation."""

from __future__ import annotations

from typing import List, Optional, Callable, TypeVar

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.destination._http import DestinationHttp, API_V1, API_V2
from sap_cloud_sdk.destination._models import (
    AccessStrategy,
    ConsumptionOptions,
    Destination,
    Label,
    Level,
    ListOptions,
    PatchLabels,
    TransparentProxy,
    TransparentProxyDestination,
)
from sap_cloud_sdk.destination.config import load_transparent_proxy
from sap_cloud_sdk.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)
from sap_cloud_sdk.destination.utils._pagination import (
    PagedResult,
    parse_pagination_headers,
)

T = TypeVar("T")

_SUBACCOUNT_COLLECTION = "subaccountDestinations"
_INSTANCE_COLLECTION = "instanceDestinations"

_SUBACCOUNT_LEVEL = "subaccount"
_INSTANCE_LEVEL = "instance"


class DestinationClient:
    """Client for SAP Destination Service operations.

    This class exposes read and write operations for destinations at both
    subaccount and instance levels. It expects a configured DestinationHttp
    instance injected via the constructor.

    Note:
        Do not instantiate DestinationClient directly. Use create_client() from
        sap_cloud_sdk.destination instead, which handles environment detection,
        secret resolution and OAuth setup.

    Example:
        ```python
        from sap_cloud_sdk.destination import create_client, Level, AccessStrategy, Destination, ListOptions

        client = create_client(instance="my-instance", use_default_proxy=False)

        # List all instance-level destinations
        destinations = client.list_instance_destinations()

        # List with filters - filter by specific names
        filter_obj = ListOptions(filter_names=["dest1", "dest2"])
        destinations = client.list_instance_destinations(filter=filter_obj)

        # List with pagination
        filter_obj = ListOptions(page=1, page_size=10, page_count=True)
        destinations = client.list_subaccount_destinations(
            access_strategy=AccessStrategy.PROVIDER_ONLY,
            filter=filter_obj
        )


        # List all subaccount-level destinations using subscriber-first strategy
        destinations = client.list_subaccount_destinations(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="tenant-subdomain"
        )

        # Read an instance-level destination
        dest = client.get_instance_destination("my-destination")

        # Read a subaccount-level destination using subscriber-first strategy
        dest = client.get_subaccount_destination(
            name="my-destination",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="tenant-subdomain"
        )

        # Create a destination at subaccount level
        new_dest = Destination(name="new-destination", type="HTTP", url="https://api.example.com")
        created = client.create_destination(new_dest, level=Level.SUB_ACCOUNT)
        ```
    """

    def __init__(self, http: DestinationHttp, use_default_proxy: bool = False) -> None:
        """Initialize DestinationClient with dependency injection.

        Note:
            Do not call this constructor directly. Use create_client() from
            sap_cloud_sdk.destination instead, which properly configures
            the HTTP transport and handles environment detection.

        Args:
            http: Configured HTTP transport for the Destination Service.
            use_default_proxy: Whether to use the default transparent proxy for all get operations.
                              When True, will attempt to load transparent proxy configuration from
                              APPFND_CONHOS_TRANSP_PROXY environment variable. Defaults to False.

        Raises:
            DestinationOperationError: If initialization fails.
        """
        self._http = http
        self._client_proxy_enabled = use_default_proxy
        self._transparent_proxy = load_transparent_proxy()

    def set_proxy(self, transparent_proxy: TransparentProxy) -> None:
        """Set or update the transparent proxy configuration for this client.

        Args:
            transparent_proxy: TransparentProxy configuration to use.
        """
        self._transparent_proxy = transparent_proxy
        self._client_proxy_enabled = True

    # ---------- Read operations ----------

    @record_metrics(
        Module.DESTINATION, Operation.DESTINATION_LIST_INSTANCE_DESTINATIONS
    )
    def list_instance_destinations(
        self, filter: Optional[ListOptions] = None
    ) -> PagedResult[Destination]:
        """List all destinations from the service instance scope.

        Args:
            filter: Optional filter configuration for pagination, filtering, or metadata inclusion.

        Returns:
            PagedResult[Destination] containing destinations and pagination info.
            Pagination info will be None if pagination parameters were not provided.
            Returns empty items list if no destinations are found.

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            return self._list_destinations(
                level=Level.SERVICE_INSTANCE, tenant_subdomain=None, filter=filter
            )
        except HttpError as e:
            raise DestinationOperationError(
                f"failed to list instance destinations: {e}"
            )

    @record_metrics(
        Module.DESTINATION, Operation.DESTINATION_LIST_SUBACCOUNT_DESTINATIONS
    )
    def list_subaccount_destinations(
        self,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
        filter: Optional[ListOptions] = None,
    ) -> PagedResult[Destination]:
        """List all destinations from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: Fetch only from subscriber context (tenant required)
            - PROVIDER_ONLY: Fetch only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: Try subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: Try provider first, fallback to subscriber (tenant required)

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            filter: Optional filter configuration for pagination, filtering, or metadata inclusion.

        Returns:
            PagedResult[Destination] containing destinations and pagination info.
            Pagination info will be None if pagination parameters were not provided.

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       on HTTP errors, or response parsing failures.
        """
        try:
            return self._apply_access_strategy(
                access_strategy=access_strategy,
                tenant=tenant,
                fetch_func=lambda t: self._list_destinations(
                    level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=filter
                ),
            )
        except HttpError as e:
            raise DestinationOperationError(
                f"failed to list subaccount destinations: {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_GET_INSTANCE_DESTINATION)
    def get_instance_destination(
        self, name: str, proxy_enabled: Optional[bool] = None
    ) -> Optional[Destination | TransparentProxyDestination]:
        """Get a destination from the service instance scope.

        Args:
            name: Destination name.
            proxy_enabled: Whether to route the request through a transparent proxy (if configured).
                          If None, uses the client's default proxy_enabled setting.

        Returns:
            Destination if found, otherwise None (when HTTP 404 occurs).

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            if self._should_use_proxy(proxy_enabled):
                return TransparentProxyDestination.from_proxy(
                    name=name, transparent_proxy=self._transparent_proxy
                )

            return self._get_destination(
                name=name, tenant_subdomain=None, level=Level.SERVICE_INSTANCE
            )
        except HttpError as e:
            raise DestinationOperationError(f"failed to get destination '{name}': {e}")

    @record_metrics(
        Module.DESTINATION, Operation.DESTINATION_GET_SUBACCOUNT_DESTINATION
    )
    def get_subaccount_destination(
        self,
        name: str,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
        proxy_enabled: Optional[bool] = None,
    ) -> Optional[Destination | TransparentProxyDestination]:
        """Get a destination from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: Fetch only from subscriber context (tenant required)
            - PROVIDER_ONLY: Fetch only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: Try subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: Try provider first, fallback to subscriber (tenant required)

        Args:
            name: Destination name.
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            proxy_enabled: Whether to route the request through a transparent proxy (if configured).
                          If None, uses the client's default proxy_enabled setting.

        Returns:
            Destination if found, otherwise None (after trying configured precedence).

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       on HTTP errors, or response parsing failures.
        """
        try:
            if self._should_use_proxy(proxy_enabled) and self._transparent_proxy:
                return TransparentProxyDestination.from_proxy(
                    name=name, transparent_proxy=self._transparent_proxy
                )

            return self._apply_access_strategy(
                access_strategy=access_strategy,
                tenant=tenant,
                fetch_func=lambda t: self._get_destination(
                    name=name, tenant_subdomain=t, level=Level.SUB_ACCOUNT
                ),
            )
        except HttpError as e:
            raise DestinationOperationError(f"failed to get destination '{name}': {e}")

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_GET_DESTINATION)
    def get_destination(
        self,
        name: str,
        level: Optional[Level] = None,
        options: Optional[ConsumptionOptions] = None,
        proxy_enabled: Optional[bool] = None,
    ) -> Optional[Destination | TransparentProxyDestination]:
        """Consume a destination using the v2 runtime API.

        This method calls the v2 consumption API which automatically:
        - Searches for destination in hierarchy
        - Retrieves and caches authentication tokens
        - Merges fragment properties if options.fragment_name is provided

        The returned Destination object includes auth_tokens and certificates fields
        populated by the v2 API.

        Args:
            name: Destination name.
            level: Optional level hint (subaccount or instance) to optimize lookup. If not
                provided, the API will search on instance level.
            options: Optional ConsumptionOptions controlling request headers sent to the
                Destination Service. See ConsumptionOptions for the full list of supported
                headers (fragment merging, token exchange, SAML, OAuth2 flows, chains, etc.).
            proxy_enabled: Whether to route the request through a transparent proxy (if
                configured). If None, uses the client's default proxy_enabled setting.

        Returns:
            Destination with auth_tokens and certificates populated from v2 API,
            or TransparentProxyDestination if proxy is enabled.
            Returns None if destination is not found (HTTP 404).

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.

        Example:
            ```python
            from sap_cloud_sdk.destination import create_client, ConsumptionOptions, Level

            client = create_client()

            # Simple consumption
            dest = client.get_destination("my-api")

            # With level hint
            dest = client.get_destination("my-api", level=Level.SERVICE_INSTANCE)

            # Fragment merging
            dest = client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod"))

            # Optional fragment (no error if fragment not found)
            dest = client.get_destination(
                "my-api",
                options=ConsumptionOptions(fragment_name="prod", fragment_optional=True),
            )

            # Tenant context
            dest = client.get_destination("my-api", options=ConsumptionOptions(tenant="tenant-1"))

            # User token exchange (OAuth2UserTokenExchange / OAuth2JWTBearer)
            dest = client.get_destination(
                "my-api",
                options=ConsumptionOptions(user_token="<jwt>", tenant="tenant-1"),
            )

            # With transparent proxy enabled
            dest = client.get_destination("my-api", proxy_enabled=True)
            ```
        """
        try:
            if self._should_use_proxy(proxy_enabled):
                return TransparentProxyDestination.from_proxy(
                    name=name, transparent_proxy=self._transparent_proxy
                )

            headers = {}

            if options:
                if options.fragment_name:
                    headers["X-fragment-name"] = options.fragment_name
                if options.fragment_optional is not None:
                    headers["X-fragment-optional"] = str(
                        options.fragment_optional
                    ).lower()
                if options.tenant:
                    headers["X-tenant"] = options.tenant
                if options.user_token:
                    headers["X-user-token"] = options.user_token
                if options.subject_token:
                    headers["X-subject-token"] = options.subject_token
                if options.subject_token_type:
                    headers["X-subject-token-type"] = options.subject_token_type
                if options.actor_token:
                    headers["X-actor-token"] = options.actor_token
                if options.actor_token_type:
                    headers["X-actor-token-type"] = options.actor_token_type
                if options.saml_assertion:
                    headers["X-samlAssertion"] = options.saml_assertion
                if options.refresh_token:
                    headers["X-refresh-token"] = options.refresh_token
                if options.code:
                    headers["X-code"] = options.code
                if options.redirect_uri:
                    headers["X-redirect-uri"] = options.redirect_uri
                if options.code_verifier:
                    headers["X-code-verifier"] = options.code_verifier
                if options.chain_name:
                    headers["X-chain-name"] = options.chain_name
                if options.chain_vars:
                    for var_name, var_value in options.chain_vars.items():
                        headers[f"X-chain-var-{var_name}"] = var_value

            # Build path with optional level hint
            if level:
                level_str = self._map_level_to_api(level)
                path = f"{API_V2}/destinations/{name}@{level_str}"
            else:
                path = f"{API_V2}/destinations/{name}"

            resp = self._http.get(path, headers=headers)
            data = resp.json()

            # Parse v2 response: destinationConfiguration + authTokens + certificates
            dest_config = data.get("destinationConfiguration")
            if not dest_config:
                raise DestinationOperationError(
                    "missing destinationConfiguration in v2 response"
                )

            # Add runtime data to the response for parsing
            dest_config["authTokens"] = data.get("authTokens", [])
            dest_config["certificates"] = data.get("certificates", [])

            return Destination.from_dict(dest_config, include_runtime_data=True)
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return None
            raise DestinationOperationError(
                f"failed to consume destination '{name}': {e}"
            )
        except Exception as e:
            raise DestinationOperationError(
                f"failed to parse consume destination response: {e}"
            )

    # ---------- Write operations ----------

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_CREATE_DESTINATION)
    def create_destination(
        self,
        dest: Destination,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Create a destination.

        Args:
            dest: Destination entity to create.
            level: Scope where the destination should be created (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the destination is created in the
                subscriber context; otherwise the provider context is used.

        Returns:
            None. Success responses from the Destination Service return an empty body.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)
        body = dest.to_dict()

        try:
            self._http.post(f"{API_V1}/{coll}", body=body, tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to create destination '{dest.name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_UPDATE_DESTINATION)
    def update_destination(
        self,
        dest: Destination,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Update a destination.

        Args:
            dest: Destination entity with updated fields.
            level: Scope where the destination exists (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the destination is updated in the
                subscriber context; otherwise the provider context is used.

        Returns:
            None. Success responses from the Destination Service return an Update object (e.g., {"Count": 1}),
            not the full destination. The HTTP layer will raise for non-2xx responses.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)
        body = dest.to_dict()

        try:
            self._http.put(f"{API_V1}/{coll}", body=body, tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to update destination '{dest.name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_DELETE_DESTINATION)
    def delete_destination(
        self,
        name: str,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Delete a destination.

        Args:
            name: Destination name.
            level: Scope where the destination exists (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the destination is deleted in the
                subscriber context; otherwise the provider context is used.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)

        try:
            self._http.delete(f"{API_V1}/{coll}/{name}", tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to delete destination '{name}': {e}"
            )

    # ---------- Label operations ----------

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_GET_LABELS)
    def get_destination_labels(
        self,
        name: str,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> List[Label]:
        """Get labels for a destination.

        Args:
            name: Destination name.
            level: Scope to query (subaccount by default).
            tenant: Optional subscriber tenant subdomain. If provided, the request is scoped to that tenant.

        Returns:
            List of labels assigned to the destination. Returns empty list if none assigned.

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            path = self._sub_path_for_level(level)
            resp = self._http.get(f"{API_V1}/{path}/{name}/labels", tenant_subdomain=tenant)
            data = resp.json()
            if not isinstance(data, list):
                raise DestinationOperationError(
                    f"expected list in labels response, got {type(data)}"
                )
            return [Label.from_dict(item) for item in data]
        except HttpError as e:
            raise DestinationOperationError(
                f"failed to get labels for destination '{name}': {e}"
            )
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"invalid JSON in get labels response: {e}")

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_UPDATE_LABELS)
    def update_destination_labels(
        self,
        name: str,
        labels: List[Label],
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Replace all labels for a destination.

        Args:
            name: Destination name.
            labels: List of labels to set (replaces existing labels).
            level: Scope where the destination exists (subaccount by default).
            tenant: Optional subscriber tenant subdomain. If provided, the request is scoped to that tenant.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        resolved_level = level or Level.SUB_ACCOUNT
        try:
            path = self._sub_path_for_level(resolved_level)
            self._http.put(
                f"{API_V1}/{path}/{name}/labels",
                body=[lbl.to_dict() for lbl in labels],
                tenant_subdomain=tenant,
            )
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to put labels for destination '{name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.DESTINATION_PATCH_LABELS)
    def patch_destination_labels(
        self,
        name: str,
        patch: PatchLabels,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Add or remove labels for a destination.

        Args:
            name: Destination name.
            patch: PatchLabels with action ("ADD" or "DELETE") and labels to apply.
            level: Scope where the destination exists (subaccount by default).
            tenant: Optional subscriber tenant subdomain. If provided, the request is scoped to that tenant.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        resolved_level = level or Level.SUB_ACCOUNT
        try:
            path = self._sub_path_for_level(resolved_level)
            self._http.patch(
                f"{API_V1}/{path}/{name}/labels",
                body=patch.to_dict(),
                tenant_subdomain=tenant,
            )
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to patch labels for destination '{name}': {e}"
            )

    # ---------- Internal helpers ----------

    def _get_destination(
        self,
        name: str,
        tenant_subdomain: Optional[str] = None,
        level: Optional[Level] = Level.SUB_ACCOUNT,
    ) -> Optional[Destination]:
        """Internal helper to fetch a destination with optional tenant context.

        Args:
            name: Destination name.
            tenant_subdomain: Subscriber tenant subdomain, if fetching in subscriber context.
            level: Scope to query (subaccount by default).

        Returns:
            Destination if found, otherwise None (for HTTP 404).

        Raises:
            HttpError: Propagated for non-404 HTTP errors.
            DestinationOperationError: If response JSON is invalid.
        """
        try:
            path = self._sub_path_for_level(level)
            resp = self._http.get(
                f"{API_V1}/{path}/{name}", tenant_subdomain=tenant_subdomain
            )
            data = resp.json()

            return Destination.from_dict(data)
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return None
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"invalid JSON in get destination response: {e}"
            )

    def _list_destinations(
        self,
        level: Level,
        tenant_subdomain: Optional[str] = None,
        filter: Optional[ListOptions] = None,
    ) -> PagedResult[Destination]:
        """Internal helper to list destinations with optional tenant context and filters.

        Args:
            level: Scope to query (subaccount or service instance).
            tenant_subdomain: Subscriber tenant subdomain, if fetching in subscriber context.
            filter: Optional filter configuration for pagination, filtering, or metadata inclusion.

        Returns:
            PagedResult[Destination] containing destinations and pagination info.
            Pagination info will be None if pagination parameters were not provided.
            Returns empty items list if no destinations are found.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: If response JSON is invalid.
        """
        try:
            path = self._sub_path_for_level(level)
            query_params = filter.to_query_params() if filter else {}
            resp = self._http.get(
                f"{API_V1}/{path}",
                tenant_subdomain=tenant_subdomain,
                params=query_params,
            )
            data = resp.json()

            if not isinstance(data, list):
                raise DestinationOperationError(
                    f"expected list in response, got {type(data).__name__}"
                )

            # Parse destinations, skipping any with missing required fields
            destinations = []
            for item in data:
                try:
                    destinations.append(Destination.from_dict(item))
                except DestinationOperationError:
                    # Skip destinations that don't have required fields (e.g., missing type)
                    # This can happen when the API returns fragments or other non-destination entities
                    continue

            # Always parse pagination headers (will be None if not present)
            pagination_info = parse_pagination_headers(resp)

            return PagedResult(items=destinations, pagination=pagination_info)
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return PagedResult(items=[])
            raise
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"invalid JSON in list destinations response: {e}"
            )

    def _should_use_proxy(self, proxy_enabled: Optional[bool]) -> bool:
        """Determine whether to use proxy based on provided parameter or client default.

        Args:
            proxy_enabled: Explicit proxy setting, or None to use client default.

        Returns:
            True if proxy should be used, False otherwise.
        """
        return (
            proxy_enabled if proxy_enabled is not None else self._client_proxy_enabled
        )

    @staticmethod
    def _apply_access_strategy(
        access_strategy: AccessStrategy,
        tenant: Optional[str],
        fetch_func: Callable[[Optional[str]], T],
    ) -> T:
        """Apply access strategy pattern for fetching resources from subaccount scope.

        This generic method handles the access strategy logic (subscriber/provider precedence)
        to eliminate duplication between get and list operations.

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            fetch_func: Function that fetches the resource given a tenant_subdomain (or None for provider).

        Returns:
            The fetched resource (type T).

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies.
        """
        subscriber_access = [
            AccessStrategy.SUBSCRIBER_ONLY,
            AccessStrategy.SUBSCRIBER_FIRST,
            AccessStrategy.PROVIDER_FIRST,
        ]

        if access_strategy in subscriber_access and tenant is None:
            raise DestinationOperationError(
                "tenant subdomain must be provided for subscriber access. "
                "If you want to access provider destinations only, use AccessStrategy.PROVIDER_ONLY."
            )

        def is_empty(value: T) -> bool:
            """Check if value is empty, handling PagedResult objects."""
            if isinstance(value, PagedResult):
                return len(value.items) == 0

            return value is None

        match access_strategy:
            case AccessStrategy.SUBSCRIBER_ONLY:
                return fetch_func(tenant)
            case AccessStrategy.PROVIDER_ONLY:
                return fetch_func(None)
            case AccessStrategy.SUBSCRIBER_FIRST:
                result = fetch_func(tenant)
                if is_empty(result):
                    result = fetch_func(None)
                return result
            case AccessStrategy.PROVIDER_FIRST:
                result = fetch_func(None)
                if is_empty(result):
                    result = fetch_func(tenant)
                return result
            case _:
                raise DestinationOperationError(
                    f"unknown access strategy: {access_strategy}"
                )

    @staticmethod
    def _sub_path_for_level(level: Optional[Level] = Level.SUB_ACCOUNT) -> str:
        """Return API sub-path for the given level."""
        return (
            _INSTANCE_COLLECTION
            if level == Level.SERVICE_INSTANCE
            else _SUBACCOUNT_COLLECTION
        )

    @staticmethod
    def _map_level_to_api(level: Level) -> str:
        """Return the v2 API level string for the given level."""
        return _INSTANCE_LEVEL if level == Level.SERVICE_INSTANCE else _SUBACCOUNT_LEVEL
