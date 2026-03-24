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
from typing import Any, List, Optional
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
    

@dataclass
class UserClaim:
    """Represents user identity claims forwarded to the DMS service.

    Attributes:
        x_ecm_user_enc: User identifier (e.g. username or email) passed as a request header.
        x_ecm_add_principals: Additional principals to include in the request.
            - Groups: prefix the group name with ``~`` (e.g. ``~group1``)
            - Extra identifiers: plain username or email (e.g. ``username2``)
    """
    x_ecm_user_enc: Optional[str] = None
    x_ecm_add_principals: Optional[List[str]] = field(default_factory=lambda: [])