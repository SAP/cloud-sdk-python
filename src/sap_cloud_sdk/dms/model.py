"""Data models for DMS service."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict, cast
from urllib.parse import urlparse


def _serialize(v: Any) -> Any:
    """Recursively serialize values — converts Enums to their values, handles nested dicts/lists."""
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, dict):
        d: dict[str, Any] = cast(dict[str, Any], v)
        return {str(k): _serialize(val) for k, val in d.items()}
    if isinstance(v, list):
        lst: list[Any] = cast(list[Any], v)
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
            k: v
            for k, v in {
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
                raise ValueError(
                    f"DMSCredentials.{fname} is not a valid URL: '{value}'"
                )


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


class HashAlgorithm(str, Enum):
    MD5 = "MD5"
    SHA1 = "SHA-1"
    SHA256 = "SHA-256"


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
    x_ecm_add_principals: Optional[List[str]] = field(default_factory=lambda: [])


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
    hashAlgorithms: Optional[HashAlgorithm] = None
    isThumbnailEnabled: Optional[bool] = None
    isEncryptionEnabled: Optional[bool] = None
    externalId: Optional[str] = None
    isContentBridgeEnabled: Optional[bool] = None
    isAIEnabled: Optional[bool] = None
    repositoryParams: List[RepositoryParam] = field(default_factory=lambda: [])

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
    repositoryParams: List[RepositoryParam] = field(default_factory=lambda: [])

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

    @staticmethod
    def _parse_repo_params(raw: Any) -> "RepositoryParams":
        """Normalise repositoryParams from the API response.

        The API may return:
        - A list of ``{paramName, paramValue}`` dicts (common case)
        - A single ``{paramName, paramValue}`` dict (when only one param)
        - An empty list or ``None``
        """
        if not raw:
            return cast(RepositoryParams, {})
        if isinstance(raw, dict):
            raw = [raw]
        return cast(RepositoryParams, {p["paramName"]: p["paramValue"] for p in raw})

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
            created_time=datetime.fromisoformat(
                data["createdTime"].replace("Z", "+00:00")
            ),
            id=data["id"],
            last_updated_time=datetime.fromisoformat(
                data["lastUpdatedTime"].replace("Z", "+00:00")
            ),
            name=data["name"],
            repository_category=data["repositoryCategory"],
            repository_params=cls._parse_repo_params(data.get("repositoryParams")),
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
            "lastUpdatedTime": self.last_updated_time.isoformat().replace(
                "+00:00", "Z"
            ),
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
            created_time=datetime.fromisoformat(
                data["createdTime"].replace("Z", "+00:00")
            ),
            last_updated_time=datetime.fromisoformat(
                data["lastUpdatedTime"].replace("Z", "+00:00")
            ),
            service_instance_id=data["serviceInstanceId"],
        )


# ---------------------------------------------------------------------------
# CMIS browser-binding response models
# ---------------------------------------------------------------------------


def _parse_datetime(val: Any) -> Optional[datetime]:
    """Parse a CMIS timestamp (epoch millis or ISO string) into a datetime."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
    return datetime.fromisoformat(str(val).replace("Z", "+00:00"))


def _prop_val(props: Dict[str, Any], key: str) -> Any:
    """Extract a property value from verbose or succinct CMIS properties.

    Verbose format:  ``{"cmis:name": {"value": "MyDoc"}}``
    Succinct format: ``{"cmis:name": "MyDoc"}``
    """
    raw = props.get(key)
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


@dataclass
class CmisObject:
    """Base CMIS object with shared properties."""

    object_id: str = ""
    name: str = ""
    base_type_id: str = ""
    object_type_id: str = ""
    created_by: Optional[str] = None
    creation_date: Optional[datetime] = None
    last_modified_by: Optional[str] = None
    last_modification_date: Optional[datetime] = None
    change_token: Optional[str] = None
    parent_ids: Optional[List[str]] = None
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CmisObject":
        props = data.get("succinctProperties") or data.get("properties") or {}
        return cls(
            object_id=_prop_val(props, "cmis:objectId") or "",
            name=_prop_val(props, "cmis:name") or "",
            base_type_id=_prop_val(props, "cmis:baseTypeId") or "",
            object_type_id=_prop_val(props, "cmis:objectTypeId") or "",
            created_by=_prop_val(props, "cmis:createdBy"),
            creation_date=_parse_datetime(_prop_val(props, "cmis:creationDate")),
            last_modified_by=_prop_val(props, "cmis:lastModifiedBy"),
            last_modification_date=_parse_datetime(
                _prop_val(props, "cmis:lastModificationDate")
            ),
            change_token=_prop_val(props, "cmis:changeToken"),
            parent_ids=_prop_val(props, "sap:parentIds"),
            description=_prop_val(props, "cmis:description"),
            properties=props,
        )


