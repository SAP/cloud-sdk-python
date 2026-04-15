"""Fragment client implementation."""

from __future__ import annotations

from typing import Callable, List, Optional, TypeVar

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.destination._http import DestinationHttp, API_V1
from sap_cloud_sdk.destination._models import (
    AccessStrategy,
    Fragment,
    Label,
    Level,
    ListOptions,
    PatchLabels,
)
from sap_cloud_sdk.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)

T = TypeVar("T")

_SUBACCOUNT_COLLECTION = "subaccountDestinationFragments"
_INSTANCE_COLLECTION = "instanceDestinationFragments"


class FragmentClient:
    """Client for SAP Destination Service Fragment operations.

    This class exposes read and write operations for destination fragments at both
    subaccount and instance levels. Fragments are used to override and/or extend
    destination properties. It expects a configured DestinationHttp instance injected
    via the constructor.

    Note:
        Do not instantiate FragmentClient directly. Use create_fragment_client() instead,
        which handles environment detection, secret resolution and OAuth setup.

    Example:
        ```python
        from sap_cloud_sdk.destination import create_client, Level
        from sap_cloud_sdk.destination._models import Fragment

        # Recommended: use the factory which configures OAuth/HTTP from environment
        client = create_fragment_client()

        # Read an instance-level fragment
        fragment = client.get_instance_fragment("my-fragment")

        # Read a subaccount-level fragment
        fragment = client.get_subaccount_fragment("my-fragment")

        # Create a fragment at subaccount level
        new_fragment = Fragment(name="new-fragment", properties={"URL": "https://api.example.com"})
        created = client.create_fragment(new_fragment, level=Level.SUB_ACCOUNT)
        ```
    """

    def __init__(self, http: DestinationHttp) -> None:
        """Initialize FragmentClient with dependency injection.

        Args:
            http: Configured HTTP transport for the Destination Service.

        Raises:
            DestinationOperationError: If initialization fails.
        """
        self._http = http

    # ---------- Read operations ----------

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_GET_INSTANCE_FRAGMENT)
    def get_instance_fragment(self, name: str) -> Optional[Fragment]:
        """Get a fragment from the service instance scope.

        Args:
            name: Fragment name.

        Returns:
            Fragment if found, otherwise None (when HTTP 404 occurs).

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            return self._get_fragment(name=name, level=Level.SERVICE_INSTANCE)
        except HttpError as e:
            raise DestinationOperationError(f"failed to get fragment '{name}': {e}")

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_GET_SUBACCOUNT_FRAGMENT)
    def get_subaccount_fragment(
        self,
        name: str,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
    ) -> Optional[Fragment]:
        """Get a fragment from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: Fetch only from subscriber context (tenant required)
            - PROVIDER_ONLY: Fetch only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: Try subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: Try provider first, fallback to subscriber (tenant required)

        Args:
            name: Fragment name.
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.

        Returns:
            Fragment if found, otherwise None (after trying configured precedence).

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       on HTTP errors, or response parsing failures.
        """
        try:
            return self._apply_access_strategy(
                access_strategy=access_strategy,
                tenant=tenant,
                fetch_func=lambda t: self._get_fragment(
                    name=name, tenant_subdomain=t, level=Level.SUB_ACCOUNT
                ),
                empty_value=None,
            )
        except HttpError as e:
            raise DestinationOperationError(f"failed to get fragment '{name}': {e}")

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_LIST_INSTANCE_FRAGMENTS)
    def list_instance_fragments(
        self,
        filter: Optional[ListOptions] = None,
    ) -> List[Fragment]:
        """List all fragments from the service instance scope.

        Args:
            filter: Optional filter configuration for label filtering.

        Returns:
            List of fragments. Returns empty list if no fragments exist.

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            return self._list_fragments(level=Level.SERVICE_INSTANCE, filter=filter)
        except HttpError as e:
            raise DestinationOperationError(f"failed to list instance fragments: {e}")

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_LIST_SUBACCOUNT_FRAGMENTS)
    def list_subaccount_fragments(
        self,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
        filter: Optional[ListOptions] = None,
    ) -> List[Fragment]:
        """List fragments from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: Fetch only from subscriber context (tenant required)
            - PROVIDER_ONLY: Fetch only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: Try subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: Try provider first, fallback to subscriber (tenant required)

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            filter: Optional filter configuration for label filtering.

        Returns:
            List of fragments (after trying configured precedence). Returns empty list if no fragments exist.

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       on HTTP errors, or response parsing failures.
        """
        try:
            return self._apply_access_strategy(
                access_strategy=access_strategy,
                tenant=tenant,
                fetch_func=lambda t: self._list_fragments(
                    level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=filter
                ),
                empty_value=[],
            )
        except HttpError as e:
            raise DestinationOperationError(f"failed to list subaccount fragments: {e}")

    # ---------- Write operations ----------

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_CREATE_FRAGMENT)
    def create_fragment(
        self,
        fragment: Fragment,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Create a fragment.

        Args:
            fragment: Fragment entity to create.
            level: Scope where the fragment should be created (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the fragment is created in the
                subscriber context; otherwise the provider context is used.

        Returns:
            None. Success responses from the Destination Service return an empty body.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)
        body = fragment.to_dict()

        try:
            self._http.post(f"{API_V1}/{coll}", body=body, tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to create fragment '{fragment.name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_UPDATE_FRAGMENT)
    def update_fragment(
        self,
        fragment: Fragment,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Update a fragment.

        Args:
            fragment: Fragment entity with updated fields.
            level: Scope where the fragment exists (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the fragment is updated in the
                subscriber context; otherwise the provider context is used.

        Returns:
            None. Success responses from the Destination Service return an Update object (e.g., {"Count": 1}),
            not the full fragment. The HTTP layer will raise for non-2xx responses.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)
        body = fragment.to_dict()

        try:
            self._http.put(f"{API_V1}/{coll}", body=body, tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to update fragment '{fragment.name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_DELETE_FRAGMENT)
    def delete_fragment(
        self,
        name: str,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Delete a fragment.

        Args:
            name: Fragment name.
            level: Scope where the fragment exists (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the fragment is deleted in the
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
            raise DestinationOperationError(f"failed to delete fragment '{name}': {e}")

    # ---------- Label operations ----------

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_GET_LABELS)
    def get_fragment_labels(
        self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> List[Label]:
        """Get labels for a fragment.

        Args:
            name: Fragment name.
            level: Scope to query (subaccount by default).

        Returns:
            List of labels assigned to the fragment. Returns empty list if none assigned.

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            path = self._sub_path_for_level(level)
            resp = self._http.get(f"{API_V1}/{path}/{name}/labels")
            data = resp.json()
            if not isinstance(data, list):
                raise DestinationOperationError(
                    f"expected list in labels response, got {type(data)}"
                )
            return [Label.from_dict(item) for item in data]
        except HttpError as e:
            raise DestinationOperationError(
                f"failed to get labels for fragment '{name}': {e}"
            )
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"invalid JSON in get labels response: {e}")

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_UPDATE_LABELS)
    def update_fragment_labels(
        self, name: str, labels: List[Label], level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Replace all labels for a fragment.

        Args:
            name: Fragment name.
            labels: List of labels to set (replaces existing labels).
            level: Scope where the fragment exists (subaccount by default).

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
            )
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to put labels for fragment '{name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.FRAGMENT_PATCH_LABELS)
    def patch_fragment_labels(
        self, name: str, patch: PatchLabels, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Add or remove labels for a fragment.

        Args:
            name: Fragment name.
            patch: PatchLabels with action ("ADD" or "DELETE") and labels to apply.
            level: Scope where the fragment exists (subaccount by default).

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
            )
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to patch labels for fragment '{name}': {e}"
            )

    # ---------- Internal helpers ----------

    def _get_fragment(
        self,
        name: str,
        tenant_subdomain: Optional[str] = None,
        level: Optional[Level] = Level.SUB_ACCOUNT,
    ) -> Optional[Fragment]:
        """Internal helper to fetch a fragment with optional tenant context.

        Args:
            name: Fragment name.
            tenant_subdomain: Subscriber tenant subdomain, if fetching in subscriber context.
            level: Scope to query (subaccount by default).

        Returns:
            Fragment if found, otherwise None (for HTTP 404).

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

            return Fragment.from_dict(data)
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return None
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"invalid JSON in get fragment response: {e}"
            )

    def _list_fragments(
        self,
        level: Level,
        tenant_subdomain: Optional[str] = None,
        filter: Optional[ListOptions] = None,
    ) -> List[Fragment]:
        """Internal helper to list fragments with optional tenant context and filters.

        Args:
            level: Scope to query (service instance or subaccount).
            tenant_subdomain: Subscriber tenant subdomain, if fetching in subscriber context.
            filter: Optional filter configuration for label filtering.

        Returns:
            List of fragments. Returns empty list if no fragments exist.

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
                    f"expected list in response, got {type(data)}"
                )

            return [Fragment.from_dict(item) for item in data]
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return []
            raise
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"invalid JSON in list fragments response: {e}"
            )

    def _apply_access_strategy(
        self,
        access_strategy: AccessStrategy,
        tenant: Optional[str],
        fetch_func: Callable[[Optional[str]], T],
        empty_value: T,
    ) -> T:
        """Apply access strategy pattern for fetching resources.

        This generic helper implements the access strategy logic for both get and list operations,
        eliminating code duplication.

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain (required for subscriber access strategies).
            fetch_func: Function to fetch the resource, takes tenant_subdomain as parameter.
            empty_value: Value representing "empty" result (None for get, [] for list).

        Returns:
            Result from fetch_func based on access strategy (could be single resource or list).

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       or for unknown access strategies.
        """
        subscriber_access = [
            AccessStrategy.SUBSCRIBER_ONLY,
            AccessStrategy.SUBSCRIBER_FIRST,
            AccessStrategy.PROVIDER_FIRST,
        ]

        if access_strategy in subscriber_access and tenant is None:
            raise DestinationOperationError(
                "tenant subdomain must be provided for subscriber access. "
                "If you want to access provider resources only, use AccessStrategy.PROVIDER_ONLY."
            )

        match access_strategy:
            case AccessStrategy.SUBSCRIBER_ONLY:
                return fetch_func(tenant)
            case AccessStrategy.PROVIDER_ONLY:
                return fetch_func(None)
            case AccessStrategy.SUBSCRIBER_FIRST:
                result = fetch_func(tenant)
                if result == empty_value:
                    result = fetch_func(None)
                return result
            case AccessStrategy.PROVIDER_FIRST:
                result = fetch_func(None)
                if result == empty_value:
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
