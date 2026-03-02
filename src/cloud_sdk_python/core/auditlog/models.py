"""Data models for SAP Audit Log Service.

This module provides dataclasses for constructing audit events that comply with
the SAP Audit Log Service OpenAPI specification. The module supports four main
types of audit events:

- SecurityEvent: Authentication, authorization, and security-related activities
- DataAccessEvent: Reading or accessing personal/sensitive data (GDPR compliance)
- DataModificationEvent: Creating, updating, or modifying personal/sensitive data
- DataDeletionEvent: Deleting personal/sensitive data (specialized for deletions)
- ConfigurationChangeEvent: System configuration and settings changes
- ConfigurationDeletionEvent: Deleting system configurations (specialized for deletions)

All events are Python dataclasses with built-in validation to ensure required
fields are present and properly formatted before sending to the audit service.

Example:
    from cloud_sdk_python.core.auditlog.models import SecurityEvent, Tenant
    
    event = SecurityEvent(
        data="User login attempt",
        user="john.doe",
        tenant=Tenant.PROVIDER
    )
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid
from datetime import datetime, timezone
import ipaddress


class Tenant(Enum):
    """Tenant identifier for audit log entries.
    
    Specifies whether the audit event originates from the service provider
    or a subscriber tenant in a multi-tenant environment.
    
    Attributes:
        PROVIDER: Event originates from the service provider ($PROVIDER)
        SUBSCRIBER: Event originates from a subscriber tenant ($SUBSCRIBER)
    """
    PROVIDER = "$PROVIDER"
    SUBSCRIBER = "$SUBSCRIBER"


@dataclass
class _BaseAuditEvent:
    """Base class for all audit events with common fields."""
    user: str = "$USER"
    tenant: Tenant = Tenant.PROVIDER
    custom_details: Optional[Dict[str, Any]] = None
    
    # Auto-generated fields
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Base serialization with common fields for all audit events."""
        return {
            "uuid": self.uuid,
            "user": self.user,
            "time": self.time,
            "tenant": self.tenant.value,
            "customDetails": self.custom_details
        }


@dataclass
class SecurityEventAttribute:
    """Represents an attribute in the attributes array for SecurityEvent logs.
    
    Used to provide additional context for security events with name-value pairs.
    Both name and value are required and must be non-empty strings.
    
    Args:
        name: The attribute name (required, non-empty string)
        value: The attribute value (required, non-empty string)
        
    Example:
        SecurityEventAttribute("login_method", "password")
        SecurityEventAttribute("failure_reason", "invalid_credentials")
    """
    name: str
    value: str

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("SecurityEventAttribute: name is required")
        if not self.value or not self.value.strip():
            raise ValueError("SecurityEventAttribute: value is required")


@dataclass
class DataAccessAttribute:
    """Represents an attribute in the attributes array for DataAccess logs.
    
    Used to specify which data attributes were accessed and whether the access
    was successful. The name is required, while successful is optional.
    
    Args:
        name: The name of the data attribute that was accessed (required)
        successful: Whether the access to this attribute was successful (optional)
        
    Example:
        DataAccessAttribute("email", successful=True)
        DataAccessAttribute("phone_number", successful=False)
        DataAccessAttribute("address")  # successful not specified
    """
    name: str
    successful: Optional[bool] = None

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("DataAccessAttribute: name is required")


@dataclass
class ChangeAttribute:
    """Represents an attribute in the attributes array for DataModification and ConfigurationChange logs.
    
    Used to track changes to data or configuration attributes, including old and new values.
    The name is required, while old and new values are optional.
    
    Args:
        name: The name of the attribute that was changed (required)
        new: The new value after the change (optional)
        old: The previous value before the change (optional)
        
    Example:
        ChangeAttribute("email", "new@example.com", "old@example.com")
        ChangeAttribute("status", "active", "inactive")
        ChangeAttribute("new_field", "value")  # old not specified for new fields
    """
    name: str
    new: Optional[str] = None
    old: Optional[str] = None

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("ChangeAttribute: name is required")

@dataclass
class DeletedAttribute:
    """Represents a deleted attribute with only name and old value.
    
    Used specifically for deletion events to track what was deleted.
    The name is required, while old value is optional.
    
    Args:
        name: The name of the attribute that was deleted (required)
        old: The value that was deleted (optional)
        
    Example:
        DeletedAttribute("email", "deleted@example.com")
        DeletedAttribute("phone_number", "+1234567890")
        DeletedAttribute("temp_field")  # old value not available
    """
    name: str
    old: Optional[str] = None

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("DeletedAttribute: name is required")

