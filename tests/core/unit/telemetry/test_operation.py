"""Tests for Operation enum."""

import pytest

from sap_cloud_sdk.core.telemetry.operation import Operation


class TestOperation:
    """Test suite for Operation enum."""

    def test_auditlog_operations(self):
        """Test Audit Log operation values."""
        assert Operation.AUDITLOG_LOG.value == "log"
        assert Operation.AUDITLOG_LOG_BATCH.value == "log_batch"
        assert Operation.AUDITLOG_CREATE_CLIENT.value == "create_client"

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

    def test_dms_operations(self):
        """Test DMS operation values."""
        assert Operation.DMS_ONBOARD_REPOSITORY.value == "onboard_repository"
        assert Operation.DMS_GET_REPOSITORY.value == "get_repository"
        assert Operation.DMS_GET_ALL_REPOSITORIES.value == "get_all_repositories"
        assert Operation.DMS_UPDATE_REPOSITORY.value == "update_repository"
        assert Operation.DMS_DELETE_REPOSITORY.value == "delete_repository"
        assert Operation.DMS_CREATE_CONFIG.value == "create_config"
        assert Operation.DMS_GET_CONFIGS.value == "get_configs"
        assert Operation.DMS_UPDATE_CONFIG.value == "update_config"
        assert Operation.DMS_DELETE_CONFIG.value == "delete_config"
        assert Operation.DMS_CREATE_FOLDER.value == "cmis_create_folder"
        assert Operation.DMS_CREATE_DOCUMENT.value == "cmis_create_document"
        assert Operation.DMS_CHECK_OUT.value == "cmis_check_out"
        assert Operation.DMS_CHECK_IN.value == "cmis_check_in"
        assert Operation.DMS_CANCEL_CHECK_OUT.value == "cmis_cancel_check_out"
        assert Operation.DMS_APPLY_ACL.value == "cmis_apply_acl"
        assert Operation.DMS_GET_OBJECT.value == "cmis_get_object"
        assert Operation.DMS_GET_CONTENT.value == "cmis_get_content"
        assert Operation.DMS_UPDATE_PROPERTIES.value == "cmis_update_properties"
        assert Operation.DMS_GET_CHILDREN.value == "cmis_get_children"
        assert Operation.DMS_DELETE_OBJECT.value == "cmis_delete_object"
        assert Operation.DMS_RESTORE_OBJECT.value == "cmis_restore_object"
        assert Operation.DMS_APPEND_CONTENT_STREAM.value == "cmis_append_content_stream"
        assert Operation.DMS_CMIS_QUERY.value == "cmis_query"

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
        # 3 auditlog + 11 destination + 10 certificate + 10 fragment
        # + 8 objectstore + 2 aicore + 23 dms + 13 agent_memory = 80
        assert len(all_operations) == 80
