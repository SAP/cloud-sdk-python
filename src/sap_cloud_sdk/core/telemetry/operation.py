"""Types for telemetry operation definitions."""

from enum import Enum


class Operation(str, Enum):
    """SDK operations identifiers for telemetry."""

    # Audit Log Operations
    AUDITLOG_LOG = "log"
    AUDITLOG_LOG_BATCH = "log_batch"
    AUDITLOG_CREATE_CLIENT = "create_client"

    # Destination Operations
    DESTINATION_GET_INSTANCE_DESTINATION = "get_instance_destination"
    DESTINATION_GET_SUBACCOUNT_DESTINATION = "get_subaccount_destination"
    DESTINATION_LIST_INSTANCE_DESTINATIONS = "list_instance_destinations"
    DESTINATION_LIST_SUBACCOUNT_DESTINATIONS = "list_subaccount_destinations"
    DESTINATION_CREATE_DESTINATION = "create_destination"
    DESTINATION_UPDATE_DESTINATION = "update_destination"
    DESTINATION_DELETE_DESTINATION = "delete_destination"
    DESTINATION_GET_DESTINATION = "get_destination"

    # Destination Label Operations
    DESTINATION_GET_LABELS = "get_destination_labels"
    DESTINATION_UPDATE_LABELS = "update_destination_labels"
    DESTINATION_PATCH_LABELS = "patch_destination_labels"

    # Certificate Operations
    CERTIFICATE_GET_INSTANCE_CERTIFICATE = "get_instance_certificate"
    CERTIFICATE_GET_SUBACCOUNT_CERTIFICATE = "get_subaccount_certificate"
    CERTIFICATE_LIST_INSTANCE_CERTIFICATES = "list_instance_certificates"
    CERTIFICATE_LIST_SUBACCOUNT_CERTIFICATES = "list_subaccount_certificates"
    CERTIFICATE_CREATE_CERTIFICATE = "create_certificate"
    CERTIFICATE_UPDATE_CERTIFICATE = "update_certificate"
    CERTIFICATE_DELETE_CERTIFICATE = "delete_certificate"

    # Certificate Label Operations
    CERTIFICATE_GET_LABELS = "get_certificate_labels"
    CERTIFICATE_UPDATE_LABELS = "update_certificate_labels"
    CERTIFICATE_PATCH_LABELS = "patch_certificate_labels"

    # Fragment Operations
    FRAGMENT_GET_INSTANCE_FRAGMENT = "get_instance_fragment"
    FRAGMENT_GET_SUBACCOUNT_FRAGMENT = "get_subaccount_fragment"
    FRAGMENT_LIST_INSTANCE_FRAGMENTS = "list_instance_fragments"
    FRAGMENT_LIST_SUBACCOUNT_FRAGMENTS = "list_subaccount_fragments"
    FRAGMENT_CREATE_FRAGMENT = "create_fragment"
    FRAGMENT_UPDATE_FRAGMENT = "update_fragment"
    FRAGMENT_DELETE_FRAGMENT = "delete_fragment"

    # Fragment Label Operations
    FRAGMENT_GET_LABELS = "get_fragment_labels"
    FRAGMENT_UPDATE_LABELS = "update_fragment_labels"
    FRAGMENT_PATCH_LABELS = "patch_fragment_labels"

    # Object Store Operations
    OBJECTSTORE_PUT_OBJECT = "put_object"
    OBJECTSTORE_PUT_OBJECT_FROM_FILE = "put_object_from_file"
    OBJECTSTORE_PUT_OBJECT_FROM_BYTES = "put_object_from_bytes"
    OBJECTSTORE_GET_OBJECT = "get_object"
    OBJECTSTORE_HEAD_OBJECT = "head_object"
    OBJECTSTORE_DELETE_OBJECT = "delete_object"
    OBJECTSTORE_LIST_OBJECTS = "list_objects"
    OBJECTSTORE_OBJECT_EXISTS = "object_exists"

    # AI Core Operations
    AICORE_SET_CONFIG = "set_aicore_config"
    AICORE_AUTO_INSTRUMENT = "auto_instrument"

    # DMS Operations
    DMS_ONBOARD_REPOSITORY = "onboard_repository"
    DMS_GET_REPOSITORY = "get_repository"
    DMS_GET_ALL_REPOSITORIES = "get_all_repositories"
    DMS_UPDATE_REPOSITORY = "update_repository"
    DMS_DELETE_REPOSITORY = "delete_repository"
    DMS_CREATE_CONFIG = "create_config"
    DMS_GET_CONFIGS = "get_configs"
    DMS_UPDATE_CONFIG = "update_config"
    DMS_DELETE_CONFIG = "delete_config"

    # DMS CMIS Operations
    # Prefixed with "cmis_" to distinguish from other modules (e.g.
    # ObjectStore also has "get_object" / "delete_object") and to avoid
    # Python enum aliasing on duplicate values.
    DMS_CREATE_FOLDER = "cmis_create_folder"
    DMS_CREATE_DOCUMENT = "cmis_create_document"
    DMS_CHECK_OUT = "cmis_check_out"
    DMS_CHECK_IN = "cmis_check_in"
    DMS_CANCEL_CHECK_OUT = "cmis_cancel_check_out"
    DMS_APPLY_ACL = "cmis_apply_acl"
    DMS_GET_OBJECT = "cmis_get_object"
    DMS_GET_CONTENT = "cmis_get_content"
    DMS_UPDATE_PROPERTIES = "cmis_update_properties"
    DMS_GET_CHILDREN = "cmis_get_children"
    DMS_DELETE_OBJECT = "cmis_delete_object"
    DMS_RESTORE_OBJECT = "cmis_restore_object"
    DMS_APPEND_CONTENT_STREAM = "cmis_append_content_stream"
    DMS_CMIS_QUERY = "cmis_query"

    # Agent Gateway Operations
    AGENTGATEWAY_LIST_MCP_TOOLS = "list_mcp_tools"
    AGENTGATEWAY_CALL_MCP_TOOL = "call_mcp_tool"

    # Agent Memory Operations
    AGENT_MEMORY_ADD_MEMORY = "add_memory"
    AGENT_MEMORY_GET_MEMORY = "get_memory"
    AGENT_MEMORY_UPDATE_MEMORY = "update_memory"
    AGENT_MEMORY_DELETE_MEMORY = "delete_memory"
    AGENT_MEMORY_LIST_MEMORIES = "list_memories"
    AGENT_MEMORY_COUNT_MEMORIES = "count_memories"
    AGENT_MEMORY_SEARCH_MEMORIES = "search_memories"
    AGENT_MEMORY_ADD_MESSAGE = "add_message"
    AGENT_MEMORY_GET_MESSAGE = "get_message"
    AGENT_MEMORY_DELETE_MESSAGE = "delete_message"
    AGENT_MEMORY_LIST_MESSAGES = "list_messages"
    AGENT_MEMORY_GET_RETENTION_CONFIG = "get_retention_config"
    AGENT_MEMORY_UPDATE_RETENTION_CONFIG = "update_retention_config"

    def __str__(self) -> str:
        return self.value
