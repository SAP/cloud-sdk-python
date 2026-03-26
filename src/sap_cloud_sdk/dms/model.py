"""Data models for DMS service."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, TypedDict, cast
from urllib.parse import urlparse

def _serialize(v: Any) -> Any:
    """Recursively serialize values — converts Enums to their values, handles nested dicts/lists."""
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, dict):
        d: dict[str, Any] = cast(dict[str, Any],v) 
        return {str(k): _serialize(val) for k, val in d.items()}
    if isinstance(v, list):
        lst: list[Any] = cast(list[Any],v)
        return [_serialize(i) for i in lst]
    return v


def _to_dict_drop_none(obj: Any) -> dict[str, Any]:
    """Convert a dataclass to a dict, dropping None values and serializing enums."""
    raw: dict[str, Any] = asdict(obj)
    return {k: _serialize(v) for k, v in raw.items() if v is not None}



@dataclass
class DMSCredentials:
    """Credentials for authenticating with the DMS service."""
    instance_name: str
    uri: str
    client_id: str
    client_secret: str
    token_url: str
    identityzone: str

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        placeholders = {
            k: v for k, v in {
                "uri": self.uri,
                "token_url": self.token_url,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "identityzone": self.identityzone,
            }.items()
            if not v or v.startswith("<") or v.endswith(">")
        }
        if placeholders:
            raise ValueError(
                f"DMSCredentials contains unfilled placeholder values: {list(placeholders.keys())}. "
                "Replace all <...> values with real credentials before creating a client."
            )
        for fname, value in {"uri": self.uri, "token_url": self.token_url}.items():
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"DMSCredentials.{fname} is not a valid URL: '{value}'")


class RepositoryType(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class RepositoryCategory(str, Enum):
    COLLABORATION = "Collaboration"
    INSTANT = "Instant"
    FAVORITES = "Favorites"


class ConfigName(str, Enum):
    BLOCKED_FILE_EXTENSIONS = "blockedFileExtensions"
    TEMPSPACE_MAX_CONTENT_SIZE = "tempspaceMaxContentSize"
    IS_CROSS_DOMAIN_MAPPING_ALLOWED = "isCrossDomainMappingAllowed"


@dataclass
class UserClaim:
    """User identity claims forwarded to the DMS service.

    Attributes:
        x_ecm_user_enc: User identifier (e.g. username or email).
        x_ecm_add_principals: Additional principals.
            - Groups: prefix with ``~`` (e.g. ``~group1``)
            - Extra users: plain username or email
    """
    x_ecm_user_enc: Optional[str] = None
    x_ecm_add_principals: Optional[List[str]] = field(default_factory=lambda:[])


@dataclass
class RepositoryParam:
    paramName: str
    paramValue: str


@dataclass
class InternalRepoRequest:
    """Request payload for onboarding a new internal repository."""

    # Required
    displayName: str
    repositoryType: RepositoryType = RepositoryType.INTERNAL

    # Optional
    description: Optional[str] = None
    repositoryCategory: Optional[RepositoryCategory] = None
    isVersionEnabled: Optional[bool] = None
    isVirusScanEnabled: Optional[bool] = None
    skipVirusScanForLargeFile: Optional[bool] = None
    hashAlgorithms: Optional[str] = None # TODO provide enum
    isThumbnailEnabled: Optional[bool] = None
    isEncryptionEnabled: Optional[bool] = None
    externalId: Optional[str] = None
    isContentBridgeEnabled: Optional[bool] = None
    isAIEnabled: Optional[bool] = None
    repositoryParams: List[RepositoryParam] = field(default_factory=lambda:[])

    def to_dict(self) -> dict[str, Any]:
        return _to_dict_drop_none(self)


@dataclass
class UpdateRepoRequest:
    """Request payload for updating an internal repository."""

    description: Optional[str] = None
    isVirusScanEnabled: Optional[bool] = None
    skipVirusScanForLargeFile: Optional[bool] = None
    isThumbnailEnabled: Optional[bool] = None
    isClientCacheEnabled: Optional[bool] = None
    isAIEnabled: Optional[bool] = None
    repositoryParams: List[RepositoryParam] = field(default_factory=lambda:[])

    def to_dict(self) -> dict[str, Any]:
        return {"repository": _to_dict_drop_none(self)}


class RepositoryParams(TypedDict, total=False):
    """Typed schema for known repository parameters returned by the API.

    All keys are optional since the API may not always return every param.
    Unknown params can still be accessed via get_param() on the Repository object.
    """
    changeLogDuration: int
    isVersionEnabled: bool
    isThumbnailEnabled: bool
    isVirusScanEnabled: bool
    hashAlgorithms: str
    skipVirusScanForLargeFile: bool
    isEncryptionEnabled: bool
    isClientCacheEnabled: bool
    isAIEnabled: bool


@dataclass
class Repository:
    """Represents a repository entity returned by the Document Management API.

    Attributes:
        cmis_repository_id: Internal CMIS repository identifier.
        created_time: Timestamp when the repository was created (UTC).
        id: Unique repository UUID.
        last_updated_time: Timestamp of the last update (UTC).
        name: Human-readable repository name.
        repository_category: Category of the repository (e.g. "Instant").
        repository_params: Flat dict of repository parameters. Known keys are
            typed via RepositoryParams. Unknown keys can be accessed via get_param().
        repository_sub_type: Repository sub-type (e.g. "SAP Document Management Service").
        repository_type: Repository type (e.g. "internal").
    """
    cmis_repository_id: str
    created_time: datetime
    id: str
    last_updated_time: datetime
    name: str
    repository_category: str
    repository_params: RepositoryParams
    repository_sub_type: str
    repository_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Repository":
        """Parse a raw API response dict into a Repository instance.

        Converts the repositoryParams list of {paramName, paramValue} objects
        into a flat dict for easier access.

        Args:
            data: Raw dict returned by the repository API.

        Returns:
            Repository: Parsed repository instance.
        """
        return cls(
            cmis_repository_id=data["cmisRepositoryId"],
            created_time=datetime.fromisoformat(data["createdTime"].replace("Z", "+00:00")),
            id=data["id"],
            last_updated_time=datetime.fromisoformat(data["lastUpdatedTime"].replace("Z", "+00:00")),
            name=data["name"],
            repository_category=data["repositoryCategory"],
            repository_params=cast(RepositoryParams, {p["paramName"]: p["paramValue"] for p in data["repositoryParams"]}),
            repository_sub_type=data["repositorySubType"],
            repository_type=data["repositoryType"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize back into an API-compatible payload.

        Converts the flat repository_params dict back into the
        [{paramName, paramValue}] list format expected by the API.
        """
        return {
            "cmisRepositoryId": self.cmis_repository_id,
            "createdTime": self.created_time.isoformat().replace("+00:00", "Z"),
            "id": self.id,
            "lastUpdatedTime": self.last_updated_time.isoformat().replace("+00:00", "Z"),
            "name": self.name,
            "repositoryCategory": self.repository_category,
            "repositoryParams": [
                {"paramName": k, "paramValue": v}
                for k, v in self.repository_params.items()
            ],
            "repositorySubType": self.repository_sub_type,
            "repositoryType": self.repository_type,
        }

    def get_param(self, name: str, default: Any = None) -> Any:
        """Get a repository parameter value by name.

        Use for unknown or dynamic param keys not defined in RepositoryParams.
        For known keys, prefer direct access via repository_params for type safety.

        Args:
            name: The paramName to look up (e.g. "isEncryptionEnabled").
            default: Fallback value if the param is not found.

        Example:
            repo.get_param("isEncryptionEnabled")     # True
            repo.get_param("unknownParam", "N/A")     # "N/A"
        """
        return self.repository_params.get(name, default)


