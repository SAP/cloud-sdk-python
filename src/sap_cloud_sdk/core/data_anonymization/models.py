"""Data models for the SAP Data Anonymization Service.

The service exposes separate endpoints for text and file processing, with both
anonymization and pseudonymization variants.

Example::

    from sap_cloud_sdk.core.data_anonymization.models import (
        AnonymizeTextRequest,
        PseudonymizeFileRequest,
    )

    text_request = AnonymizeTextRequest(
        text="Contact John Doe at john@example.com",
        entities=["profile-person", "profile-email"],
    )

    file_request = PseudonymizeFileRequest(
        file_path="sample.json",
        pseudonymization_secret="x" * 32,
    )
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _validate_entities(
    entities: Optional[List[str]],
    request_name: str,
) -> None:
    """Validate the optional list of entity profile identifiers."""
    if entities is None:
        return
    if not isinstance(entities, list) or any(
        not isinstance(entity, str) or not entity.strip() for entity in entities
    ):
        raise ValueError(
            f"{request_name}: entities must be a list of non-empty strings"
        )


def _append_form_value(
    fields: List[Tuple[str, str]],
    key: str,
    value: Optional[Any],
) -> None:
    """Append a scalar form field using the service wire format."""
    if value is None:
        return
    if isinstance(value, bool):
        fields.append((key, "true" if value else "false"))
        return
    fields.append((key, str(value)))


def _append_common_form_fields(
    fields: List[Tuple[str, str]],
    *,
    entities: Optional[List[str]],
    anonymization_method_per_profile: Optional[str],
    allowlist: Optional[str],
    enable_default_allowlist: Optional[bool],
    custom_entities: Optional[str],
) -> None:
    """Append request fields shared by text and file operations."""
    if entities:
        for entity in entities:
            fields.append(("entities", entity))
    _append_form_value(
        fields,
        "anonymization-method-per-profile",
        anonymization_method_per_profile,
    )
    _append_form_value(fields, "whitelist", allowlist)
    _append_form_value(
        fields,
        "enable-default-whitelist",
        enable_default_allowlist,
    )
    _append_form_value(fields, "custom-entities", custom_entities)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


@dataclass
class AnonymizeTextRequest:
    """Request payload for the text anonymization endpoint.

    Args:
        text: Text to anonymize.
        entities: Optional list of profile names in priority order.
        anonymization_method_per_profile: JSON string matching the OpenAPI
            `anonymization-method-per-profile` field.
        allowlist: Semicolon-separated values excluded from anonymization.
        enable_default_allowlist: Whether the service default allowlist is used.
        custom_entities: JSON string with custom entity regex definitions.
    """

    text: str
    entities: Optional[List[str]] = None
    anonymization_method_per_profile: Optional[str] = None
    allowlist: Optional[str] = None
    enable_default_allowlist: Optional[bool] = None
    custom_entities: Optional[str] = None

    def validate(self) -> None:
        """Validate required fields and SDK-side parameter constraints."""
        if not self.text or not self.text.strip():
            raise ValueError("AnonymizeTextRequest: text must not be empty")
        _validate_entities(self.entities, "AnonymizeTextRequest")

    def to_form_fields(self) -> List[Tuple[str, str]]:
        """Serialize the request to form-urlencoded fields."""
        fields: List[Tuple[str, str]] = [("text", self.text)]
        _append_common_form_fields(
            fields,
            entities=self.entities,
            anonymization_method_per_profile=self.anonymization_method_per_profile,
            allowlist=self.allowlist,
            enable_default_allowlist=self.enable_default_allowlist,
            custom_entities=self.custom_entities,
        )
        return fields


@dataclass
class PseudonymizeTextRequest:
    """Request payload for the text pseudonymization endpoint.

    Args:
        text: Text to pseudonymize.
        entities: Optional list of profile names in priority order.
        anonymization_method_per_profile: JSON string matching the OpenAPI
            `anonymization-method-per-profile` field.
        allowlist: Semicolon-separated values excluded from processing.
        enable_default_allowlist: Whether the service default allowlist is used.
        custom_entities: JSON string with custom entity regex definitions.
        pseudonymization_metadata: Optional JSON string with existing metadata.
        pseudonymization_secret: Optional deterministic pseudonymization secret.
    """

    text: str
    entities: Optional[List[str]] = None
    anonymization_method_per_profile: Optional[str] = None
    allowlist: Optional[str] = None
    enable_default_allowlist: Optional[bool] = None
    custom_entities: Optional[str] = None
    pseudonymization_metadata: Optional[str] = None
    pseudonymization_secret: Optional[str] = None

    def validate(self) -> None:
        """Validate required fields and pseudonymization-specific constraints."""
        if not self.text or not self.text.strip():
            raise ValueError("PseudonymizeTextRequest: text must not be empty")
        _validate_entities(self.entities, "PseudonymizeTextRequest")
        if (
            self.pseudonymization_secret is not None
            and len(self.pseudonymization_secret) < 32
        ):
            raise ValueError(
                "PseudonymizeTextRequest: pseudonymization_secret must be at least 32 characters"
            )

    def to_form_fields(self) -> List[Tuple[str, str]]:
        """Serialize the request to form-urlencoded fields."""
        fields: List[Tuple[str, str]] = [("text", self.text)]
        _append_common_form_fields(
            fields,
            entities=self.entities,
            anonymization_method_per_profile=self.anonymization_method_per_profile,
            allowlist=self.allowlist,
            enable_default_allowlist=self.enable_default_allowlist,
            custom_entities=self.custom_entities,
        )
        _append_form_value(
            fields,
            "pseudonymization-metadata",
            self.pseudonymization_metadata,
        )
        _append_form_value(
            fields,
            "pseudonymization-secret",
            self.pseudonymization_secret,
        )
        return fields


@dataclass
class AnonymizeFileRequest:
    """Request payload for the file anonymization endpoint.

    Exactly one of `file_path` or `file_content` must be provided.

    Args:
        file_path: Path to the file uploaded as multipart content.
        file_content: In-memory file bytes used instead of `file_path`.
        file_name: Optional multipart filename override.
        entities: Optional list of profile names in priority order.
        anonymization_method_per_profile: JSON string matching the OpenAPI
            `anonymization-method-per-profile` field.
        allowlist: Semicolon-separated values excluded from anonymization.
        enable_default_allowlist: Whether the service default allowlist is used.
        custom_entities: JSON string with custom entity regex definitions.
    """

    file_path: Optional[str] = None
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    entities: Optional[List[str]] = None
    anonymization_method_per_profile: Optional[str] = None
    allowlist: Optional[str] = None
    enable_default_allowlist: Optional[bool] = None
    custom_entities: Optional[str] = None

    def validate(self) -> None:
        """Validate file source selection and common request parameters."""
        has_path = bool(self.file_path)
        has_content = self.file_content is not None
        if has_path == has_content:
            raise ValueError(
                "AnonymizeFileRequest: provide exactly one of file_path or file_content"
            )
        _validate_entities(self.entities, "AnonymizeFileRequest")

    def to_form_fields(self) -> List[Tuple[str, str]]:
        """Serialize non-file fields for the multipart request."""
        fields: List[Tuple[str, str]] = []
        _append_common_form_fields(
            fields,
            entities=self.entities,
            anonymization_method_per_profile=self.anonymization_method_per_profile,
            allowlist=self.allowlist,
            enable_default_allowlist=self.enable_default_allowlist,
            custom_entities=self.custom_entities,
        )
        return fields

    def resolved_file_name(self) -> str:
        """Return the multipart filename sent to the service."""
        if self.file_name:
            return self.file_name
        if self.file_path:
            return os.path.basename(self.file_path)
        return "upload.bin"


@dataclass
class PseudonymizeFileRequest:
    """Request payload for the file pseudonymization endpoint.

    Exactly one of `file_path` or `file_content` must be provided.

    Args:
        file_path: Path to the file uploaded as multipart content.
        file_content: In-memory file bytes used instead of `file_path`.
        file_name: Optional multipart filename override.
        entities: Optional list of profile names in priority order.
        anonymization_method_per_profile: JSON string matching the OpenAPI
            `anonymization-method-per-profile` field.
        allowlist: Semicolon-separated values excluded from processing.
        enable_default_allowlist: Whether the service default allowlist is used.
        custom_entities: JSON string with custom entity regex definitions.
        pseudonymization_metadata: Optional JSON string with existing metadata.
        pseudonymization_secret: Optional deterministic pseudonymization secret.

    """

    file_path: Optional[str] = None
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    entities: Optional[List[str]] = None
    anonymization_method_per_profile: Optional[str] = None
    allowlist: Optional[str] = None
    enable_default_allowlist: Optional[bool] = None
    custom_entities: Optional[str] = None
    pseudonymization_metadata: Optional[str] = None
    pseudonymization_secret: Optional[str] = None

    def validate(self) -> None:
        """Validate file source selection and pseudonymization constraints."""
        has_path = bool(self.file_path)
        has_content = self.file_content is not None
        if has_path == has_content:
            raise ValueError(
                "PseudonymizeFileRequest: provide exactly one of file_path or file_content"
            )
        _validate_entities(self.entities, "PseudonymizeFileRequest")
        if (
            self.pseudonymization_secret is not None
            and len(self.pseudonymization_secret) < 32
        ):
            raise ValueError(
                "PseudonymizeFileRequest: pseudonymization_secret must be at least 32 characters"
            )

    def to_form_fields(self) -> List[Tuple[str, str]]:
        """Serialize non-file fields for the multipart request."""
        fields: List[Tuple[str, str]] = []
        _append_common_form_fields(
            fields,
            entities=self.entities,
            anonymization_method_per_profile=self.anonymization_method_per_profile,
            allowlist=self.allowlist,
            enable_default_allowlist=self.enable_default_allowlist,
            custom_entities=self.custom_entities,
        )
        _append_form_value(
            fields,
            "pseudonymization-metadata",
            self.pseudonymization_metadata,
        )
        _append_form_value(
            fields,
            "pseudonymization-secret",
            self.pseudonymization_secret,
        )
        return fields

    def resolved_file_name(self) -> str:
        """Return the multipart filename sent to the service."""
        if self.file_name:
            return self.file_name
        if self.file_path:
            return os.path.basename(self.file_path)
        return "upload.zip"


AnonymizeRequest = AnonymizeTextRequest
"""Backward-compatible alias for `AnonymizeTextRequest`."""

PseudonymizeRequest = PseudonymizeTextRequest
"""Backward-compatible alias for `PseudonymizeTextRequest`."""


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass
class EntityMapping:
    """Single PII entity replaced during pseudonymization.

    Args:
        original: The original PII value detected in the input.
        pseudonym: The token that replaced it in the output.
        entity_type: Category of the entity (e.g. ``"PERSON"``, ``"EMAIL"``).
    """

    original: str
    pseudonym: str
    entity_type: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityMapping":
        return cls(
            original=data.get("original", ""),
            pseudonym=data.get("pseudonym", ""),
            entity_type=data.get("entity_type", data.get("entityType", "")),
        )


@dataclass
class AnonymizeResult:
    """Response from the anonymize endpoint.

    Args:
        result: The anonymized text with PII replaced by placeholders.
        raw: The raw response dict returned by the service (preserved for
             forward-compatibility with future service fields).
    """

    result: str
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnonymizeResult":
        return cls(result=data.get("result", ""), raw=data)


@dataclass
class PseudonymizeResult:
    """Response from the pseudonymize endpoint.

    Args:
        result: The pseudonymized text with PII replaced by tokens.
        metadata: List of entity mappings (original ↔ pseudonym).
        raw: The raw response dict returned by the service.
    """

    result: str
    metadata: List[EntityMapping] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PseudonymizeResult":
        raw_meta = data.get("metadata") or []
        metadata: List[EntityMapping] = []
        if isinstance(raw_meta, list):
            metadata = [
                EntityMapping.from_dict(m) for m in raw_meta if isinstance(m, dict)
            ]
        return cls(result=data.get("result", ""), metadata=metadata, raw=data)


@dataclass
class FileOperationResult:
    """Response from a file anonymization or pseudonymization endpoint.

    Attributes:
        result: Textual result when the service returns plain text or JSON.
        content: Raw binary payload, for example a ZIP response.
        content_type: Response content type returned by the service.
        filename: Filename parsed from the `Content-Disposition` header.
        raw: Parsed JSON payload when available for response inspection.
    """

    result: Optional[str] = None
    job_id: Optional[str] = None
    content: Optional[bytes] = None
    content_type: str = ""
    filename: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


AnonymizeFileResult = FileOperationResult
"""Alias for file anonymization responses."""

PseudonymizeFileResult = FileOperationResult
"""Alias for file pseudonymization responses."""
