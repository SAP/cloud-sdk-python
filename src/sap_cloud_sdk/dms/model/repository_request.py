from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# Constrained types

RepositoryCategory = Literal["Collaboration", "Instant", "Favorites"]
RepositoryType     = Literal["internal", "external"]


@dataclass
class RepositoryParam:
    param_name: str
    param_value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paramName":  self.param_name,
            "paramValue": self.param_value,
        }


#Internal Repository

@dataclass
class InternalRepoRequest:
    display_name: str
    repository_type: RepositoryType = "internal"
    description: Optional[str] = None
    repository_category: Optional[RepositoryCategory] = None
    external_id: Optional[str] = None
    is_version_enabled: Optional[bool] = None
    is_virus_scan_enabled: Optional[bool] = None
    skip_virus_scan_for_large_file: Optional[bool] = None
    hash_algorithms: Optional[str] = None
    is_thumbnail_enabled: Optional[bool] = None
    is_encryption_enabled: Optional[bool] = None
    is_client_cache_enabled: Optional[bool] = None
    is_content_bridge_enabled: Optional[bool] = None
    is_ai_enabled: Optional[bool] = None
    repository_params: List[RepositoryParam] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "displayName":    self.display_name,
            "repositoryType": self.repository_type,
        }
        optional_fields: Dict[str, Any] = {
            "description":              self.description,
            "repositoryCategory":       self.repository_category,
            "externalId":               self.external_id,
            "isVersionEnabled":         self.is_version_enabled,
            "isVirusScanEnabled":       self.is_virus_scan_enabled,
            "skipVirusScanForLargeFile": self.skip_virus_scan_for_large_file,
            "hashAlgorithms":           self.hash_algorithms,
            "isThumbnailEnabled":       self.is_thumbnail_enabled,
            "isEncryptionEnabled":      self.is_encryption_enabled,
            "isClientCacheEnabled":     self.is_client_cache_enabled,
            "isContentBridgeEnabled":   self.is_content_bridge_enabled,
            "isAIEnabled":              self.is_ai_enabled,
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value

        if self.repository_params:
            payload["repositoryParams"] = [p.to_dict() for p in self.repository_params]

        return payload


#External Repository

@dataclass
class ExternalRepoDetails:
    display_name: str
    repository_id: str
    repository_type: RepositoryType = "external"
    description: Optional[str] = None
    external_id: Optional[str] = None
    repository_params: List[RepositoryParam] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "displayName":    self.display_name,
            "repositoryType": self.repository_type,
            "repositoryId":   self.repository_id,
        }
        optional_fields: Dict[str, Any] = {
            "description": self.description,
            "externalId":  self.external_id,
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value

        if self.repository_params:
            payload["repositoryParams"] = [p.to_dict() for p in self.repository_params]

        return payload


@dataclass
class ConnectionRequest:
    destination_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"destinationName": self.destination_name}
        if self.display_name is not None:
            payload["displayName"] = self.display_name
        if self.description is not None:
            payload["description"] = self.description
        return payload


@dataclass
class ExternalRepoRequest:
    repository: ExternalRepoDetails
    connection: ConnectionRequest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": self.repository.to_dict(),
            "connection": self.connection.to_dict(),
        }