@dataclass
class CreateConfigRequest:
    """Request payload for creating a repository configuration.

    Use ConfigName enum for known config keys. Unknown keys can be passed as raw strings.

    Example:
        CreateConfigRequest(ConfigName.BLOCKED_FILE_EXTENSIONS, "bat,dmg,txt")
        CreateConfigRequest("someCustomConfig", "value")
    """
    config_name: ConfigName | str
    config_value: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "configName": _serialize(self.config_name),
            "configValue": self.config_value,
        }


@dataclass
class UpdateConfigRequest:
    """Request payload for updating a repository configuration.

    Args:
        id: Config Id.
        config_name: ConfigName enum or raw string.
        config_value: Value for the given config name.
        service_instance_id: Optional service instance id.
    """
    id: str
    config_name: ConfigName | str
    config_value: str
    service_instance_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "configName": _serialize(self.config_name),
            "configValue": self.config_value,
        }
        if self.service_instance_id:
            payload["serviceInstanceId"] = self.service_instance_id
        return payload


@dataclass
class RepositoryConfig:
    """Represents a repository configuration entry."""
    id: str
    config_name: str
    config_value: str
    created_time: datetime
    last_updated_time: datetime
    service_instance_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepositoryConfig":
        return cls(
            id=data["id"],
            config_name=data["configName"],
            config_value=data["configValue"],
            created_time=datetime.fromisoformat(data["createdTime"].replace("Z", "+00:00")),
            last_updated_time=datetime.fromisoformat(data["lastUpdatedTime"].replace("Z", "+00:00")),
            service_instance_id=data["serviceInstanceId"],
        )