@dataclass
class SecurityEvent(_BaseAuditEvent):
    """Security event audit log message.

    Records authentication attempts, authorization failures, and other
    security-relevant activities. Used for tracking access control,
    authentication events, and security policy violations.

    Required fields:
        - data: Description of the security event (must not be empty)  

    Optional fields:
        - identity_provider: The identity provider used for authentication
        - ip: IP address of the client (must be valid IP if provided)
        - attributes: Additional security-related attributes
        - user: User identifier (defaults to "$USER")
        - tenant: Tenant context (defaults to Tenant.PROVIDER)
        - custom_details: Additional custom information

    Example:
        from cloud_sdk_python.core.auditlog.models import SecurityEvent, SecurityEventAttribute, Tenant
        
        event = SecurityEvent(
            data="User login attempt",
            user="john.doe",
            tenant=Tenant.PROVIDER,
            identity_provider="SAP ID",
            ip="192.168.1.100",
            attributes=[
                SecurityEventAttribute("login_method", "password"),
                SecurityEventAttribute("session_id", "abc123")
            ]
        )

    Raises:
        ValueError: If required fields are missing or invalid during validation
    """
    data: str = ""
    identity_provider: Optional[str] = None
    ip: Optional[str] = None
    attributes: Optional[List[SecurityEventAttribute]] = None

    def validate(self):
        """Validate the security event."""
        if not self.data or not self.data.strip() or self.data.strip() == "":
            raise ValueError("SecurityEvent data must not be empty")
        if self.ip is not None and self.ip.strip():
            try:
                ipaddress.ip_address(self.ip.strip())
            except ValueError:
                raise ValueError(f"SecurityEvent ip '{self.ip}' is not a valid IP address")
        if self.attributes:
            for attr in self.attributes:
                attr.validate()

    def to_dict(self) -> Dict[str, Any]:
       result = {
           **super().to_dict(),
           "data": self.data,
           "identityProvider": self.identity_provider,
           "ip": self.ip,
       }
       if self.attributes:
           result["attributes"] = [{"name": attr.name, "value": attr.value} for attr in self.attributes if attr.name and attr.value]

       return result


@dataclass
class DataAccessEvent(_BaseAuditEvent):
    """Data access event audit log message.

    Records when personal or sensitive data is read or accessed. This is particularly
    important for GDPR compliance and data privacy auditing, as it tracks who
    accessed what personal data and when.

    Required fields:
        - object_type: Type of the data object (e.g., "database", "file", "api")
        - object_id: Dictionary identifying the data object (e.g., {"table": "users"})
        - subject_type: Type of the data subject (e.g., "customer", "employee")
        - subject_id: Dictionary identifying the data subject (e.g., {"user_id": "123"})
        - attributes: List of data attributes that were accessed (at least one required)

    Optional fields:
        - subject_role: Role of the data subject (e.g., "customer", "employee")
        - identity_provider: The identity provider used for authentication
        - user: User identifier (defaults to "$USER")
        - tenant: Tenant context (defaults to Tenant.PROVIDER)
        - custom_details: Additional custom information

    Example:
        from cloud_sdk_python.core.auditlog.models import DataAccessEvent, DataAccessAttribute, Tenant
        
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "customers", "schema": "public"},
            subject_type="customer",
            subject_id={"customer_id": "12345"},
            subject_role="end_user",
            attributes=[
                DataAccessAttribute("email", successful=True),
                DataAccessAttribute("phone_number", successful=True),
                DataAccessAttribute("address", successful=False)
            ],
            user="service-account",
            tenant=Tenant.PROVIDER,
            identity_provider="OAuth2"
        )

    Raises:
        ValueError: If required fields are missing or invalid during validation
    """
    # Data object parameters
    object_type: Optional[str] = None
    object_id: Optional[Dict[str, str]] = None
    # Data subject parameters
    subject_type: Optional[str] = None
    subject_id: Optional[Dict[str, str]] = None
    subject_role: Optional[str] = None
    # Attributes
    attributes: List[DataAccessAttribute] = field(default_factory=list)
    identity_provider: Optional[str] = None

    def validate(self):
        """Validate the data access event."""
        if not self.object_type or not self.object_type.strip():
            raise ValueError("DataAccessEvent object_type must not be empty")
        if not self.object_id:
            raise ValueError("DataAccessEvent object_id must not be empty")
        if len(self.object_id) == 0:
            raise ValueError("DataAccessEvent object_id must not be empty")
        if not self.subject_type or not self.subject_type.strip():
            raise ValueError("DataAccessEvent subject_type must not be empty")
        if not self.subject_id:
            raise ValueError("DataAccessEvent subject_id must not be empty")
        if len(self.subject_id) == 0:
            raise ValueError("DataAccessEvent subject_id must not be empty")
        if len(self.attributes) == 0:
            raise ValueError("DataAccessEvent must have at least one attribute")
        for attr in self.attributes:
            attr.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            **super().to_dict(),
            "object": {
                "type": self.object_type,
                "id": self.object_id
            },
            "data_subject": {
                "type": self.subject_type,
                "id": self.subject_id,
                "role": self.subject_role
            },
            "identityProvider": self.identity_provider,
            "attributes": [{"name": attr.name, "successful": attr.successful} for attr in self.attributes]
        }


