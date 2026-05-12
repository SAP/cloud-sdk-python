"""Local file-based transport for extensibility development and testing.

Reads extension capability implementations from a local JSON file
instead of calling the extensibility backend.  Activated in two ways:

1. **File-presence detection** (zero-config): place a file at
   ``<repo-root>/mocks/extensibility.json``.
2. **Environment variable** (explicit): set
   ``CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE`` to any file path.

The environment variable takes precedence when both are present.

The JSON file must use the same schema as the backend response.
See ``local_extensibility_example.json`` in this package for a ready-to-use
template::

    CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE=src/sap_cloud_sdk/extensibility/local_extensibility_example.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    ExtensionCapabilityImplementation,
)
from sap_cloud_sdk.extensibility.exceptions import TransportError

logger = logging.getLogger(__name__)

#: Environment variable that activates local mode.
#: Set to a file path containing the JSON response.
CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE_ENV = "CLOUD_SDK_LOCAL_EXTENSIBILITY_FILE"

#: Default mock file name used for file-presence detection under ``mocks/``.
EXTENSIBILITY_MOCK_FILE = "extensibility.json"


class LocalTransport:
    """File-based transport that reads extension data from a local JSON file.

    Intended for local development and testing. The JSON file uses the same
    schema as the extensibility backend response, so a captured real
    response can be used directly.

    Args:
        file_path: Path to the JSON file containing the extension data.
    """

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)

    def get_extension_capability_implementation(
        self,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
        skip_cache: bool = False,
        tenant: str = "",
    ) -> ExtensionCapabilityImplementation:
        """Read extension capability implementation from the local JSON file.

        Args:
            capability_id: Extension capability ID. Ignored for file-based
                lookup (the file contains a single response), but accepted
                for interface compatibility.
            skip_cache: Accepted for interface compatibility but ignored
                by the local transport (no caching layer).
            tenant: Accepted for interface compatibility but ignored
                by the local transport.

        Returns:
            Parsed ``ExtensionCapabilityImplementation`` from the JSON file.

        Raises:
            TransportError: If the file cannot be read or parsed.
        """
        try:
            raw = self._file_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise TransportError(
                f"Local extensibility file not found: {self._file_path}"
            ) from exc
        except OSError as exc:
            raise TransportError(
                f"Failed to read local extensibility file '{self._file_path}': {exc}"
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TransportError(
                f"Failed to parse local extensibility file '{self._file_path}' "
                f"as JSON: {exc}"
            ) from exc

        return ExtensionCapabilityImplementation.from_dict(data)
