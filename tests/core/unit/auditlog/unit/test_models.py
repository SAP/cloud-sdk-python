"""Tests for audit log data models."""

from datetime import datetime, timezone
import pytest
import uuid

from cloud_sdk_python.core.auditlog.models import (
    Tenant,
    _BaseAuditEvent,
    SecurityEvent,
    SecurityEventAttribute,
    DataAccessEvent,
    DataAccessAttribute,
    DataModificationEvent,
    ChangeAttribute,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    DeletedAttribute,
    ConfigurationDeletionEvent,
    FailedMessage
)


class TestTenant:

    def test_enum_values(self):
        assert Tenant.PROVIDER.value == "$PROVIDER"
        assert Tenant.SUBSCRIBER.value == "$SUBSCRIBER"

    def test_enum_comparison(self):
        assert Tenant.PROVIDER == Tenant.PROVIDER
        assert Tenant.PROVIDER != Tenant.SUBSCRIBER


class TestBaseAuditEvent:

    def test_default_initialization(self):
        event = _BaseAuditEvent()
        assert event.user == "$USER"
        assert event.tenant == Tenant.PROVIDER
        assert event.custom_details is None
        assert isinstance(event.uuid, str)
        assert isinstance(event.time, str)

    def test_custom_initialization(self):
        custom_details = {"key": "value"}
        event = _BaseAuditEvent(
            user="test_user",
            tenant=Tenant.SUBSCRIBER,
            custom_details=custom_details
        )
        assert event.user == "test_user"
        assert event.tenant == Tenant.SUBSCRIBER
        assert event.custom_details == custom_details

    def test_uuid_generation(self):
        event1 = _BaseAuditEvent()
        event2 = _BaseAuditEvent()
        assert event1.uuid != event2.uuid
        assert uuid.UUID(event1.uuid)
        assert uuid.UUID(event2.uuid)

    def test_time_generation(self):
        event = _BaseAuditEvent()
        assert event.time.endswith("Z")
        datetime.fromisoformat(event.time.replace("Z", "+00:00"))

    def test_to_dict(self):
        event = _BaseAuditEvent(
            user="test_user",
            tenant=Tenant.SUBSCRIBER,
            custom_details={"test": "data"}
        )
        result = event.to_dict()
        
        assert result["user"] == "test_user"
        assert result["tenant"] == "$SUBSCRIBER"
        assert result["customDetails"] == {"test": "data"}
        assert "uuid" in result
        assert "time" in result

    def test_to_dict_no_custom_details(self):
        event = _BaseAuditEvent(user="test_user")
        result = event.to_dict()
        
        assert result["customDetails"] is None
        assert result["user"] == "test_user"


class TestSecurityEventAttribute:

    def test_creation(self):
        attr = SecurityEventAttribute("login_method", "password")
        assert attr.name == "login_method"
        assert attr.value == "password"

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(SecurityEventAttribute)


class TestDataAccessAttribute:

    def test_creation_with_successful(self):
        attr = DataAccessAttribute("email", successful=True)
        assert attr.name == "email"
        assert attr.successful is True

    def test_creation_without_successful(self):
        attr = DataAccessAttribute("phone")
        assert attr.name == "phone"
        assert attr.successful is None

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(DataAccessAttribute)


class TestChangeAttribute:

    def test_creation_full(self):
        attr = ChangeAttribute("email", "new@example.com", "old@example.com")
        assert attr.name == "email"
        assert attr.new == "new@example.com"
        assert attr.old == "old@example.com"

    def test_creation_partial(self):
        attr = ChangeAttribute("status", new="active")
        assert attr.name == "status"
        assert attr.new == "active"
        assert attr.old is None

    def test_creation_name_only(self):
        attr = ChangeAttribute("field")
        assert attr.name == "field"
        assert attr.new is None
        assert attr.old is None

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(ChangeAttribute)


class TestDeletedAttribute:

    def test_creation_with_old(self):
        attr = DeletedAttribute("email", "deleted@example.com")
        assert attr.name == "email"
        assert attr.old == "deleted@example.com"

    def test_creation_without_old(self):
        attr = DeletedAttribute("temp_field")
        assert attr.name == "temp_field"
        assert attr.old is None

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(DeletedAttribute)


