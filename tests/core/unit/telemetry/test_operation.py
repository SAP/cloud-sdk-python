"""Tests for Operation enum."""

from sap_cloud_sdk.core.telemetry.operation import Operation


class TestOperation:
    """Test suite for Operation enum."""

    def test_auditlog_operations(self):
        """Test Audit Log operation values."""
        assert Operation.AUDITLOG_LOG.value == "log"
        assert Operation.AUDITLOG_LOG_BATCH.value == "log_batch"
        assert Operation.AUDITLOG_CREATE_CLIENT.value == "create_client"

    def test_data_anonymization_operations(self):
        """Test Data Anonymization operation values."""
        assert (
            Operation.DATA_ANONYMIZATION_CREATE_CLIENT.value
            == "create_data_anonymization_client"
        )
        assert (
            Operation.DATA_ANONYMIZATION_ANONYMIZE_TEXT.value == "anonymize_text"
        )
        assert (
            Operation.DATA_ANONYMIZATION_ANONYMIZE_FILE.value == "anonymize_file"
        )
        assert (
            Operation.DATA_ANONYMIZATION_PSEUDONYMIZE_TEXT.value
            == "pseudonymize_text"
        )
        assert (
            Operation.DATA_ANONYMIZATION_PSEUDONYMIZE_FILE.value
            == "pseudonymize_file"
        )

    def test_destination_operations(self):
        """Test Destination operation values."""
        assert (
            Operation.DESTINATION_GET_INSTANCE_DESTINATION.value
            == "get_instance_destination"
        )
        assert (
            Operation.DESTINATION_GET_SUBACCOUNT_DESTINATION.value
            == "get_subaccount_destination"
        )
        assert (
            Operation.DESTINATION_LIST_INSTANCE_DESTINATIONS.value
            == "list_instance_destinations"
        )
        assert (
            Operation.DESTINATION_LIST_SUBACCOUNT_DESTINATIONS.value
            == "list_subaccount_destinations"
        )
        assert Operation.DESTINATION_CREATE_DESTINATION.value == "create_destination"
        assert Operation.DESTINATION_UPDATE_DESTINATION.value == "update_destination"
        assert Operation.DESTINATION_DELETE_DESTINATION.value == "delete_destination"
        assert (
            Operation.DESTINATION_GET_SERVICE_INSTANCE_ID.value
            == "get_service_instance_id"
        )

    def test_certificate_operations(self):
        """Test Certificate operation values."""
        assert (
            Operation.CERTIFICATE_GET_INSTANCE_CERTIFICATE.value
            == "get_instance_certificate"
        )
        assert (
            Operation.CERTIFICATE_GET_SUBACCOUNT_CERTIFICATE.value
            == "get_subaccount_certificate"
        )
        assert (
            Operation.CERTIFICATE_LIST_INSTANCE_CERTIFICATES.value
            == "list_instance_certificates"
        )
        assert (
            Operation.CERTIFICATE_LIST_SUBACCOUNT_CERTIFICATES.value
            == "list_subaccount_certificates"
        )
        assert Operation.CERTIFICATE_CREATE_CERTIFICATE.value == "create_certificate"
        assert Operation.CERTIFICATE_UPDATE_CERTIFICATE.value == "update_certificate"
        assert Operation.CERTIFICATE_DELETE_CERTIFICATE.value == "delete_certificate"

    def test_fragment_operations(self):
        """Test Fragment operation values."""
        assert Operation.FRAGMENT_GET_INSTANCE_FRAGMENT.value == "get_instance_fragment"
        assert (
            Operation.FRAGMENT_GET_SUBACCOUNT_FRAGMENT.value
            == "get_subaccount_fragment"
        )
        assert (
            Operation.FRAGMENT_LIST_INSTANCE_FRAGMENTS.value
            == "list_instance_fragments"
        )
        assert (
            Operation.FRAGMENT_LIST_SUBACCOUNT_FRAGMENTS.value
            == "list_subaccount_fragments"
        )
        assert Operation.FRAGMENT_CREATE_FRAGMENT.value == "create_fragment"
        assert Operation.FRAGMENT_UPDATE_FRAGMENT.value == "update_fragment"
        assert Operation.FRAGMENT_DELETE_FRAGMENT.value == "delete_fragment"

    def test_objectstore_operations(self):
        """Test Object Store operation values."""
        assert Operation.OBJECTSTORE_PUT_OBJECT.value == "put_object"
        assert (
            Operation.OBJECTSTORE_PUT_OBJECT_FROM_FILE.value == "put_object_from_file"
        )
        assert (
            Operation.OBJECTSTORE_PUT_OBJECT_FROM_BYTES.value == "put_object_from_bytes"
        )
        assert Operation.OBJECTSTORE_GET_OBJECT.value == "get_object"
        assert Operation.OBJECTSTORE_HEAD_OBJECT.value == "head_object"
        assert Operation.OBJECTSTORE_DELETE_OBJECT.value == "delete_object"
        assert Operation.OBJECTSTORE_LIST_OBJECTS.value == "list_objects"
        assert Operation.OBJECTSTORE_OBJECT_EXISTS.value == "object_exists"

    def test_aicore_operations(self):
        """Test AI Core operation values."""
        assert Operation.AICORE_SET_CONFIG.value == "set_aicore_config"
        assert Operation.AICORE_AUTO_INSTRUMENT.value == "auto_instrument"

    def test_extensibility_operations(self):
        """Test Extensibility operation values."""
        assert (
            Operation.EXTENSIBILITY_GET_EXTENSION_CAPABILITY_IMPLEMENTATION.value
            == "get_extension_capability_implementation"
        )
        assert Operation.EXTENSIBILITY_CALL_HOOK.value == "call_hook"

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

    def test_print_operations(self):
        """Test Print operation values."""
        assert Operation.PRINT_CREATE_CLIENT.value == "print_create_client"
        assert Operation.PRINT_LIST_QUEUES.value == "list_queues"
        assert Operation.PRINT_CREATE_QUEUE.value == "create_queue"
        assert Operation.PRINT_GET_PROFILES.value == "get_print_profiles"
        assert Operation.PRINT_UPLOAD_DOCUMENT.value == "upload_document"
        assert Operation.PRINT_CREATE_TASK.value == "create_print_task"

    def test_dpi_ng_consent_operations(self):
        """Test DPI NG Consent operation values."""
        assert Operation.DPI_NG_CONSENT_CREATE_CLIENT.value == "consent_create_client"
        assert Operation.DPI_NG_CONSENT_LIST_CONSENTS.value == "consent_list_consents"
        assert Operation.DPI_NG_CONSENT_GET_CONSENT.value == "consent_get_consent"
        assert Operation.DPI_NG_CONSENT_DELETE_CONSENT.value == "consent_delete_consent"
        assert Operation.DPI_NG_CONSENT_CREATE_CONSENT_FROM_TEMPLATE.value == "consent_create_consent_from_template"
        assert Operation.DPI_NG_CONSENT_WITHDRAW_CONSENT.value == "consent_withdraw_consent"
        assert Operation.DPI_NG_CONSENT_TERMINATE_CONSENT.value == "consent_terminate_consent"
        assert Operation.DPI_NG_CONSENT_CHECK_CONSENT_EXISTS.value == "consent_check_consent_exists"
        assert Operation.DPI_NG_CONSENT_LIST_PURPOSES.value == "consent_list_purposes"
        assert Operation.DPI_NG_CONSENT_GET_PURPOSE.value == "consent_get_purpose"
        assert Operation.DPI_NG_CONSENT_CREATE_PURPOSE.value == "consent_create_purpose"
        assert Operation.DPI_NG_CONSENT_UPDATE_PURPOSE.value == "consent_update_purpose"
        assert Operation.DPI_NG_CONSENT_DELETE_PURPOSE.value == "consent_delete_purpose"
        assert Operation.DPI_NG_CONSENT_SET_PURPOSE_ACTIVE.value == "consent_set_purpose_active"
        assert Operation.DPI_NG_CONSENT_SET_PURPOSE_INACTIVE.value == "consent_set_purpose_inactive"
        assert Operation.DPI_NG_CONSENT_LIST_PURPOSE_TEXTS.value == "consent_list_purpose_texts"
        assert Operation.DPI_NG_CONSENT_GET_PURPOSE_TEXT.value == "consent_get_purpose_text"
        assert Operation.DPI_NG_CONSENT_CREATE_PURPOSE_TEXT.value == "consent_create_purpose_text"
        assert Operation.DPI_NG_CONSENT_UPDATE_PURPOSE_TEXT.value == "consent_update_purpose_text"
        assert Operation.DPI_NG_CONSENT_DELETE_PURPOSE_TEXT.value == "consent_delete_purpose_text"
        assert Operation.DPI_NG_CONSENT_LIST_TEMPLATES.value == "consent_list_templates"
        assert Operation.DPI_NG_CONSENT_GET_TEMPLATE.value == "consent_get_template"
        assert Operation.DPI_NG_CONSENT_CREATE_TEMPLATE.value == "consent_create_template"
        assert Operation.DPI_NG_CONSENT_UPDATE_TEMPLATE.value == "consent_update_template"
        assert Operation.DPI_NG_CONSENT_DELETE_TEMPLATE.value == "consent_delete_template"
        assert Operation.DPI_NG_CONSENT_SET_TEMPLATE_ACTIVE.value == "consent_set_template_active"
        assert Operation.DPI_NG_CONSENT_SET_TEMPLATE_INACTIVE.value == "consent_set_template_inactive"
        assert Operation.DPI_NG_CONSENT_LIST_TEMPLATE_TEXTS.value == "consent_list_template_texts"
        assert Operation.DPI_NG_CONSENT_GET_TEMPLATE_TEXT.value == "consent_get_template_text"
        assert Operation.DPI_NG_CONSENT_CREATE_TEMPLATE_TEXT.value == "consent_create_template_text"
        assert Operation.DPI_NG_CONSENT_UPDATE_TEMPLATE_TEXT.value == "consent_update_template_text"
        assert Operation.DPI_NG_CONSENT_DELETE_TEMPLATE_TEXT.value == "consent_delete_template_text"
        assert Operation.DPI_NG_CONSENT_LIST_THIRD_PARTY_PERS_DATA.value == "consent_list_third_party_pers_data"
        assert Operation.DPI_NG_CONSENT_GET_THIRD_PARTY_PERS_DATA.value == "consent_get_third_party_pers_data"
        assert Operation.DPI_NG_CONSENT_CREATE_THIRD_PARTY_PERS_DATA.value == "consent_create_third_party_pers_data"
        assert Operation.DPI_NG_CONSENT_UPDATE_THIRD_PARTY_PERS_DATA.value == "consent_update_third_party_pers_data"
        assert Operation.DPI_NG_CONSENT_DELETE_THIRD_PARTY_PERS_DATA.value == "consent_delete_third_party_pers_data"
        assert Operation.DPI_NG_CONSENT_LIST_RULES.value == "consent_list_rules"
        assert Operation.DPI_NG_CONSENT_GET_RULE.value == "consent_get_rule"
        assert Operation.DPI_NG_CONSENT_CREATE_RULE.value == "consent_create_rule"
        assert Operation.DPI_NG_CONSENT_UPDATE_RULE.value == "consent_update_rule"
        assert Operation.DPI_NG_CONSENT_DELETE_RULE.value == "consent_delete_rule"
        assert Operation.DPI_NG_CONSENT_SET_RULE_ACTIVE.value == "consent_set_rule_active"
        assert Operation.DPI_NG_CONSENT_SET_RULE_INACTIVE.value == "consent_set_rule_inactive"
        assert Operation.DPI_NG_CONSENT_LIST_THIRD_PARTIES.value == "consent_list_third_parties"
        assert Operation.DPI_NG_CONSENT_GET_THIRD_PARTY.value == "consent_get_third_party"
        assert Operation.DPI_NG_CONSENT_CREATE_THIRD_PARTY.value == "consent_create_third_party"
        assert Operation.DPI_NG_CONSENT_UPDATE_THIRD_PARTY.value == "consent_update_third_party"
        assert Operation.DPI_NG_CONSENT_DELETE_THIRD_PARTY.value == "consent_delete_third_party"
        assert Operation.DPI_NG_CONSENT_LIST_JURISDICTIONS.value == "consent_list_jurisdictions"
        assert Operation.DPI_NG_CONSENT_GET_JURISDICTION.value == "consent_get_jurisdiction"
        assert Operation.DPI_NG_CONSENT_CREATE_JURISDICTION.value == "consent_create_jurisdiction"
        assert Operation.DPI_NG_CONSENT_UPDATE_JURISDICTION.value == "consent_update_jurisdiction"
        assert Operation.DPI_NG_CONSENT_DELETE_JURISDICTION.value == "consent_delete_jurisdiction"
        assert Operation.DPI_NG_CONSENT_LIST_JURISDICTION_TEXTS.value == "consent_list_jurisdiction_texts"
        assert Operation.DPI_NG_CONSENT_CREATE_JURISDICTION_TEXT.value == "consent_create_jurisdiction_text"
        assert Operation.DPI_NG_CONSENT_UPDATE_JURISDICTION_TEXT.value == "consent_update_jurisdiction_text"
        assert Operation.DPI_NG_CONSENT_DELETE_JURISDICTION_TEXT.value == "consent_delete_jurisdiction_text"
        assert Operation.DPI_NG_CONSENT_LIST_LANGUAGES.value == "consent_list_languages"
        assert Operation.DPI_NG_CONSENT_GET_LANGUAGE.value == "consent_get_language"
        assert Operation.DPI_NG_CONSENT_LIST_LANGUAGE_DESCRIPTIONS.value == "consent_list_language_descriptions"
        assert Operation.DPI_NG_CONSENT_CREATE_LANGUAGE_DESCRIPTION.value == "consent_create_language_description"
        assert Operation.DPI_NG_CONSENT_UPDATE_LANGUAGE_DESCRIPTION.value == "consent_update_language_description"
        assert Operation.DPI_NG_CONSENT_DELETE_LANGUAGE_DESCRIPTION.value == "consent_delete_language_description"
        assert Operation.DPI_NG_CONSENT_LIST_SOURCE_INFOS.value == "consent_list_source_infos"
        assert Operation.DPI_NG_CONSENT_GET_SOURCE_INFO.value == "consent_get_source_info"
        assert Operation.DPI_NG_CONSENT_CREATE_SOURCE_INFO.value == "consent_create_source_info"
        assert Operation.DPI_NG_CONSENT_UPDATE_SOURCE_INFO.value == "consent_update_source_info"
        assert Operation.DPI_NG_CONSENT_DELETE_SOURCE_INFO.value == "consent_delete_source_info"
        assert Operation.DPI_NG_CONSENT_LIST_CONTROLLERS.value == "consent_list_controllers"
        assert Operation.DPI_NG_CONSENT_GET_CONTROLLER.value == "consent_get_controller"
        assert Operation.DPI_NG_CONSENT_CREATE_CONTROLLER.value == "consent_create_controller"
        assert Operation.DPI_NG_CONSENT_UPDATE_CONTROLLER.value == "consent_update_controller"
        assert Operation.DPI_NG_CONSENT_DELETE_CONTROLLER.value == "consent_delete_controller"
        assert Operation.DPI_NG_CONSENT_LIST_DATA_SUBJECT_TYPES.value == "consent_list_data_subject_types"
        assert Operation.DPI_NG_CONSENT_GET_DATA_SUBJECT_TYPE.value == "consent_get_data_subject_type"
        assert Operation.DPI_NG_CONSENT_CREATE_DATA_SUBJECT_TYPE.value == "consent_create_data_subject_type"
        assert Operation.DPI_NG_CONSENT_UPDATE_DATA_SUBJECT_TYPE.value == "consent_update_data_subject_type"
        assert Operation.DPI_NG_CONSENT_DELETE_DATA_SUBJECT_TYPE.value == "consent_delete_data_subject_type"
        assert Operation.DPI_NG_CONSENT_LIST_APPLICATIONS.value == "consent_list_applications"
        assert Operation.DPI_NG_CONSENT_GET_APPLICATION.value == "consent_get_application"
        assert Operation.DPI_NG_CONSENT_CREATE_APPLICATION.value == "consent_create_application"
        assert Operation.DPI_NG_CONSENT_UPDATE_APPLICATION.value == "consent_update_application"
        assert Operation.DPI_NG_CONSENT_DELETE_APPLICATION.value == "consent_delete_application"
        assert Operation.DPI_NG_CONSENT_LIST_MASTER_DATA_SOURCES.value == "consent_list_master_data_sources"
        assert Operation.DPI_NG_CONSENT_GET_MASTER_DATA_SOURCE.value == "consent_get_master_data_source"
        assert Operation.DPI_NG_CONSENT_CREATE_MASTER_DATA_SOURCE.value == "consent_create_master_data_source"
        assert Operation.DPI_NG_CONSENT_UPDATE_MASTER_DATA_SOURCE.value == "consent_update_master_data_source"
        assert Operation.DPI_NG_CONSENT_DELETE_MASTER_DATA_SOURCE.value == "consent_delete_master_data_source"
        assert Operation.DPI_NG_CONSENT_LIST_OUTBOUND_CHANNEL_TYPES.value == "consent_list_outbound_channel_types"
        assert Operation.DPI_NG_CONSENT_GET_OUTBOUND_CHANNEL_TYPE.value == "consent_get_outbound_channel_type"
        assert Operation.DPI_NG_CONSENT_CREATE_OUTBOUND_CHANNEL_TYPE.value == "consent_create_outbound_channel_type"
        assert Operation.DPI_NG_CONSENT_UPDATE_OUTBOUND_CHANNEL_TYPE.value == "consent_update_outbound_channel_type"
        assert Operation.DPI_NG_CONSENT_DELETE_OUTBOUND_CHANNEL_TYPE.value == "consent_delete_outbound_channel_type"

    def test_operation_str_representation(self):
        """Test that Operation enum converts to string correctly."""
        assert str(Operation.AUDITLOG_LOG) == "log"
        assert str(Operation.DATA_ANONYMIZATION_ANONYMIZE_TEXT)  == "anonymize_text"
        assert str(Operation.DESTINATION_GET_INSTANCE_DESTINATION) == "get_instance_destination"
        assert str(Operation.OBJECTSTORE_PUT_OBJECT) == "put_object"
        assert str(Operation.AICORE_AUTO_INSTRUMENT) == "auto_instrument"
        assert str(Operation.DPI_NG_CONSENT_CREATE_CLIENT) == "consent_create_client"
        assert str(Operation.DPI_NG_CONSENT_LIST_CONSENTS) == "consent_list_consents"

    def test_operation_is_string_enum(self):
        """Test that Operation enum inherits from str."""
        assert isinstance(Operation.AUDITLOG_LOG, str)
        assert isinstance(Operation.DATA_ANONYMIZATION_ANONYMIZE_TEXT, str)
        assert isinstance(Operation.DESTINATION_CREATE_DESTINATION, str)
        assert isinstance(Operation.OBJECTSTORE_GET_OBJECT, str)
        assert isinstance(Operation.DPI_NG_CONSENT_CREATE_CLIENT, str)

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
        assert any("DATA_ANONYMIZATION" in op.name for op in all_operations)
        assert any("DESTINATION" in op.name for op in all_operations)
        assert any("CERTIFICATE" in op.name for op in all_operations)
        assert any("EXTENSIBILITY" in op.name for op in all_operations)
        assert any("FRAGMENT" in op.name for op in all_operations)
        assert any("OBJECTSTORE" in op.name for op in all_operations)
        assert any("AICORE" in op.name for op in all_operations)
        assert any("PRINT" in op.name for op in all_operations)
        assert any("DPI_NG" in op.name for op in all_operations)

    def test_operation_count(self):
        """Test that we have the expected number of operations."""
        all_operations = list(Operation)
        # 3 auditlog + 12 destination + 10 certificate + 10 fragment + 8 objectstore
        # + 2 extensibility + 4 aicore + 23 dms + 6 agentgateway + 13 agent_memory
        # + 5 data_anonymization + 52 adms + 6 print + 94 dpi_ng = 248
        assert len(all_operations) == 248
