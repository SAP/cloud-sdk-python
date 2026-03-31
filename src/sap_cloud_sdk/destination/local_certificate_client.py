from __future__ import annotations

from typing import Any, Dict, Optional

from sap_cloud_sdk.destination._local_client_base import LocalDevClientBase, CERTIFICATE_MOCK_FILE
from sap_cloud_sdk.destination._models import AccessStrategy, Certificate, Level
from sap_cloud_sdk.destination.utils._pagination import PagedResult
from sap_cloud_sdk.destination.exceptions import HttpError, DestinationOperationError


class LocalDevCertificateClient(LocalDevClientBase[Certificate]):
    """
    Local development client that mocks CertificateClient by manipulating a JSON file.

    Backing store:
      - Fixed JSON file at '<repo root>/mocks/certificates.json'.
      - Overrides via environment variables are not supported.

    JSON schema example (lower-cased keys):
    {
      "subaccount": [
        {
          "Name": "cert1.pem",
          "Content": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
          "Type": "PEM"
          ...additional string properties...
        }
      ],
      "instance": [
        {
          "Name": "keystore.jks",
          "Content": "base64-encoded-content",
          "Type": "JKS"
          ...additional string properties...
        }
      ]
    }

    Semantics:
      - get_instance_certificate(name) -> Optional[Certificate]
      - get_subaccount_certificate(name) -> Optional[Certificate]
      - create_certificate(certificate, level) -> None
          Creates in 'instance' or 'subaccount'. Duplicate names raise HttpError(409).
      - update_certificate(certificate, level) -> None
          Updates by name in the selected collection. Missing raises HttpError(404).
      - delete_certificate(name, level) -> None
          Deletes by name in the selected collection. Missing raises HttpError(404).
    """

    # ---------- Base class implementation ----------

    @property
    def file_name(self) -> str:
        """Return the JSON file name."""
        return CERTIFICATE_MOCK_FILE

    @property
    def name_field(self) -> str:
        """Return the primary name field for certificates."""
        return "Name"

    @property
    def alt_name_field(self) -> Optional[str]:
        """Return the alternative name field for certificates."""
        return "name"

    def from_dict(self, data: Dict[str, Any]) -> Certificate:
        """Convert dictionary to Certificate object."""
        return Certificate.from_dict(data)

    def to_dict(self, entity: Certificate) -> Dict[str, Any]:
        """Convert Certificate object to dictionary."""
        return entity.to_dict()

    # ---------- Public API ----------

    def get_instance_certificate(self, name: str) -> Optional[Certificate]:
        """Get a certificate from the service instance scope.

        Args:
            name: Certificate name.

        Returns:
            Certificate if found, otherwise None.

        Raises:
            DestinationOperationError: On file read/parse errors.
        """
        return self._get_entity("instance", name)

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
        self._validate_subscriber_access(access_strategy, tenant, "certificates")
        try:
            data = self._read()
            sub_list = data.get("subaccount", [])
            return self._resolve_subaccount_entity(name, access_strategy, tenant, sub_list)
        except HttpError:
            raise
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to get certificate '{name}': {e}")

    def create_certificate(self, certificate: Certificate, level: Optional[Level] = Level.SUB_ACCOUNT) -> None:
        """Create a certificate.

        Args:
            certificate: Certificate entity to create.
            level: Scope where the certificate should be created (subaccount by default).

        Raises:
            HttpError: If a certificate with the same name already exists (409).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._create_entity(collection, certificate, certificate.name)

    def update_certificate(self, certificate: Certificate, level: Optional[Level] = Level.SUB_ACCOUNT) -> None:
        """Update a certificate.

        Args:
            certificate: Certificate entity with updated fields.
            level: Scope where the certificate exists (subaccount by default).

        Raises:
            HttpError: If the certificate is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._update_entity(collection, certificate, certificate.name)

    def delete_certificate(self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT) -> None:
        """Delete a certificate.

        Args:
            name: Certificate name.
            level: Scope where the certificate exists (subaccount by default).

        Raises:
            HttpError: If the certificate is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._delete_entity(collection, name)

    def list_instance_certificates(
            self,
            _filter: Optional[Any] = None
    ) -> PagedResult[Certificate]:
        """List all certificates from the service instance scope.

        Args:
            filter: Optional ListCertificatesFilter (ignored in local dev mode).

        Returns:
            PagedResult[Certificate] containing certificates and pagination info.
            Pagination info is always None in local dev mode.
            Returns empty items list if none found.

        Raises:
            DestinationOperationError: On file read/parse errors.
        """
        try:
            data = self._read()
            items = [Certificate.from_dict(entry) for entry in data.get("instance", [])]
            return PagedResult(items=items)
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to list instance certificates: {e}")

    def list_subaccount_certificates(
            self,
            access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
            tenant: Optional[str] = None,
            _filter: Optional[Any] = None
    ) -> PagedResult[Certificate]:
        """List certificates from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: List only from subscriber context (tenant required)
            - PROVIDER_ONLY: List only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: List from subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: List from provider first, fallback to subscriber (tenant required)

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            filter: Optional ListCertificatesFilter (ignored in local dev mode).

        Returns:
            PagedResult[Certificate] containing certificates and pagination info.
            Pagination info is always None in local dev mode.

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       or on file read/parse errors.
        """
        self._validate_subscriber_access(access_strategy, tenant, "certificates")
        try:
            data = self._read()
            sub_list = data.get("subaccount", [])
            items = self._resolve_subaccount_list(access_strategy, tenant, sub_list)
            return PagedResult(items=items)
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to list subaccount certificates: {e}")
