"""Base class for local development clients with common JSON file operations."""

from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

from sap_cloud_sdk.destination._models import AccessStrategy
from sap_cloud_sdk.destination.exceptions import DestinationOperationError, HttpError

T = TypeVar('T')

_SUBSCRIBER_ACCESS_STRATEGIES = {
    AccessStrategy.SUBSCRIBER_ONLY,
    AccessStrategy.SUBSCRIBER_FIRST,
    AccessStrategy.PROVIDER_FIRST,
}

class LocalDevClientBase(ABC, Generic[T]):
    """
    Base class for local development clients that manipulate JSON files.

    This class provides common functionality for:
    - Thread-safe JSON file operations
    - File initialization and management
    - Common search and indexing operations
    - Access-strategy resolution for subaccount-scoped reads

    Subclasses must implement:
    - file_name: Return the JSON file name (e.g., "destinations.json")
    - name_field: Return the field name used for entity names
    - alt_name_field: Return the alternative name field (or None)
    - from_dict(data): Convert dict to entity object
    - to_dict(entity): Convert entity object to dict
    """

    def __init__(self) -> None:
        # Resolve to repo root and mocks path
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self._file_path = os.path.join(repo_root, "mocks", self.file_name)
        self._lock = threading.Lock()
        self._ensure_file()

    @property
    @abstractmethod
    def file_name(self) -> str:
        """Return the JSON file name (e.g., 'destinations.json')."""
        pass

    @property
    @abstractmethod
    def name_field(self) -> str:
        """Return the primary name field for entities (e.g., 'name', 'FragmentName')."""
        pass

    @property
    @abstractmethod
    def alt_name_field(self) -> Optional[str]:
        """Return the alternative name field for entities (e.g., 'Name', 'fragmentName')."""
        pass

    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> T:
        """Convert dictionary to entity object."""
        pass

    @abstractmethod
    def to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity object to dictionary."""
        pass

    def get_initial_data(self) -> Dict[str, Any]:
        """Return initial data structure for empty files."""
        return {"subaccount": [], "instance": []}

    # ---------- File operations ----------

    def _ensure_file(self) -> None:
        """Ensure the JSON file exists with initial structure."""
        if not os.path.exists(self._file_path):
            with self._lock:
                if not os.path.exists(self._file_path):
                    self._safe_write(self.get_initial_data())

    def _read(self) -> Dict[str, Any]:
        """Read and parse the JSON file."""
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # Initialize if deleted between calls
            self._ensure_file()
            return self.get_initial_data()
        except Exception as e:
            raise DestinationOperationError(f"failed to read local store: {e}")

    def _write(self, data: Dict[str, Any]) -> None:
        """Write data to the JSON file."""
        try:
            self._safe_write(data)
        except Exception as e:
            raise DestinationOperationError(f"failed to write local store: {e}")

    def _safe_write(self, data: Dict[str, Any]) -> None:
        """Atomically write data to the JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        tmp_path = f"{self._file_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, self._file_path)

    # ---------- Search operations ----------

    def _resolve_name(self, item: Dict[str, Any]) -> Optional[str]:
        """Resolve entity name from primary or alternative field."""
        name = item.get(self.name_field)
        if not name and self.alt_name_field:
            name = item.get(self.alt_name_field)
        return name

    def _find_by_name(self, lst: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """Find an item by name in a list."""
        for item in lst:
            if self._resolve_name(item) == name:
                return item
        return None

    def _index_by_name(self, lst: List[Dict[str, Any]], name: str) -> int:
        """Find the index of an item by name in a list."""
        for i, item in enumerate(lst):
            if self._resolve_name(item) == name:
                return i
        return -1

    def _find_by_name_and_no_tenant(self, lst: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """Find an item by name that has no tenant field (provider context)."""
        for item in lst:
            if self._resolve_name(item) == name and not item.get("tenant"):
                return item
        return None

    def _find_by_name_and_tenant(self, lst: List[Dict[str, Any]], name: str, tenant: str) -> Optional[Dict[str, Any]]:
        """Find an item by name and tenant (subscriber context)."""
        for item in lst:
            if self._resolve_name(item) == name and item.get("tenant") == tenant:
                return item
        return None

    def _index_by_name_and_no_tenant(self, lst: List[Dict[str, Any]], name: str) -> int:
        """Find the index of an item by name that has no tenant field (provider context)."""
        for i, item in enumerate(lst):
            if self._resolve_name(item) == name and not item.get("tenant"):
                return i
        return -1

    # ---------- Access-strategy resolution ----------

    def _validate_subscriber_access(self, access_strategy: AccessStrategy, tenant: Optional[str], entity_kind: str) -> None:
        """Raise DestinationOperationError when tenant is required but missing."""
        if access_strategy in _SUBSCRIBER_ACCESS_STRATEGIES and tenant is None:
            raise DestinationOperationError(
                f"tenant subdomain must be provided for subscriber access. "
                f"If you want to access provider {entity_kind} only, use AccessStrategy.PROVIDER_ONLY."
            )

    def _resolve_subaccount_entity(
            self,
            name: str,
            access_strategy: AccessStrategy,
            tenant: Optional[str],
            sub_list: List[Dict[str, Any]],
    ) -> Optional[T]:
        """Resolve a single entity from the subaccount list using the given access strategy."""
        def find_subscriber() -> Optional[T]:
            if tenant is None:
                return None
            entry = self._find_by_name_and_tenant(sub_list, name, tenant)
            return self.from_dict(entry) if entry else None

        def find_provider() -> Optional[T]:
            entry = self._find_by_name_and_no_tenant(sub_list, name)
            return self.from_dict(entry) if entry else None

        order_map: Dict[AccessStrategy, tuple[Callable[[], Optional[T]], ...]] = {
            AccessStrategy.SUBSCRIBER_ONLY: (find_subscriber,),
            AccessStrategy.PROVIDER_ONLY: (find_provider,),
            AccessStrategy.SUBSCRIBER_FIRST: (find_subscriber, find_provider),
            AccessStrategy.PROVIDER_FIRST: (find_provider, find_subscriber),
        }

        funcs = order_map.get(access_strategy)
        if not funcs:
            raise DestinationOperationError(f"unknown access strategy: {access_strategy}")

        for fn in funcs:
            result = fn()
            if result is not None:
                return result
        return None

    def _resolve_subaccount_list(
            self,
            access_strategy: AccessStrategy,
            tenant: Optional[str],
            sub_list: List[Dict[str, Any]],
    ) -> List[T]:
        """Resolve a list of entities from the subaccount list using the given access strategy."""
        def list_subscriber() -> List[T]:
            if tenant is None:
                return []
            return [self.from_dict(entry) for entry in sub_list if entry.get("tenant") == tenant]

        def list_provider() -> List[T]:
            return [self.from_dict(entry) for entry in sub_list if not entry.get("tenant")]

        order_map: Dict[AccessStrategy, tuple[Callable[[], List[T]], ...]] = {
            AccessStrategy.SUBSCRIBER_ONLY: (list_subscriber,),
            AccessStrategy.PROVIDER_ONLY: (list_provider,),
            AccessStrategy.SUBSCRIBER_FIRST: (list_subscriber, list_provider),
            AccessStrategy.PROVIDER_FIRST: (list_provider, list_subscriber),
        }

        funcs = order_map.get(access_strategy)
        if not funcs:
            raise DestinationOperationError(f"unknown access strategy: {access_strategy}")

        results = funcs[0]()
        if not results and len(funcs) > 1:
            results = funcs[1]()
        return results

    # ---------- Common CRUD operations ----------

    def _get_entity(self, collection: str, name: str) -> Optional[T]:
        """Get an entity from a collection by name."""
        try:
            data = self._read()
            entry = self._find_by_name(data.get(collection, []), name)
            return self.from_dict(entry) if entry else None
        except DestinationOperationError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to get entity '{name}': {e}")

    def _create_entity(self, collection: str, entity: T, entity_name: str) -> None:
        """Create an entity in a collection."""
        entry = self.to_dict(entity)
        try:
            with self._lock:
                data = self._read()
                lst = data.setdefault(collection, [])
                if self._find_by_name(lst, entity_name) is not None:
                    raise HttpError(f"entity '{entity_name}' already exists", status_code=409, response_text="Conflict")

                lst.append(entry)
                self._write(data)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to create entity '{entity_name}': {e}")

    def _update_entity(self, collection: str, entity: T, entity_name: str, preserve_fields: Optional[List[str]] = None) -> None:
        """Update an entity in a collection."""
        updated = self.to_dict(entity)
        try:
            with self._lock:
                data = self._read()
                lst = data.setdefault(collection, [])
                idx = self._index_by_name(lst, entity_name)
                if idx < 0:
                    raise HttpError(f"entity '{entity_name}' not found", status_code=404, response_text="Not Found")

                if preserve_fields:
                    existing = lst[idx]
                    for field in preserve_fields:
                        if field in existing and existing[field]:
                            updated[field] = existing[field]

                lst[idx] = updated
                self._write(data)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to update entity '{entity_name}': {e}")

    def _delete_entity(self, collection: str, entity_name: str) -> None:
        """Delete an entity from a collection."""
        try:
            with self._lock:
                data = self._read()
                lst = data.setdefault(collection, [])
                idx = self._index_by_name(lst, entity_name)
                if idx < 0:
                    raise HttpError(f"entity '{entity_name}' not found", status_code=404, response_text="Not Found")

                lst.pop(idx)
                self._write(data)
        except HttpError:
            raise
        except Exception as e:
            raise DestinationOperationError(f"failed to delete entity '{entity_name}': {e}")
