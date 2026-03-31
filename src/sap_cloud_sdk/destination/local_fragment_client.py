from __future__ import annotations

from typing import Any, Dict, List, Optional

from sap_cloud_sdk.destination._local_client_base import (
    LocalDevClientBase,
    FRAGMENT_MOCK_FILE,
)
from sap_cloud_sdk.destination._models import AccessStrategy, Fragment, Level
from sap_cloud_sdk.destination.exceptions import HttpError, DestinationOperationError


class LocalDevFragmentClient(LocalDevClientBase[Fragment]):
    """
    Local development client that mocks FragmentClient by manipulating a JSON file.

    Backing store:
      - Fixed JSON file at '<repo root>/mocks/fragments.json'.
      - Overrides via environment variables are not supported.

    JSON schema example (lower-cased keys):
    {
      "subaccount": [
        {
          "fragmentName": "fragmentA",
          "URL": "https://example.com",
          "ProxyType": "Internet",
          "Authentication": "NoAuthentication",
          "Description": "Sample fragment"
          ...additional string properties...
        }
      ],
      "instance": [
        {
          "fragmentName": "fragmentC",
          "URL": "https://provider.example.com",
          "ProxyType": "Internet"
          ...additional string properties...
        }
      ]
    }

    Semantics:
      - get_instance_fragment(name) -> Optional[Fragment]
      - get_subaccount_fragment(name) -> Optional[Fragment]
      - create_fragment(fragment, level) -> None
          Creates in 'instance' or 'subaccount'. Duplicate names raise HttpError(409).
      - update_fragment(fragment, level) -> None
          Updates by name in the selected collection. Missing raises HttpError(404).
      - delete_fragment(name, level) -> None
          Deletes by name in the selected collection. Missing raises HttpError(404).
    """

    # ---------- Base class implementation ----------

    @property
    def file_name(self) -> str:
        """Return the JSON file name."""
        return FRAGMENT_MOCK_FILE

    @property
    def name_field(self) -> str:
        """Return the primary name field for fragments."""
        return "FragmentName"

    @property
    def alt_name_field(self) -> Optional[str]:
        """Return the alternative name field for fragments."""
        return "fragmentName"

    def from_dict(self, data: Dict[str, Any]) -> Fragment:
        """Convert dictionary to Fragment object."""
        return Fragment.from_dict(data)

    def to_dict(self, entity: Fragment) -> Dict[str, Any]:
        """Convert Fragment object to dictionary."""
        return entity.to_dict()

    # ---------- Read operations ----------

    def get_instance_fragment(self, name: str) -> Optional[Fragment]:
        """Get a fragment from the service instance scope.

        Args:
            name: Fragment name.

        Returns:
            Fragment if found, otherwise None.

        Raises:
            DestinationOperationError: On file read/parse errors.
        """
        return self._get_entity("instance", name)

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
        self._validate_subscriber_access(access_strategy, tenant, "fragments")
        try:
            data = self._read()
            sub_list = data.get("subaccount", [])
            return self._resolve_subaccount_entity(
                name, access_strategy, tenant, sub_list
            )
        except HttpError:
            raise
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to get fragment '{name}': {e}")

    def list_instance_fragments(self) -> List[Fragment]:
        """List all fragments from the service instance scope.

        Returns:
            List of fragments. Returns empty list if no fragments exist.

        Raises:
            DestinationOperationError: On file read/parse errors.
        """
        try:
            data = self._read()
            return [Fragment.from_dict(entry) for entry in data.get("instance", [])]
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to list instance fragments: {e}")

    def list_subaccount_fragments(
        self,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
    ) -> List[Fragment]:
        """List fragments from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: List only from subscriber context (tenant required)
            - PROVIDER_ONLY: List only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: List from subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: List from provider first, fallback to subscriber (tenant required)

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.

        Returns:
            List of fragments (after trying configured precedence). Returns empty list if no fragments exist.

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       or on file read/parse errors.
        """
        self._validate_subscriber_access(access_strategy, tenant, "fragments")
        try:
            data = self._read()
            sub_list = data.get("subaccount", [])
            return self._resolve_subaccount_list(access_strategy, tenant, sub_list)
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to list subaccount fragments: {e}")

    # ---------- Write operations ----------

    def create_fragment(
        self, fragment: Fragment, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Create a fragment.

        Args:
            fragment: Fragment entity to create.
            level: Scope where the fragment should be created (subaccount by default).

        Raises:
            HttpError: If a fragment with the same name already exists (409).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._create_entity(collection, fragment, fragment.name)

    def update_fragment(
        self, fragment: Fragment, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Update a fragment.

        Args:
            fragment: Fragment entity with updated fields.
            level: Scope where the fragment exists (subaccount by default).

        Raises:
            HttpError: If the fragment is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._update_entity(collection, fragment, fragment.name)

    def delete_fragment(
        self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Delete a fragment.

        Args:
            name: Fragment name.
            level: Scope where the fragment exists (subaccount by default).

        Raises:
            HttpError: If the fragment is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._delete_entity(collection, name)