@dataclass
class DataModificationEvent(_BaseAuditEvent):
    """Data modification event audit log message.

    Records when personal or sensitive data is created, updated, or deleted.
    This is essential for GDPR compliance and data change tracking, providing
    an audit trail of what data was modified, including old and new values.

    Required fields:
        - object_type: Type of the data object (e.g., "user_profile", "customer_record")
        - object_id: Dictionary identifying the data object (e.g., {"profile_id": "123"})
        - subject_type: Type of the data subject (e.g., "user", "customer")
        - subject_id: Dictionary identifying the data subject (e.g., {"user_id": "456"})
        - attributes: List of attributes that were modified (at least one required)

    Optional fields:
        - subject_role: Role of the data subject (e.g., "customer", "employee")
        - user: User identifier (defaults to "$USER")
        - tenant: Tenant context (defaults to Tenant.PROVIDER)
        - custom_details: Additional custom information

    Example:
        from cloud_sdk_python.core.auditlog.models import DataModificationEvent, ChangeAttribute, Tenant
        
        event = DataModificationEvent(
            object_type="user_profile",
            object_id={"profile_id": "profile-123"},
            subject_type="user",
            subject_id={"user_id": "user-456"},
            subject_role="customer",
            attributes=[
                ChangeAttribute("email", "new@example.com", "old@example.com"),
                ChangeAttribute("phone", "+0987654321", "+1234567890"),
                ChangeAttribute("status", "active", "inactive")
            ],
            user="admin-user",
            tenant=Tenant.PROVIDER
        )

    Raises:
        ValueError: If required fields are missing or invalid during validation
    """
    # Data object parameters
    object_type: Optional[str] = None
    object_id: Optional[Dict[str, str]] = None
    # Data subject parameters
    subject_type: Optional[str] = None
    subject_id: Optional[Dict[str, str]] = None
    subject_role: Optional[str] = None
    # Attributes
    attributes: List[ChangeAttribute] = field(default_factory=list)

    def validate(self):
        """Validate the data modification event."""
        if not self.object_type or not self.object_type.strip():
            raise ValueError("DataModificationEvent object_type must not be empty")
        if not self.object_id:
            raise ValueError("DataModificationEvent object_id must not be empty")
        if len(self.object_id) == 0:
            raise ValueError("DataModificationEvent object_id must not be empty")
        if not self.subject_type or not self.subject_type.strip():
            raise ValueError("DataModificationEvent subject_type must not be empty")
        if not self.subject_id:
            raise ValueError("DataModificationEvent subject_id must not be empty")
        if len(self.subject_id) == 0:
            raise ValueError("DataModificationEvent subject_id must not be empty")
        if len(self.attributes) == 0:
            raise ValueError("DataModificationEvent must have at least one attribute")
        for attr in self.attributes:
            attr.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            **super().to_dict(),
            "object": {
                "type": self.object_type,
                "id": self.object_id
            },
            "data_subject": {
                "type": self.subject_type,
                "id": self.subject_id,
                "role": self.subject_role
            },
            "attributes": [{"name": attr.name, "new": attr.new, "old": attr.old} for attr in self.attributes]
        }


