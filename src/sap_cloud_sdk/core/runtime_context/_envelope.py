"""Framework-agnostic request envelope passed to ContextProviders."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RequestEnvelope:
    """Normalized view of an inbound request, independent of framework.

    Framework middlewares build this from their native request object.
    :class:`~sap_cloud_sdk.core.runtime_context.ContextProvider` implementations
    read from it — they never touch framework-specific types.

    Attributes:
        headers:  Case-insensitive HTTP headers (or equivalent for gRPC/etc.).
        body:     Raw request body bytes. ``None`` if not extracted.
        metadata: Catch-all for framework extras (query params, gRPC metadata,
                  connection info, etc.). Reserved for future providers.
    """

    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)
