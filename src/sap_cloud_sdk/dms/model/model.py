"""Data models for DMS service."""

from dataclasses import dataclass

@dataclass
class DMSCredentials:
    instance_name: str
    uri: str
    client_id: str
    client_secret: str
    token_url: str
    identityzone: str


from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from enum import Enum


class RepositoryType(str, Enum):
    INTERNAL = "internal"


class RepositoryCategory(str, Enum):
    COLLABORATION = "Collaboration"
    INSTANT = "Instant"
    FAVORITES = "Favorites"


@dataclass
class RepositoryParam:
    paramName: str
    paramValue: str


@dataclass
class InternalRepoRequest:
    # Required fields
    displayName: str
    repositoryType: RepositoryType = RepositoryType.INTERNAL

    # Optional fields
    description: Optional[str] = None
    repositoryCategory: Optional[RepositoryCategory] = None
    isVersionEnabled: Optional[bool] = None
    isVirusScanEnabled: Optional[bool] = None
    skipVirusScanForLargeFile: Optional[bool] = None
    hashAlgorithms: Optional[str] = None
    isThumbnailEnabled: Optional[bool] = None
    isEncryptionEnabled: Optional[bool] = None
    isClientCacheEnabled: Optional[bool] = None
    externalId: Optional[str] = None
    isContentBridgeEnabled: Optional[bool] = None
    isAIEnabled: Optional[bool] = None
    repositoryParams: list[RepositoryParam] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]: 
        raw: dict[str, Any] = asdict(self)
        return {k: v for k, v in raw.items() if v is not None}