@dataclass
class ConfigurationChangeEvent(_BaseAuditEvent):
    """Configuration change event audit log message.

    Records when system configurations, settings, or other non-personal data is modified.
    This event type is used for tracking changes to application settings, system
    parameters, feature flags, and other configuration data that affects system behavior.

    Required fields:
        - object_type: Type of the configuration object (e.g., "system_config", "feature_flag")
        - object_id: Dictionary identifying the configuration object (e.g., {"setting": "timeout"})
        - attributes: List of configuration attributes that were changed (at least one required)

    Optional fields:
        - id: Additional identifier for the configuration change event
        - user: User identifier (defaults to "$USER")
        - tenant: Tenant context (defaults to Tenant.PROVIDER)
        - custom_details: Additional custom information

    Example:
        from cloud_sdk_python.core.auditlog.models import ConfigurationChangeEvent, ChangeAttribute, Tenant
        
        event = ConfigurationChangeEvent(
            object_type="system_config",
            object_id={"component": "authentication", "setting": "timeout"},
            attributes=[
                ChangeAttribute("session_timeout", "60", "30"),
                ChangeAttribute("max_attempts", "5", "3")
            ],
            user="system-admin",
            tenant=Tenant.PROVIDER,
            id="config-change-001"
        )

    Raises:
        ValueError: If required fields are missing or invalid during validation
    """
    # Data object parameters
    object_type: Optional[str] = None
    object_id: Optional[Dict[str, str]] = None
    # Attributes
    attributes: List[ChangeAttribute] = field(default_factory=list)
    id: Optional[str] = None

    def validate(self):
        """Validate the configuration change event."""
        if not self.object_type or not self.object_type.strip():
            raise ValueError("ConfigurationChangeEvent object_type must not be empty")
        if not self.object_id:
            raise ValueError("ConfigurationChangeEvent object_id must not be empty")
        if len(self.object_id) == 0:
            raise ValueError("ConfigurationChangeEvent object_id must not be empty")
        if len(self.attributes) == 0:
            raise ValueError("ConfigurationChangeEvent must have at least one attribute")
        for attr in self.attributes:
            attr.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            **super().to_dict(),
            "object": {
                "type": self.object_type,
                "id": self.object_id
            },
            "id": self.id,
            "attributes": [{"name": attr.name, "new": attr.new, "old": attr.old} for attr in self.attributes]
        }