@dataclass
class Folder(CmisObject):
    """CMIS folder object."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Folder":
        base = CmisObject.from_dict(data)
        return cls(
            **{k: v for k, v in base.__dict__.items() if k in cls.__dataclass_fields__}
        )


@dataclass
class Document(CmisObject):
    """CMIS document with content stream and versioning metadata."""

    content_stream_length: Optional[int] = None
    content_stream_mime_type: Optional[str] = None
    content_stream_file_name: Optional[str] = None
    version_series_id: Optional[str] = None
    version_label: Optional[str] = None
    is_latest_version: Optional[bool] = None
    is_major_version: Optional[bool] = None
    is_latest_major_version: Optional[bool] = None
    is_private_working_copy: Optional[bool] = None
    checkin_comment: Optional[str] = None
    is_version_series_checked_out: Optional[bool] = None
    version_series_checked_out_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        base = CmisObject.from_dict(data)
        props = base.properties
        return cls(
            **{
                k: v
                for k, v in base.__dict__.items()
                if k in CmisObject.__dataclass_fields__
            },
            content_stream_length=_prop_val(props, "cmis:contentStreamLength"),
            content_stream_mime_type=_prop_val(props, "cmis:contentStreamMimeType"),
            content_stream_file_name=_prop_val(props, "cmis:contentStreamFileName"),
            version_series_id=_prop_val(props, "cmis:versionSeriesId"),
            version_label=_prop_val(props, "cmis:versionLabel"),
            is_latest_version=_prop_val(props, "cmis:isLatestVersion"),
            is_major_version=_prop_val(props, "cmis:isMajorVersion"),
            is_latest_major_version=_prop_val(props, "cmis:isLatestMajorVersion"),
            is_private_working_copy=_prop_val(props, "cmis:isPrivateWorkingCopy"),
            checkin_comment=_prop_val(props, "cmis:checkinComment"),
            is_version_series_checked_out=_prop_val(
                props, "cmis:isVersionSeriesCheckedOut"
            ),
            version_series_checked_out_id=_prop_val(
                props, "cmis:versionSeriesCheckedOutId"
            ),
        )


@dataclass
class Ace:
    """Single access control entry."""

    principal_id: str
    permissions: List[str] = field(default_factory=list)
    is_direct: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ace":
        principal = data.get("principal", {})
        return cls(
            principal_id=principal.get("principalId", ""),
            permissions=data.get("permissions", []),
            is_direct=data.get("isDirect", True),
        )


@dataclass
class Acl:
    """Access control list for a CMIS object."""

    aces: List[Ace] = field(default_factory=list)
    is_exact: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Acl":
        raw_aces = data.get("aces", [])
        return cls(
            aces=[Ace.from_dict(a) for a in raw_aces],
            is_exact=data.get("isExact", True),
        )


@dataclass
class ChildrenOptions:
    """Pagination and query options for :meth:`DMSClient.get_children`.

    Encapsulates all pagination and filter parameters for listing folder
    children, following the same pattern as the Destination module's
    ``ListOptions``.

    Example:
        ```python
        from sap_cloud_sdk.dms import create_client, ChildrenOptions

        client = create_client()
        options = ChildrenOptions(max_items=50, skip_count=100, order_by="cmis:creationDate ASC")
        page = client.get_children(repo_id, folder_id, options=options)
        while page.has_more_items:
            options.skip_count += options.max_items
            page = client.get_children(repo_id, folder_id, options=options)
        ```

    Attributes:
        max_items: Maximum number of items to return per page (default 100).
        skip_count: Number of items to skip (pagination offset, default 0).
        order_by: Sort order (e.g. ``"cmis:creationDate ASC"``).
        filter: Comma-separated CMIS property filter list.
        include_allowable_actions: Include allowable actions per child.
        include_path_segment: Include the path segment per child.
        succinct: Use succinct property format (default True).
    """

    max_items: int = 100
    skip_count: int = 0
    order_by: Optional[str] = None
    filter: Optional[str] = None
    include_allowable_actions: bool = False
    include_path_segment: bool = False
    succinct: bool = True

    def to_query_params(self) -> Dict[str, str]:
        """Convert options to CMIS query parameters.

        Returns:
            Dict[str, str]: Query parameters for the HTTP request.
        """
        params: Dict[str, str] = {
            "maxItems": str(self.max_items),
            "skipCount": str(self.skip_count),
        }
        if self.order_by:
            params["orderBy"] = self.order_by
        if self.filter:
            params["filter"] = self.filter
        if self.include_allowable_actions:
            params["includeAllowableActions"] = "true"
        if self.include_path_segment:
            params["includePathSegment"] = "true"
        if self.succinct:
            params["succinct"] = "true"
        return params


@dataclass
class ChildrenPage:
    """Paginated result from a CMIS ``getChildren`` request."""

    objects: List[CmisObject] = field(default_factory=list)
    has_more_items: bool = False
    num_items: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChildrenPage":
        raw_objects = data.get("objects") or []
        parsed: List[CmisObject] = []
        for entry in raw_objects:
            obj_data = entry.get("object") or entry
            props = (
                obj_data.get("succinctProperties") or obj_data.get("properties") or {}
            )
            base_type = _prop_val(props, "cmis:baseTypeId") or ""
            if base_type == "cmis:document":
                parsed.append(Document.from_dict(obj_data))
            elif base_type == "cmis:folder":
                parsed.append(Folder.from_dict(obj_data))
            else:
                parsed.append(CmisObject.from_dict(obj_data))
        return cls(
            objects=parsed,
            has_more_items=data.get("hasMoreItems", False),
            num_items=data.get("numItems"),
        )
