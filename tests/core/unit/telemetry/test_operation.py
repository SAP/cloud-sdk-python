"""Tests for Operation enum."""

import pytest

from cloud_sdk_python.core.telemetry.operation import Operation


class TestOperation:
    """Test suite for Operation enum."""

    def test_auditlog_operations(self):
        """Test Audit Log operation values."""
        assert Operation.AUDITLOG_LOG.value == "log"
        assert Operation.AUDITLOG_LOG_BATCH.value == "log_batch"

    def test_destination_operations(self):
        """Test Destination operation values."""
        assert Operation.DESTINATION_GET_INSTANCE_DESTINATION.value == "get_instance_destination"
        assert Operation.DESTINATION_GET_SUBACCOUNT_DESTINATION.value == "get_subaccount_destination"
        assert Operation.DESTINATION_LIST_INSTANCE_DESTINATIONS.value == "list_instance_destinations"
        assert Operation.DESTINATION_LIST_SUBACCOUNT_DESTINATIONS.value == "list_subaccount_destinations"
        assert Operation.DESTINATION_CREATE_DESTINATION.value == "create_destination"
        assert Operation.DESTINATION_UPDATE_DESTINATION.value == "update_destination"
        assert Operation.DESTINATION_DELETE_DESTINATION.value == "delete_destination"

    def test_certificate_operations(self):
        """Test Certificate operation values."""
        assert Operation.CERTIFICATE_GET_INSTANCE_CERTIFICATE.value == "get_instance_certificate"
        assert Operation.CERTIFICATE_GET_SUBACCOUNT_CERTIFICATE.value == "get_subaccount_certificate"
        assert Operation.CERTIFICATE_LIST_INSTANCE_CERTIFICATES.value == "list_instance_certificates"
        assert Operation.CERTIFICATE_LIST_SUBACCOUNT_CERTIFICATES.value == "list_subaccount_certificates"
        assert Operation.CERTIFICATE_CREATE_CERTIFICATE.value == "create_certificate"
        assert Operation.CERTIFICATE_UPDATE_CERTIFICATE.value == "update_certificate"
        assert Operation.CERTIFICATE_DELETE_CERTIFICATE.value == "delete_certificate"

    def test_fragment_operations(self):
        """Test Fragment operation values."""
        assert Operation.FRAGMENT_GET_INSTANCE_FRAGMENT.value == "get_instance_fragment"
        assert Operation.FRAGMENT_GET_SUBACCOUNT_FRAGMENT.value == "get_subaccount_fragment"
        assert Operation.FRAGMENT_LIST_INSTANCE_FRAGMENTS.value == "list_instance_fragments"
        assert Operation.FRAGMENT_LIST_SUBACCOUNT_FRAGMENTS.value == "list_subaccount_fragments"
        assert Operation.FRAGMENT_CREATE_FRAGMENT.value == "create_fragment"
        assert Operation.FRAGMENT_UPDATE_FRAGMENT.value == "update_fragment"
        assert Operation.FRAGMENT_DELETE_FRAGMENT.value == "delete_fragment"

    def test_objectstore_operations(self):
        """Test Object Store operation values."""
        assert Operation.OBJECTSTORE_PUT_OBJECT.value == "put_object"
        assert Operation.OBJECTSTORE_PUT_OBJECT_FROM_FILE.value == "put_object_from_file"
        assert Operation.OBJECTSTORE_PUT_OBJECT_FROM_BYTES.value == "put_object_from_bytes"
        assert Operation.OBJECTSTORE_GET_OBJECT.value == "get_object"
        assert Operation.OBJECTSTORE_HEAD_OBJECT.value == "head_object"
        assert Operation.OBJECTSTORE_DELETE_OBJECT.value == "delete_object"
        assert Operation.OBJECTSTORE_LIST_OBJECTS.value == "list_objects"
        assert Operation.OBJECTSTORE_OBJECT_EXISTS.value == "object_exists"

    def test_aicore_operations(self):
        """Test AI Core operation values."""
        assert Operation.AICORE_SET_CONFIG.value == "set_aicore_config"
        assert Operation.AICORE_AUTO_INSTRUMENT.value == "auto_instrument"

    def test_operation_str_representation(self):
        """Test that Operation enum converts to string correctly."""
        assert str(Operation.AUDITLOG_LOG) == "log"
        assert str(Operation.DESTINATION_GET_INSTANCE_DESTINATION) == "get_instance_destination"
        assert str(Operation.OBJECTSTORE_PUT_OBJECT) == "put_object"
        assert str(Operation.AICORE_AUTO_INSTRUMENT) == "auto_instrument"

    def test_operation_is_string_enum(self):
        """Test that Operation enum inherits from str."""
        assert isinstance(Operation.AUDITLOG_LOG, str)
        assert isinstance(Operation.DESTINATION_CREATE_DESTINATION, str)
        assert isinstance(Operation.OBJECTSTORE_GET_OBJECT, str)

    def test_operation_equality(self):
        """Test Operation enum equality comparisons."""
        assert Operation.AUDITLOG_LOG == Operation.AUDITLOG_LOG
        assert Operation.AUDITLOG_LOG != Operation.AUDITLOG_LOG_BATCH
        assert Operation.AUDITLOG_LOG == "log"
        assert "log" == Operation.AUDITLOG_LOG

    def test_operation_in_collection(self):
        """Test Operation enum membership in collections."""
        operations = [Operation.AUDITLOG_LOG, Operation.OBJECTSTORE_PUT_OBJECT]
        assert Operation.AUDITLOG_LOG in operations
        assert Operation.DESTINATION_CREATE_DESTINATION not in operations

    def test_all_operations_have_unique_names(self):
        """Test that all operation enum members have unique names."""
        all_operations = list(Operation)
        operation_names = [op.name for op in all_operations]
        assert len(operation_names) == len(set(operation_names))

    def test_operation_iteration(self):
        """Test iterating over Operation enum."""
        all_operations = list(Operation)
        # Verify we have operations from all modules
        assert any("AUDITLOG" in op.name for op in all_operations)
        assert any("DESTINATION" in op.name for op in all_operations)
        assert any("CERTIFICATE" in op.name for op in all_operations)
        assert any("FRAGMENT" in op.name for op in all_operations)
        assert any("OBJECTSTORE" in op.name for op in all_operations)
        assert any("AICORE" in op.name for op in all_operations)

    def test_operation_count(self):
        """Test that we have the expected number of operations."""
        all_operations = list(Operation)
        # 2 auditlog + 8 destination + 7 certificate + 7 fragment + 8 objectstore + 2 aicore = 34
        assert len(all_operations) == 34