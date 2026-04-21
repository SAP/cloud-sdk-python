"""Certificate client implementation."""

from __future__ import annotations

from typing import List, Optional, TypeVar, Callable

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.destination._http import DestinationHttp, API_V1
from sap_cloud_sdk.destination._models import (
    AccessStrategy,
    Certificate,
    Label,
    Level,
    ListOptions,
    PatchLabels,
)
from sap_cloud_sdk.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)
from sap_cloud_sdk.destination.utils._pagination import (
    PagedResult,
    parse_pagination_headers,
)

_SUBACCOUNT_COLLECTION = "subaccountCertificates"
_INSTANCE_COLLECTION = "instanceCertificates"

T = TypeVar("T")


class CertificateClient:
    """Client for SAP Destination Service Certificate operations.

    This class exposes read and write operations for certificates at both
    subaccount and instance levels. Certificates are used to store keystores
    and certificates for mTLS and other authentication mechanisms. It expects
    a configured DestinationHttp instance injected via the constructor.

    Note:
        Do not instantiate CertificateClient directly. Use create_certificate_client() instead,
        which handles environment detection, secret resolution and OAuth setup.

    Example:
        ```python
        from sap_cloud_sdk.destination import create_certificate_client, Level
        from sap_cloud_sdk.destination._models import Certificate

        # Recommended: use the factory which configures OAuth/HTTP from environment
        client = create_certificate_client()

        # Read an instance-level certificate
        cert = client.get_instance_certificate("my-cert")

        # Read a subaccount-level certificate
        cert = client.get_subaccount_certificate("my-cert")

        # Create a certificate at subaccount level
        new_cert = Certificate(name="new-cert.pem", content="base64-encoded-content", type="PEM")
        created = client.create_certificate(new_cert, level=Level.SUB_ACCOUNT)
        ```
    """

    def __init__(self, http: DestinationHttp) -> None:
        """Initialize CertificateClient with dependency injection.

        Args:
            http: Configured HTTP transport for the Destination Service.

        Raises:
            DestinationOperationError: If initialization fails.
        """
        self._http = http

    # ---------- Read operations ----------

    @record_metrics(
        Module.DESTINATION, Operation.CERTIFICATE_LIST_INSTANCE_CERTIFICATES
    )
    def list_instance_certificates(
        self,
        filter: Optional[ListOptions] = None,
    ) -> PagedResult[Certificate]:
        """List all certificates at the service instance level.

        Args:
            filter: Optional filter configuration for query parameters.

        Returns:
            PagedResult[Certificate] containing certificates and pagination info.
            Pagination info will be None if pagination parameters were not provided.
            Returns empty items list if none found.

        Raises:
            DestinationOperationError: If HTTP error occurs or response parsing fails.
        """
        try:
            return self._list_certificates(level=Level.SERVICE_INSTANCE, filter=filter)
        except HttpError as e:
            raise DestinationOperationError(
                f"failed to list instance certificates: {e}"
            )

    @record_metrics(
        Module.DESTINATION, Operation.CERTIFICATE_LIST_SUBACCOUNT_CERTIFICATES
    )
    def list_subaccount_certificates(
        self,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
        filter: Optional[ListOptions] = None,
    ) -> PagedResult[Certificate]:
        """List certificates at subaccount level with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: List only from subscriber context (tenant required)
            - PROVIDER_ONLY: List only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: Try subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: Try provider first, fallback to subscriber (tenant required)

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            filter: Optional filter configuration for query parameters.

        Returns:
            PagedResult[Certificate] containing certificates and pagination info.
            Pagination info will be None if pagination parameters were not provided.

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       on HTTP errors, or response parsing failures.
        """
        try:
            return self._apply_access_strategy(
                access_strategy=access_strategy,
                tenant=tenant,
                fetch_func=lambda t: self._list_certificates(
                    level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=filter
                ),
            )
        except HttpError as e:
            raise DestinationOperationError(
                f"failed to list subaccount certificates: {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_GET_INSTANCE_CERTIFICATE)
    def get_instance_certificate(self, name: str) -> Optional[Certificate]:
        """Get a certificate from the service instance scope.

        Args:
            name: Certificate name.

        Returns:
            Certificate if found, otherwise None (when HTTP 404 occurs).

        Raises:
            DestinationOperationError: If an HTTP error occurs or response parsing fails.
        """
        try:
            return self._get_certificate(name=name, level=Level.SERVICE_INSTANCE)
        except HttpError as e:
            raise DestinationOperationError(f"failed to get certificate '{name}': {e}")

    @record_metrics(
        Module.DESTINATION, Operation.CERTIFICATE_GET_SUBACCOUNT_CERTIFICATE
    )
    def get_subaccount_certificate(
        self,
        name: str,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
    ) -> Optional[Certificate]:
        """Get a certificate from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: Fetch only from subscriber context (tenant required)
            - PROVIDER_ONLY: Fetch only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: Try subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: Try provider first, fallback to subscriber (tenant required)

        Args:
            name: Certificate name.
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.

        Returns:
            Certificate if found, otherwise None (after trying configured precedence).

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       on HTTP errors, or response parsing failures.
        """
        try:
            return self._apply_access_strategy(
                access_strategy=access_strategy,
                tenant=tenant,
                fetch_func=lambda t: self._get_certificate(
                    name=name, tenant_subdomain=t, level=Level.SUB_ACCOUNT
                ),
            )
        except HttpError as e:
            raise DestinationOperationError(f"failed to get certificate '{name}': {e}")

    # ---------- Write operations ----------

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_CREATE_CERTIFICATE)
    def create_certificate(
        self,
        certificate: Certificate,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Create a certificate.

        Args:
            certificate: Certificate entity to create.
            level: Scope where the certificate should be created (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the certificate is created in the
                subscriber context; otherwise the provider context is used.

        Returns:
            None. Success responses from the Destination Service return an empty body.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)
        body = certificate.to_dict()

        try:
            self._http.post(f"{API_V1}/{coll}", body=body, tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to create certificate '{certificate.name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_UPDATE_CERTIFICATE)
    def update_certificate(
        self,
        certificate: Certificate,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Update a certificate.

        Args:
            certificate: Certificate entity with updated fields.
            level: Scope where the certificate exists (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the certificate is updated in the
                subscriber context; otherwise the provider context is used.

        Returns:
            None. Success responses from the Destination Service return an Update object (e.g., {"Count": 1}),
            not the full certificate. The HTTP layer will raise for non-2xx responses.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: For unexpected errors.
        """
        coll = self._sub_path_for_level(level)
        body = certificate.to_dict()

        try:
            self._http.put(f"{API_V1}/{coll}", body=body, tenant_subdomain=tenant)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to update certificate '{certificate.name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_DELETE_CERTIFICATE)
    def delete_certificate(
        self,
        name: str,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Delete a certificate.

        Args:
            name: Certificate name.
            level: Scope where the certificate exists (subaccount by default).
            tenant: Subscriber tenant subdomain. When provided, the certificate is deleted in the
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
                f"failed to delete certificate '{name}': {e}"
            )

    # ---------- Label operations ----------

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_GET_LABELS)
    def get_certificate_labels(
        self,
        name: str,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> List[Label]:
        """Get labels for a certificate.

        Args:
            name: Certificate name.
            level: Scope to query (subaccount by default).
            tenant: Optional subscriber tenant subdomain. If provided, the request is scoped to that tenant.

        Returns:
            List of labels assigned to the certificate. Returns empty list if none assigned.

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
                f"failed to get labels for certificate '{name}': {e}"
            )
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"invalid JSON in get labels response: {e}")

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_UPDATE_LABELS)
    def update_certificate_labels(
        self,
        name: str,
        labels: List[Label],
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Replace all labels for a certificate.

        Args:
            name: Certificate name.
            labels: List of labels to set (replaces existing labels).
            level: Scope where the certificate exists (subaccount by default).
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
                f"failed to put labels for certificate '{name}': {e}"
            )

    @record_metrics(Module.DESTINATION, Operation.CERTIFICATE_PATCH_LABELS)
    def patch_certificate_labels(
        self,
        name: str,
        patch: PatchLabels,
        level: Optional[Level] = Level.SUB_ACCOUNT,
        tenant: Optional[str] = None,
    ) -> None:
        """Add or remove labels for a certificate.

        Args:
            name: Certificate name.
            patch: PatchLabels with action ("ADD" or "DELETE") and labels to apply.
            level: Scope where the certificate exists (subaccount by default).
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
                f"failed to patch labels for certificate '{name}': {e}"
            )

    # ---------- Internal helpers ----------

    def _get_certificate(
        self,
        name: str,
        tenant_subdomain: Optional[str] = None,
        level: Optional[Level] = Level.SUB_ACCOUNT,
    ) -> Optional[Certificate]:
        """Internal helper to fetch a certificate with optional tenant context.

        Args:
            name: Certificate name.
            tenant_subdomain: Subscriber tenant subdomain, if fetching in subscriber context.
            level: Scope to query (subaccount by default).

        Returns:
            Certificate if found, otherwise None (for HTTP 404).

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

            return Certificate.from_dict(data)
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return None
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"invalid JSON in get certificate response: {e}"
            )

    def _list_certificates(
        self,
        level: Level = Level.SUB_ACCOUNT,
        tenant_subdomain: Optional[str] = None,
        filter: Optional[ListOptions] = None,
    ) -> PagedResult[Certificate]:
        """Internal helper to list certificates with optional filters.

        Args:
            level: Scope to query (subaccount or service instance).
            tenant_subdomain: Optional subscriber tenant subdomain for subaccount queries.
            filter: Optional filter configuration for query parameters.

        Returns:
            PagedResult[Certificate] containing certificates and pagination info.
            Pagination info will be None if pagination parameters were not provided.
            Returns empty items list if none found.

        Raises:
            HttpError: Propagated for HTTP errors.
            DestinationOperationError: If response JSON is invalid.
        """
        try:
            path = self._sub_path_for_level(level)
            params = filter.to_query_params() if filter else {}
            resp = self._http.get(
                f"{API_V1}/{path}", tenant_subdomain=tenant_subdomain, params=params
            )

            data = resp.json()
            if not isinstance(data, list):
                raise DestinationOperationError(
                    "expected JSON array in list certificates response"
                )

            certificates = [Certificate.from_dict(item) for item in data]

            # Always parse pagination headers (will be None if not present)
            pagination_info = parse_pagination_headers(resp)

            return PagedResult(items=certificates, pagination=pagination_info)
        except HttpError as e:
            if getattr(e, "status_code", None) == 404:
                return PagedResult(items=[])
            raise
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"invalid JSON in list certificates response: {e}"
            )

    @staticmethod
    def _apply_access_strategy(
        access_strategy: AccessStrategy,
        tenant: Optional[str],
        fetch_func: Callable[[Optional[str]], T],
    ) -> T:
        """Apply access strategy pattern for fetching subaccount certificates.

        This method handles the access strategy logic (subscriber/provider precedence)
        for listing certificates at the subaccount level.

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain.
            fetch_func: Function for fetching data.

        Returns:
            PagedResult[Certificate] containing certificates and pagination info based on the strategy.

        Raises:
            DestinationOperationError: For unknown strategies.
        """
        subscriber_access = [
            AccessStrategy.SUBSCRIBER_ONLY,
            AccessStrategy.SUBSCRIBER_FIRST,
            AccessStrategy.PROVIDER_FIRST,
        ]

        if access_strategy in subscriber_access and tenant is None:
            raise DestinationOperationError(
                "tenant subdomain must be provided for subscriber access. "
                "If you want to access provider certificates only, use AccessStrategy.PROVIDER_ONLY."
            )

        def is_empty(value) -> bool:
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
