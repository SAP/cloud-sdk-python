"""Framework-agnostic request envelope passed to ContextProviders."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RequestEnvelope:
    """Framework-agnostic view of an inbound request passed to providers.

    The framework middleware populates this; providers read from it. This
    means providers work identically regardless of whether the request came
    from Starlette, Flask, gRPC, or a test.

    Attributes:
        headers:  Request headers as a plain dict (lowercased keys recommended).
        body:     Raw request body. ``None`` if not needed by any provider.
        metadata: Framework-specific extras — query params, gRPC metadata, etc.
                  Currently unused; reserved for future providers.
    """

    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)