@dataclass
class DataDeletionEvent(DataModificationEvent):
    """Data deletion event audit log message.

    Records when personal or sensitive data is deleted from the system.
    This is essential for GDPR compliance and data lifecycle tracking, providing
    an audit trail of what personal data was removed and when.

    Required fields:
        - object_type: Type of the data object (e.g., "user_profile", "customer_record")
        - object_id: Dictionary identifying the data object (e.g., {"profile_id": "123"})
        - subject_type: Type of the data subject (e.g., "user", "customer")
        - subject_id: Dictionary identifying the data subject (e.g., {"user_id": "456"})
        - attributes: List of attributes that were deleted (at least one required)

    Optional fields:
        - subject_role: Role of the data subject (e.g., "customer", "employee")
        - user: User identifier (defaults to "$USER")
        - tenant: Tenant context (defaults to Tenant.PROVIDER)
        - custom_details: Additional custom information

    Example:
        from cloud_sdk_python.core.auditlog.models import DataDeletionEvent, DeletedAttribute, Tenant
        
        event = DataDeletionEvent(
            object_type="user_profile",
            object_id={"profile_id": "profile-123"},
            subject_type="user",
            subject_id={"user_id": "user-456"},
            subject_role="customer",
            attributes=[
                DeletedAttribute("email", "deleted@example.com"),
                DeletedAttribute("phone", "+1234567890"),
                DeletedAttribute("personal_notes")
            ],
            user="admin-user",
            tenant=Tenant.PROVIDER
        )

    Raises:
        ValueError: If required fields are missing or invalid during validation
    """
    # Override the attributes field to use DeletedAttribute instead of ChangeAttribute
    attributes: List[DeletedAttribute] = field(default_factory=list)

    def validate(self):
        """Validate the data deletion event - override parent validation."""
        if not self.object_type or not self.object_type.strip():
            raise ValueError("DataDeletionEvent object_type must not be empty")
        if not self.object_id:
            raise ValueError("DataDeletionEvent object_id must not be empty")
        if len(self.object_id) == 0:
            raise ValueError("DataDeletionEvent object_id must not be empty")
        if not self.subject_type or not self.subject_type.strip():
            raise ValueError("DataDeletionEvent subject_type must not be empty")
        if not self.subject_id:
            raise ValueError("DataDeletionEvent subject_id must not be empty")
        if len(self.subject_id) == 0:
            raise ValueError("DataDeletionEvent subject_id must not be empty")
        if len(self.attributes) == 0:
            raise ValueError("DataDeletionEvent must have at least one attribute")
        for attr in self.attributes:
            attr.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization - override for DeletedAttribute."""
        return {
            **_BaseAuditEvent.to_dict(self),
            "object": {
                "type": self.object_type,
                "id": self.object_id
            },
            "data_subject": {
                "type": self.subject_type,
                "id": self.subject_id,
                "role": self.subject_role
            },
            "attributes": [{"name": attr.name, "old": attr.old, "new": None} for attr in self.attributes]
        }


@dataclass
class ConfigurationDeletionEvent(ConfigurationChangeEvent):
    """Configuration deletion event audit log message.

    Records when system configurations, settings, or other non-personal data is deleted
    from the system. This event type is used for tracking removal of application settings,
    system parameters, feature flags, and other configuration data that affects system behavior.

    Required fields:
        - object_type: Type of the configuration object (e.g., "system_config", "feature_flag")
        - object_id: Dictionary identifying the configuration object (e.g., {"setting": "timeout"})
        - attributes: List of configuration attributes that were deleted (at least one required)

    Optional fields:
        - id: Additional identifier for the configuration deletion event
        - user: User identifier (defaults to "$USER")
        - tenant: Tenant context (defaults to Tenant.PROVIDER)
        - custom_details: Additional custom information

    Example:
        from cloud_sdk_python.core.auditlog.models import ConfigurationDeletionEvent, DeletedAttribute, Tenant
        
        event = ConfigurationDeletionEvent(
            object_type="feature_flag",
            object_id={"component": "ui", "flag": "new_dashboard"},
            attributes=[
                DeletedAttribute("enabled", "true"),
                DeletedAttribute("rollout_percentage", "50"),
                DeletedAttribute("target_users")
            ],
            user="system-admin",
            tenant=Tenant.PROVIDER,
            id="config-deletion-001"
        )

    Raises:
        ValueError: If required fields are missing or invalid during validation
    """
    # Override the attributes field to use DeletedAttribute instead of ChangeAttribute
    attributes: List[DeletedAttribute] = field(default_factory=list)

    def validate(self):
        """Validate the configuration deletion event - override parent validation."""
        if not self.object_type or not self.object_type.strip():
            raise ValueError("ConfigurationDeletionEvent object_type must not be empty")
        if not self.object_id:
            raise ValueError("ConfigurationDeletionEvent object_id must not be empty")
        if len(self.object_id) == 0:
            raise ValueError("ConfigurationDeletionEvent object_id must not be empty")
        if len(self.attributes) == 0:
            raise ValueError("ConfigurationDeletionEvent must have at least one attribute")
        for attr in self.attributes:
            attr.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization - override for DeletedAttribute."""
        return {
            **_BaseAuditEvent.to_dict(self),
            "object": {
                "type": self.object_type,
                "id": self.object_id
            },
            "id": self.id,
            "attributes": [{"name": attr.name, "old": attr.old, "new": None} for attr in self.attributes]
        }


@dataclass
class FailedMessage:
    """Represents an audit message that failed to be logged.
    
    Used by the audit client's batch logging functionality to return information
    about events that could not be successfully logged, along with the error details.
    
    Args:
        message: The original audit event that failed to be logged
        error: Description of the error that occurred during logging
        
    Example:
        When batch logging fails, you can handle failed messages:
        
        failed_messages = client.log_batch(events)
        for failed in failed_messages:
            print(f"Failed to log {type(failed.message).__name__}: {failed.error}")
    """
    message: Union[SecurityEvent, DataAccessEvent, DataModificationEvent, ConfigurationChangeEvent, DataDeletionEvent, ConfigurationDeletionEvent]
    error: str