class TestSecurityEvent:

    def test_minimal_valid_event(self):
        event = SecurityEvent(data="Login attempt")
        assert event.data == "Login attempt"
        assert event.identity_provider is None
        assert event.ip is None
        assert event.attributes is None

    def test_full_event(self):
        attributes = [SecurityEventAttribute("method", "password")]
        event = SecurityEvent(
            data="Login successful",
            identity_provider="SAP ID",
            ip="192.168.1.1",
            attributes=attributes,
            user="john.doe"
        )
        assert event.data == "Login successful"
        assert event.identity_provider == "SAP ID"
        assert event.ip == "192.168.1.1"
        assert event.attributes == attributes
        assert event.user == "john.doe"

    def test_validate_success(self):
        event = SecurityEvent(data="Valid event")
        event.validate()

    def test_validate_empty_data(self):
        event = SecurityEvent(data="")
        with pytest.raises(ValueError, match="SecurityEvent data must not be empty"):
            event.validate()

    def test_validate_none_data(self):
        event = SecurityEvent(data=None)
        with pytest.raises(ValueError, match="SecurityEvent data must not be empty"):
            event.validate()

    def test_validate_whitespace_data(self):
        event = SecurityEvent(data="   ")
        with pytest.raises(ValueError, match="SecurityEvent data must not be empty"):
            event.validate()

    def test_validate_valid_ip(self):
        event = SecurityEvent(data="Test", ip="192.168.1.1")
        event.validate()

    def test_validate_valid_ipv6(self):
        event = SecurityEvent(data="Test", ip="2001:db8::1")
        event.validate()

    def test_validate_invalid_ip(self):
        event = SecurityEvent(data="Test", ip="invalid-ip")
        with pytest.raises(ValueError, match="is not a valid IP address"):
            event.validate()

    def test_validate_empty_ip_allowed(self):
        event = SecurityEvent(data="Test", ip="")
        event.validate()

    def test_validate_attributes_success(self):
        attributes = [SecurityEventAttribute("method", "password")]
        event = SecurityEvent(data="Test", attributes=attributes)
        event.validate()

    def test_validate_attributes_empty_name(self):
        attributes = [SecurityEventAttribute("", "password")]
        event = SecurityEvent(data="Test", attributes=attributes)
        with pytest.raises(ValueError, match="SecurityEventAttribute: name is required"):
            event.validate()

    def test_validate_attributes_empty_value(self):
        attributes = [SecurityEventAttribute("method", "")]
        event = SecurityEvent(data="Test", attributes=attributes)
        with pytest.raises(ValueError, match="SecurityEventAttribute: value is required"):
            event.validate()

    def test_validate_attributes_whitespace_name(self):
        attributes = [SecurityEventAttribute("   ", "password")]
        event = SecurityEvent(data="Test", attributes=attributes)
        with pytest.raises(ValueError, match="SecurityEventAttribute: name is required"):
            event.validate()

    def test_validate_multiple_attributes(self):
        attributes = [
            SecurityEventAttribute("method", "password"),
            SecurityEventAttribute("", "value")
        ]
        event = SecurityEvent(data="Test", attributes=attributes)
        with pytest.raises(ValueError, match="SecurityEventAttribute: name is required"):
            event.validate()

    def test_to_dict(self):
        attributes = [SecurityEventAttribute("method", "password")]
        event = SecurityEvent(
            data="Login",
            identity_provider="SAP ID",
            ip="192.168.1.1",
            attributes=attributes
        )
        result = event.to_dict()
        
        assert result["data"] == "Login"
        assert result["identityProvider"] == "SAP ID"
        assert result["ip"] == "192.168.1.1"
        assert result["attributes"] == [{"name": "method", "value": "password"}]

    def test_to_dict_minimal(self):
        event = SecurityEvent(data="Login")
        result = event.to_dict()
        assert result["data"] == "Login"
        assert result["identityProvider"] is None
        assert result["ip"] is None


class TestDataAccessEvent:

    def test_minimal_valid_event(self):
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[DataAccessAttribute("email")]
        )
        assert event.object_type == "database"
        assert event.subject_type == "user"

    def test_validate_success(self):
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[DataAccessAttribute("email")]
        )
        event.validate()

    def test_validate_empty_object_type(self):
        event = DataAccessEvent(
            object_type="",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[DataAccessAttribute("email")]
        )
        with pytest.raises(ValueError, match="object_type must not be empty"):
            event.validate()

    def test_validate_none_object_id(self):
        event = DataAccessEvent(
            object_type="database",
            object_id=None,
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[DataAccessAttribute("email")]
        )
        with pytest.raises(ValueError, match="object_id must not be empty"):
            event.validate()

    def test_validate_empty_object_id(self):
        event = DataAccessEvent(
            object_type="database",
            object_id={},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[DataAccessAttribute("email")]
        )
        with pytest.raises(ValueError, match="object_id must not be empty"):
            event.validate()

    def test_validate_no_attributes(self):
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[]
        )
        with pytest.raises(ValueError, match="must have at least one attribute"):
            event.validate()

    def test_validate_attribute_empty_name(self):
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[DataAccessAttribute("")]
        )
        with pytest.raises(ValueError, match="DataAccessAttribute: name is required"):
            event.validate()

    def test_to_dict(self):
        attributes = [DataAccessAttribute("email", successful=True)]
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            subject_role="customer",
            attributes=attributes,
            identity_provider="OAuth2"
        )
        result = event.to_dict()
        
        assert result["object"] == {"type": "database", "id": {"table": "users"}}
        assert result["data_subject"] == {
            "type": "user",
            "id": {"id": "123"},
            "role": "customer"
        }
        assert result["identityProvider"] == "OAuth2"
        assert result["attributes"] == [{"name": "email", "successful": True}]

    def test_to_dict_minimal(self):
        attributes = [DataAccessAttribute("email")]
        event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=attributes
        )
        result = event.to_dict()
        
        assert result["identityProvider"] is None
        assert result["attributes"] == [{"name": "email", "successful": None}]


