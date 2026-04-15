from __future__ import annotations

from typing import Any, Dict, List, Optional

from sap_cloud_sdk.destination._local_client_base import (
    LocalDevClientBase,
    DESTINATION_MOCK_FILE,
)
from sap_cloud_sdk.destination._models import (
    AccessStrategy,
    Destination,
    Label,
    Level,
    PatchLabels,
)
from sap_cloud_sdk.destination.utils._pagination import PagedResult
from sap_cloud_sdk.destination.exceptions import DestinationOperationError, HttpError


class LocalDevDestinationClient(LocalDevClientBase[Destination]):
    """
    Local development client that mocks DestinationClient by manipulating a JSON file.

    Backing store:
      - Fixed JSON file at '<repo root>/mocks/destination.json'.
      - Overrides via environment variables are not supported.

    JSON schema example (lower-cased keys, plus optional 'tenant' for subscriber entries):
    {
      "subaccount": [
        {
          "tenant": "t1",                # optional: subscriber-specific entry
          "name": "destA",
          "type": "HTTP",
          "url": "https://example.com",
          "proxyType": "Internet",
          "authentication": "NoAuthentication",
          "description": "Sample"
          ...additional string properties...
        }
      ],
      "instance": [
        {
          "name": "destC",
          "type": "HTTP",
          "url": "https://provider.example.com"
          ...additional string properties...
        }
      ]
    }

    Semantics:
      - get_instance_destination(name) -> Optional[Destination]
      - get_subaccount_destination(name, access_strategy, tenant) -> Optional[Destination]
          Access strategies match DestinationClient:
            * SUBSCRIBER_ONLY: search subaccount entries with matching tenant
            * PROVIDER_ONLY: search subaccount entries without 'tenant'
            * SUBSCRIBER_FIRST: try subscriber (tenant required), then provider
            * PROVIDER_FIRST: try provider, then subscriber (tenant required)
      - create_destination(dest, level) -> None
          Creates in 'instance' or provider 'subaccount' (no tenant). Duplicate names raise HttpError(409).
      - update_destination(dest, level) -> None
          Updates by name in the selected collection. Missing raises HttpError(404).
      - delete_destination(name, level) -> None
          Deletes by name in the selected collection. Missing raises HttpError(404).
    """

    # ---------- Base class implementation ----------

    @property
    def file_name(self) -> str:
        """Return the JSON file name."""
        return DESTINATION_MOCK_FILE

    @property
    def name_field(self) -> str:
        """Return the primary name field for destinations."""
        return "name"

    @property
    def alt_name_field(self) -> Optional[str]:
        """Return the alternative name field for destinations."""
        return "Name"

    def from_dict(self, data: Dict[str, Any]) -> Destination:
        """Convert dictionary to Destination object."""
        return Destination.from_dict(data)

    def to_dict(self, entity: Destination) -> Dict[str, Any]:
        """Convert Destination object to dictionary."""
        return entity.to_dict()

    # ---------- Read operations ----------

    def get_instance_destination(self, name: str) -> Optional[Destination]:
        """Get a destination from the service instance scope.

        Args:
            name: Destination name.

        Returns:
            Destination if found, otherwise None.

        Raises:
            DestinationOperationError: On file read/parse errors.
        """
        return self._get_entity("instance", name)

    def get_subaccount_destination(
        self,
        name: str,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
    ) -> Optional[Destination]:
        """Get a destination from the subaccount scope with an access strategy.

        Args:
            name: Destination name.
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.

        Returns:
            Destination if found, otherwise None (after trying configured precedence).

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       or on file read/parse errors.
        """
        self._validate_subscriber_access(access_strategy, tenant, "destinations")
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
            raise DestinationOperationError(f"failed to get destination '{name}': {e}")

    # ---------- Write operations ----------

    def create_destination(
        self, dest: Destination, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Create a destination.

        Args:
            dest: Destination entity to create.
            level: Scope where the destination should be created (subaccount by default).

        Raises:
            HttpError: If a destination with the same name already exists (409).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"

        if collection == "instance":
            self._create_entity(collection, dest, dest.name)
        else:
            # Provider context only — no tenant field
            entry = dest.to_dict()
            try:
                with self._lock:
                    data = self._read()
                    lst = data.setdefault(collection, [])
                    if self._find_by_name_and_no_tenant(lst, dest.name) is not None:
                        raise HttpError(
                            f"destination '{dest.name}' already exists",
                            status_code=409,
                            response_text="Conflict",
                        )
                    lst.append(entry)
                    self._write(data)
            except HttpError:
                raise
            except Exception as e:
                raise DestinationOperationError(
                    f"failed to create destination '{dest.name}': {e}"
                )

    def update_destination(
        self, dest: Destination, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Update a destination.

        Args:
            dest: Destination entity with updated fields.
            level: Scope where the destination exists (subaccount by default).

        Raises:
            HttpError: If the destination is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        if collection == "instance":
            self._update_entity(collection, dest, dest.name, preserve_fields=["labels"])
        else:
            # Preserve tenant and labels fields for subaccount-level entries
            self._update_entity(
                collection, dest, dest.name, preserve_fields=["tenant", "labels"]
            )

    def delete_destination(
        self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Delete a destination.

        Args:
            name: Destination name.
            level: Scope where the destination exists (subaccount by default).

        Raises:
            HttpError: If the destination is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"

        if collection == "instance":
            self._delete_entity(collection, name)
        else:
            # Provider context only — no tenant field
            try:
                with self._lock:
                    data = self._read()
                    lst = data.setdefault(collection, [])
                    idx = self._index_by_name_and_no_tenant(lst, name)
                    if idx < 0:
                        raise HttpError(
                            f"destination '{name}' not found",
                            status_code=404,
                            response_text="Not Found",
                        )
                    lst.pop(idx)
                    self._write(data)
            except HttpError:
                raise
            except Exception as e:
                raise DestinationOperationError(
                    f"failed to delete destination '{name}': {e}"
                )

    def list_instance_destinations(
        self, _filter: Optional[Any] = None
    ) -> PagedResult[Destination]:
        """List all destinations from the service instance scope.

        Args:
            filter: Optional ListDestinationsFilter (ignored in local dev mode).

        Returns:
            PagedResult[Destination] containing destinations and pagination info.
            Pagination info is always None in local dev mode.
            Returns empty items list if no destinations are found.

        Raises:
            DestinationOperationError: On file read/parse errors.
        """
        try:
            data = self._read()
            items = [Destination.from_dict(entry) for entry in data.get("instance", [])]
            return PagedResult(items=items)
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to list instance destinations: {e}"
            )

    def list_subaccount_destinations(
        self,
        access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST,
        tenant: Optional[str] = None,
        _filter: Optional[Any] = None,
    ) -> PagedResult[Destination]:
        """List destinations from the subaccount scope with an access strategy.

        Access strategies:
            - SUBSCRIBER_ONLY: List only from subscriber context (tenant required)
            - PROVIDER_ONLY: List only from provider context (no tenant required)
            - SUBSCRIBER_FIRST: List from subscriber (tenant required), fallback to provider
            - PROVIDER_FIRST: List from provider first, fallback to subscriber (tenant required)

        Args:
            access_strategy: Strategy controlling precedence between subscriber and provider contexts.
            tenant: Subscriber tenant subdomain, required for subscriber access strategies.
            filter: Optional ListDestinationsFilter (ignored in local dev mode).

        Returns:
            PagedResult[Destination] containing destinations and pagination info.
            Pagination info is always None in local dev mode.

        Raises:
            DestinationOperationError: If tenant is missing for subscriber access strategies,
                                       or on file read/parse errors.
        """
        self._validate_subscriber_access(access_strategy, tenant, "destinations")
        try:
            data = self._read()
            sub_list = data.get("subaccount", [])
            items = self._resolve_subaccount_list(access_strategy, tenant, sub_list)
            return PagedResult(items=items)
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(
                f"failed to list subaccount destinations: {e}"
            )

    # ---------- Label operations ----------

    def get_destination_labels(
        self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> List[Label]:
        """Get labels for a destination.

        Args:
            name: Destination name.
            level: Scope to query (subaccount by default).

        Returns:
            List of labels. Returns empty list if none assigned.

        Raises:
            HttpError: If the destination is not found (404).
            DestinationOperationError: On file read errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        raw = self._get_labels(collection, name)
        return [Label.from_dict(item) for item in raw]

    def update_destination_labels(
        self, name: str, labels: List[Label], level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Replace all labels for a destination.

        Args:
            name: Destination name.
            labels: List of labels to set (replaces existing labels).
            level: Scope where the destination exists (subaccount by default).

        Raises:
            HttpError: If the destination is not found (404).
            DestinationOperationError: On file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._set_labels(collection, name, [lbl.to_dict() for lbl in labels])

    def patch_destination_labels(
        self, name: str, patch: PatchLabels, level: Optional[Level] = Level.SUB_ACCOUNT
    ) -> None:
        """Add or remove labels for a destination.

        Args:
            name: Destination name.
            patch: PatchLabels with action ("ADD" or "DELETE") and labels to apply.
            level: Scope where the destination exists (subaccount by default).

        Raises:
            HttpError: If the destination is not found (404).
            DestinationOperationError: On unknown action or file read/write errors.
        """
        collection = "instance" if level == Level.SERVICE_INSTANCE else "subaccount"
        self._patch_labels_in_store(
            collection, name, patch.action, [lbl.to_dict() for lbl in patch.labels]
        )