class TestDataModificationEvent:

    def test_validate_success(self):
        event = DataModificationEvent(
            object_type="profile",
            object_id={"id": "123"},
            subject_type="user",
            subject_id={"id": "456"},
            attributes=[ChangeAttribute("email", "new@example.com")]
        )
        event.validate()

    def test_validate_attribute_empty_name(self):
        event = DataModificationEvent(
            object_type="profile",
            object_id={"id": "123"},
            subject_type="user",
            subject_id={"id": "456"},
            attributes=[ChangeAttribute("", "new@example.com")]
        )
        with pytest.raises(ValueError, match="ChangeAttribute: name is required"):
            event.validate()

    def test_to_dict(self):
        attributes = [ChangeAttribute("email", "new@example.com", "old@example.com")]
        event = DataModificationEvent(
            object_type="profile",
            object_id={"id": "123"},
            subject_type="user",
            subject_id={"id": "456"},
            attributes=attributes
        )
        result = event.to_dict()
        
        assert result["attributes"] == [{
            "name": "email",
            "new": "new@example.com",
            "old": "old@example.com"
        }]


class TestConfigurationChangeEvent:

    def test_validate_success(self):
        event = ConfigurationChangeEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=[ChangeAttribute("value", "60")]
        )
        event.validate()

    def test_validate_attribute_empty_name(self):
        event = ConfigurationChangeEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=[ChangeAttribute("", "60")]
        )
        with pytest.raises(ValueError, match="ChangeAttribute: name is required"):
            event.validate()

    def test_to_dict_with_id(self):
        attributes = [ChangeAttribute("timeout", "60", "30")]
        event = ConfigurationChangeEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=attributes,
            id="config-change-001"
        )
        result = event.to_dict()
        
        assert result["id"] == "config-change-001"
        assert result["object"] == {"type": "config", "id": {"setting": "timeout"}}

    def test_to_dict_no_id(self):
        attributes = [ChangeAttribute("timeout", "60", "30")]
        event = ConfigurationChangeEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=attributes
        )
        result = event.to_dict()
        
        assert result["id"] is None
        assert result["object"] == {"type": "config", "id": {"setting": "timeout"}}


class TestDataDeletionEvent:

    def test_validate_success(self):
        event = DataDeletionEvent(
            object_type="profile",
            object_id={"id": "123"},
            subject_type="user", 
            subject_id={"id": "456"},
            attributes=[DeletedAttribute("email", "deleted@example.com")]
        )
        event.validate()

    def test_validate_attribute_empty_name(self):
        event = DataDeletionEvent(
            object_type="profile",
            object_id={"id": "123"},
            subject_type="user",
            subject_id={"id": "456"},
            attributes=[DeletedAttribute("", "deleted@example.com")]
        )
        with pytest.raises(ValueError, match="DeletedAttribute: name is required"):
            event.validate()

    def test_to_dict(self):
        attributes = [DeletedAttribute("email", "deleted@example.com")]
        event = DataDeletionEvent(
            object_type="profile",
            object_id={"id": "123"},
            subject_type="user",
            subject_id={"id": "456"},
            attributes=attributes
        )
        result = event.to_dict()
        
        assert result["attributes"] == [{
            "name": "email",
            "old": "deleted@example.com",
            "new": None
        }]


class TestConfigurationDeletionEvent:

    def test_validate_success(self):
        event = ConfigurationDeletionEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=[DeletedAttribute("value", "30")]
        )
        event.validate()

    def test_validate_attribute_empty_name(self):
        event = ConfigurationDeletionEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=[DeletedAttribute("", "30")]
        )
        with pytest.raises(ValueError, match="DeletedAttribute: name is required"):
            event.validate()

    def test_to_dict(self):
        attributes = [DeletedAttribute("timeout", "30")]
        event = ConfigurationDeletionEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=attributes,
            id="config-deletion-001"
        )
        result = event.to_dict()
        
        assert result["id"] == "config-deletion-001"
        assert result["attributes"] == [{
            "name": "timeout",
            "old": "30",
            "new": None
        }]

    def test_to_dict_no_id(self):
        attributes = [DeletedAttribute("timeout", "30")]
        event = ConfigurationDeletionEvent(
            object_type="config",
            object_id={"setting": "timeout"},
            attributes=attributes
        )
        result = event.to_dict()
        
        assert result["id"] is None
        assert result["attributes"] == [{
            "name": "timeout",
            "old": "30",
            "new": None
        }]


class TestFailedMessage:

    def test_creation(self):
        event = SecurityEvent(data="Test")
        failed = FailedMessage(message=event, error="Network error")
        assert failed.message == event
        assert failed.error == "Network error"

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(FailedMessage)
