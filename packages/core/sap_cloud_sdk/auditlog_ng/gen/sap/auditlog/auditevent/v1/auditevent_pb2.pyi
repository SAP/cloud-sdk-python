import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from packages.core.sap_cloud_sdk.auditlog_ng.gen.protoc.gen.jsonschema.v1 import options_pb2 as _options_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CredentialType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CREDENTIAL_TYPE_UNSPECIFIED: _ClassVar[CredentialType]
    CREDENTIAL_TYPE_X509_CERTIFICATE: _ClassVar[CredentialType]
    CREDENTIAL_TYPE_KEY: _ClassVar[CredentialType]
    CREDENTIAL_TYPE_SECRET: _ClassVar[CredentialType]

class FailureReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FAILURE_REASON_UNSPECIFIED: _ClassVar[FailureReason]
    FAILURE_REASON_PASSWORD: _ClassVar[FailureReason]
    FAILURE_REASON_MFA_FAILED: _ClassVar[FailureReason]
    FAILURE_REASON_USER_NOT_FOUND: _ClassVar[FailureReason]
    FAILURE_REASON_USER_LOCKED: _ClassVar[FailureReason]
    FAILURE_REASON_USER_BLOCKED: _ClassVar[FailureReason]
    FAILURE_REASON_USER_UNVERIFIED: _ClassVar[FailureReason]
    FAILURE_REASON_USER_EXPIRED: _ClassVar[FailureReason]
    FAILURE_REASON_USER_INVALID: _ClassVar[FailureReason]
    FAILURE_REASON_INSECURE_CONNECTION: _ClassVar[FailureReason]
    FAILURE_REASON_LOGIN_METHOD_DISABLED: _ClassVar[FailureReason]
    FAILURE_REASON_TOKEN_EXPIRED: _ClassVar[FailureReason]
    FAILURE_REASON_TOKEN_REVOKED: _ClassVar[FailureReason]
    FAILURE_REASON_TOKEN_INVALID: _ClassVar[FailureReason]
    FAILURE_REASON_SESSION_EXPIRED: _ClassVar[FailureReason]
    FAILURE_REASON_SESSION_REVOKED: _ClassVar[FailureReason]
    FAILURE_REASON_CERTIFICATE_EXPIRED: _ClassVar[FailureReason]
    FAILURE_REASON_CERTIFICATE_REVOKED: _ClassVar[FailureReason]
    FAILURE_REASON_CERTIFICATE_INVALID: _ClassVar[FailureReason]

class LoginMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOGIN_METHOD_UNSPECIFIED: _ClassVar[LoginMethod]
    LOGIN_METHOD_OPEN_ID_CONNECT: _ClassVar[LoginMethod]
    LOGIN_METHOD_SAML: _ClassVar[LoginMethod]
    LOGIN_METHOD_SAML2: _ClassVar[LoginMethod]
    LOGIN_METHOD_EXTERNAL: _ClassVar[LoginMethod]
    LOGIN_METHOD_SPNEGO: _ClassVar[LoginMethod]
    LOGIN_METHOD_PASSWORD: _ClassVar[LoginMethod]
    LOGIN_METHOD_RFC_TICKET: _ClassVar[LoginMethod]
    LOGIN_METHOD_SNC: _ClassVar[LoginMethod]
    LOGIN_METHOD_LOGON_TICKET: _ClassVar[LoginMethod]
    LOGIN_METHOD_USER_SWITCH: _ClassVar[LoginMethod]
    LOGIN_METHOD_X509_CERTIFICATE: _ClassVar[LoginMethod]
    LOGIN_METHOD_APC_SESSION: _ClassVar[LoginMethod]
    LOGIN_METHOD_INTERNAL: _ClassVar[LoginMethod]
    LOGIN_METHOD_OAUTH2: _ClassVar[LoginMethod]
    LOGIN_METHOD_REENTRANCE_TICKET: _ClassVar[LoginMethod]
    LOGIN_METHOD_HTTP_SESSION: _ClassVar[LoginMethod]
    LOGIN_METHOD_ASSERTION_TICKET: _ClassVar[LoginMethod]

class LogoffType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOGOFF_TYPE_UNSPECIFIED: _ClassVar[LogoffType]
    LOGOFF_TYPE_REGULAR: _ClassVar[LogoffType]
    LOGOFF_TYPE_FORCED: _ClassVar[LogoffType]

class MaliciousBehavior(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MALICIOUS_BEHAVIOR_UNSPECIFIED: _ClassVar[MaliciousBehavior]
    MALICIOUS_BEHAVIOR_PARAMETER_SEEN: _ClassVar[MaliciousBehavior]
    MALICIOUS_BEHAVIOR_PARAMETER_NOT_FOUND: _ClassVar[MaliciousBehavior]
    MALICIOUS_BEHAVIOR_PARAMETER_VALUE_SEEN: _ClassVar[MaliciousBehavior]
    MALICIOUS_BEHAVIOR_PARAMETER_VALUE_MODIFIED: _ClassVar[MaliciousBehavior]

class MfaType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MFA_TYPE_UNSPECIFIED: _ClassVar[MfaType]
    MFA_TYPE_NONE: _ClassVar[MfaType]
    MFA_TYPE_RSA: _ClassVar[MfaType]
    MFA_TYPE_TOTP: _ClassVar[MfaType]
    MFA_TYPE_WEB_AUTHN: _ClassVar[MfaType]

class UserType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    USER_TYPE_UNSPECIFIED: _ClassVar[UserType]
    USER_TYPE_BUSINESS_USER: _ClassVar[UserType]
    USER_TYPE_TECHNICAL_USER: _ClassVar[UserType]

class DataExportChannelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATA_EXPORT_CHANNEL_TYPE_UNSPECIFIED: _ClassVar[DataExportChannelType]
    DATA_EXPORT_CHANNEL_TYPE_DOWNLOAD: _ClassVar[DataExportChannelType]
    DATA_EXPORT_CHANNEL_TYPE_API_ACCESS: _ClassVar[DataExportChannelType]
    DATA_EXPORT_CHANNEL_TYPE_PRINTER: _ClassVar[DataExportChannelType]

class EventCategoryCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EVENT_CATEGORY_CODE_SEC_UNSPECIFIED: _ClassVar[EventCategoryCode]
    EVENT_CATEGORY_CODE_IAM: _ClassVar[EventCategoryCode]
    EVENT_CATEGORY_CODE_CFG: _ClassVar[EventCategoryCode]
    EVENT_CATEGORY_CODE_DPP: _ClassVar[EventCategoryCode]
    EVENT_CATEGORY_CODE_RAL: _ClassVar[EventCategoryCode]

class CMKAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CMK_ACTION_UNSPECIFIED: _ClassVar[CMKAction]
    CMK_ACTION_ONBOARD: _ClassVar[CMKAction]
    CMK_ACTION_BLOCK: _ClassVar[CMKAction]
    CMK_ACTION_SHUTDOWN: _ClassVar[CMKAction]
    CMK_ACTION_CSEKFALLBACK: _ClassVar[CMKAction]
    CMK_ACTION_RESTORE: _ClassVar[CMKAction]
    CMK_ACTION_KMS_ONBOARD: _ClassVar[CMKAction]
    CMK_ACTION_KMS_OFFBOARD: _ClassVar[CMKAction]

class KeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    KEY_TYPE_UNSPECIFIED: _ClassVar[KeyType]
    KEY_TYPE_SYSTEM: _ClassVar[KeyType]
    KEY_TYPE_SERVICE: _ClassVar[KeyType]
    KEY_TYPE_DATA: _ClassVar[KeyType]
    KEY_TYPE_KEK: _ClassVar[KeyType]
CREDENTIAL_TYPE_UNSPECIFIED: CredentialType
CREDENTIAL_TYPE_X509_CERTIFICATE: CredentialType
CREDENTIAL_TYPE_KEY: CredentialType
CREDENTIAL_TYPE_SECRET: CredentialType
FAILURE_REASON_UNSPECIFIED: FailureReason
FAILURE_REASON_PASSWORD: FailureReason
FAILURE_REASON_MFA_FAILED: FailureReason
FAILURE_REASON_USER_NOT_FOUND: FailureReason
FAILURE_REASON_USER_LOCKED: FailureReason
FAILURE_REASON_USER_BLOCKED: FailureReason
FAILURE_REASON_USER_UNVERIFIED: FailureReason
FAILURE_REASON_USER_EXPIRED: FailureReason
FAILURE_REASON_USER_INVALID: FailureReason
FAILURE_REASON_INSECURE_CONNECTION: FailureReason
FAILURE_REASON_LOGIN_METHOD_DISABLED: FailureReason
FAILURE_REASON_TOKEN_EXPIRED: FailureReason
FAILURE_REASON_TOKEN_REVOKED: FailureReason
FAILURE_REASON_TOKEN_INVALID: FailureReason
FAILURE_REASON_SESSION_EXPIRED: FailureReason
FAILURE_REASON_SESSION_REVOKED: FailureReason
FAILURE_REASON_CERTIFICATE_EXPIRED: FailureReason
FAILURE_REASON_CERTIFICATE_REVOKED: FailureReason
FAILURE_REASON_CERTIFICATE_INVALID: FailureReason
LOGIN_METHOD_UNSPECIFIED: LoginMethod
LOGIN_METHOD_OPEN_ID_CONNECT: LoginMethod
LOGIN_METHOD_SAML: LoginMethod
LOGIN_METHOD_SAML2: LoginMethod
LOGIN_METHOD_EXTERNAL: LoginMethod
LOGIN_METHOD_SPNEGO: LoginMethod
LOGIN_METHOD_PASSWORD: LoginMethod
LOGIN_METHOD_RFC_TICKET: LoginMethod
LOGIN_METHOD_SNC: LoginMethod
LOGIN_METHOD_LOGON_TICKET: LoginMethod
LOGIN_METHOD_USER_SWITCH: LoginMethod
LOGIN_METHOD_X509_CERTIFICATE: LoginMethod
LOGIN_METHOD_APC_SESSION: LoginMethod
LOGIN_METHOD_INTERNAL: LoginMethod
LOGIN_METHOD_OAUTH2: LoginMethod
LOGIN_METHOD_REENTRANCE_TICKET: LoginMethod
LOGIN_METHOD_HTTP_SESSION: LoginMethod
LOGIN_METHOD_ASSERTION_TICKET: LoginMethod
LOGOFF_TYPE_UNSPECIFIED: LogoffType
LOGOFF_TYPE_REGULAR: LogoffType
LOGOFF_TYPE_FORCED: LogoffType
MALICIOUS_BEHAVIOR_UNSPECIFIED: MaliciousBehavior
MALICIOUS_BEHAVIOR_PARAMETER_SEEN: MaliciousBehavior
MALICIOUS_BEHAVIOR_PARAMETER_NOT_FOUND: MaliciousBehavior
MALICIOUS_BEHAVIOR_PARAMETER_VALUE_SEEN: MaliciousBehavior
MALICIOUS_BEHAVIOR_PARAMETER_VALUE_MODIFIED: MaliciousBehavior
MFA_TYPE_UNSPECIFIED: MfaType
MFA_TYPE_NONE: MfaType
MFA_TYPE_RSA: MfaType
MFA_TYPE_TOTP: MfaType
MFA_TYPE_WEB_AUTHN: MfaType
USER_TYPE_UNSPECIFIED: UserType
USER_TYPE_BUSINESS_USER: UserType
USER_TYPE_TECHNICAL_USER: UserType
DATA_EXPORT_CHANNEL_TYPE_UNSPECIFIED: DataExportChannelType
DATA_EXPORT_CHANNEL_TYPE_DOWNLOAD: DataExportChannelType
DATA_EXPORT_CHANNEL_TYPE_API_ACCESS: DataExportChannelType
DATA_EXPORT_CHANNEL_TYPE_PRINTER: DataExportChannelType
EVENT_CATEGORY_CODE_SEC_UNSPECIFIED: EventCategoryCode
EVENT_CATEGORY_CODE_IAM: EventCategoryCode
EVENT_CATEGORY_CODE_CFG: EventCategoryCode
EVENT_CATEGORY_CODE_DPP: EventCategoryCode
EVENT_CATEGORY_CODE_RAL: EventCategoryCode
CMK_ACTION_UNSPECIFIED: CMKAction
CMK_ACTION_ONBOARD: CMKAction
CMK_ACTION_BLOCK: CMKAction
CMK_ACTION_SHUTDOWN: CMKAction
CMK_ACTION_CSEKFALLBACK: CMKAction
CMK_ACTION_RESTORE: CMKAction
CMK_ACTION_KMS_ONBOARD: CMKAction
CMK_ACTION_KMS_OFFBOARD: CMKAction
KEY_TYPE_UNSPECIFIED: KeyType
KEY_TYPE_SYSTEM: KeyType
KEY_TYPE_SERVICE: KeyType
KEY_TYPE_DATA: KeyType
KEY_TYPE_KEK: KeyType

class Metadata(_message.Message):
    __slots__ = ("ts", "source_ip", "user_impersonated_id", "user_initiator_id", "app_id", "tenant_id", "user_session_context_id", "app_context", "infrastructure", "platform")
    class AppContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class Infrastructure(_message.Message):
        __slots__ = ("k8s", "cf", "other", "app")
        class Kubernetes(_message.Message):
            __slots__ = ("infrastructure_region", "cluster", "node", "pod")
            INFRASTRUCTURE_REGION_FIELD_NUMBER: _ClassVar[int]
            CLUSTER_FIELD_NUMBER: _ClassVar[int]
            NODE_FIELD_NUMBER: _ClassVar[int]
            POD_FIELD_NUMBER: _ClassVar[int]
            infrastructure_region: str
            cluster: str
            node: str
            pod: str
            def __init__(self, infrastructure_region: _Optional[str] = ..., cluster: _Optional[str] = ..., node: _Optional[str] = ..., pod: _Optional[str] = ...) -> None: ...
        class CloudFoundry(_message.Message):
            __slots__ = ("btpregion", "org_id", "space_id", "app_id")
            BTPREGION_FIELD_NUMBER: _ClassVar[int]
            ORG_ID_FIELD_NUMBER: _ClassVar[int]
            SPACE_ID_FIELD_NUMBER: _ClassVar[int]
            APP_ID_FIELD_NUMBER: _ClassVar[int]
            btpregion: str
            org_id: str
            space_id: str
            app_id: str
            def __init__(self, btpregion: _Optional[str] = ..., org_id: _Optional[str] = ..., space_id: _Optional[str] = ..., app_id: _Optional[str] = ...) -> None: ...
        class Other(_message.Message):
            __slots__ = ("runtime_type",)
            RUNTIME_TYPE_FIELD_NUMBER: _ClassVar[int]
            runtime_type: str
            def __init__(self, runtime_type: _Optional[str] = ...) -> None: ...
        class App(_message.Message):
            __slots__ = ("image", "version")
            IMAGE_FIELD_NUMBER: _ClassVar[int]
            VERSION_FIELD_NUMBER: _ClassVar[int]
            image: str
            version: str
            def __init__(self, image: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...
        K8S_FIELD_NUMBER: _ClassVar[int]
        CF_FIELD_NUMBER: _ClassVar[int]
        OTHER_FIELD_NUMBER: _ClassVar[int]
        APP_FIELD_NUMBER: _ClassVar[int]
        k8s: Metadata.Infrastructure.Kubernetes
        cf: Metadata.Infrastructure.CloudFoundry
        other: Metadata.Infrastructure.Other
        app: Metadata.Infrastructure.App
        def __init__(self, k8s: _Optional[_Union[Metadata.Infrastructure.Kubernetes, _Mapping]] = ..., cf: _Optional[_Union[Metadata.Infrastructure.CloudFoundry, _Mapping]] = ..., other: _Optional[_Union[Metadata.Infrastructure.Other, _Mapping]] = ..., app: _Optional[_Union[Metadata.Infrastructure.App, _Mapping]] = ...) -> None: ...
    class Platform(_message.Message):
        __slots__ = ("btp", "unified_services", "other")
        class BTP(_message.Message):
            __slots__ = ("global_account_id", "sub_account_id")
            GLOBAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
            SUB_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
            global_account_id: str
            sub_account_id: str
            def __init__(self, global_account_id: _Optional[str] = ..., sub_account_id: _Optional[str] = ...) -> None: ...
        class UnifiedServices(_message.Message):
            __slots__ = ("account_id", "folder_path", "resourcegroup_path")
            ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
            FOLDER_PATH_FIELD_NUMBER: _ClassVar[int]
            RESOURCEGROUP_PATH_FIELD_NUMBER: _ClassVar[int]
            account_id: str
            folder_path: str
            resourcegroup_path: str
            def __init__(self, account_id: _Optional[str] = ..., folder_path: _Optional[str] = ..., resourcegroup_path: _Optional[str] = ...) -> None: ...
        class Other(_message.Message):
            __slots__ = ("platform_name",)
            PLATFORM_NAME_FIELD_NUMBER: _ClassVar[int]
            platform_name: str
            def __init__(self, platform_name: _Optional[str] = ...) -> None: ...
        BTP_FIELD_NUMBER: _ClassVar[int]
        UNIFIED_SERVICES_FIELD_NUMBER: _ClassVar[int]
        OTHER_FIELD_NUMBER: _ClassVar[int]
        btp: Metadata.Platform.BTP
        unified_services: Metadata.Platform.UnifiedServices
        other: Metadata.Platform.Other
        def __init__(self, btp: _Optional[_Union[Metadata.Platform.BTP, _Mapping]] = ..., unified_services: _Optional[_Union[Metadata.Platform.UnifiedServices, _Mapping]] = ..., other: _Optional[_Union[Metadata.Platform.Other, _Mapping]] = ...) -> None: ...
    TS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_IP_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    APP_ID_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_SESSION_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    APP_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    INFRASTRUCTURE_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    ts: str
    source_ip: _containers.RepeatedScalarFieldContainer[str]
    user_impersonated_id: str
    user_initiator_id: str
    app_id: str
    tenant_id: str
    user_session_context_id: str
    app_context: _containers.ScalarMap[str, str]
    infrastructure: Metadata.Infrastructure
    platform: Metadata.Platform
    def __init__(self, ts: _Optional[str] = ..., source_ip: _Optional[_Iterable[str]] = ..., user_impersonated_id: _Optional[str] = ..., user_initiator_id: _Optional[str] = ..., app_id: _Optional[str] = ..., tenant_id: _Optional[str] = ..., user_session_context_id: _Optional[str] = ..., app_context: _Optional[_Mapping[str, str]] = ..., infrastructure: _Optional[_Union[Metadata.Infrastructure, _Mapping]] = ..., platform: _Optional[_Union[Metadata.Platform, _Mapping]] = ...) -> None: ...

class AuditlogClear(_message.Message):
    __slots__ = ("number_of_events",)
    NUMBER_OF_EVENTS_FIELD_NUMBER: _ClassVar[int]
    number_of_events: int
    def __init__(self, number_of_events: _Optional[int] = ...) -> None: ...

class AuditlogDisable(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AuditlogEnable(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AuthnPrivilegeToGroupAdd(_message.Message):
    __slots__ = ("group", "privilege", "object_type", "object_id")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    group: str
    privilege: str
    object_type: str
    object_id: str
    def __init__(self, group: _Optional[str] = ..., privilege: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToGroupDelete(_message.Message):
    __slots__ = ("group", "privilege", "object_type", "object_id")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    group: str
    privilege: str
    object_type: str
    object_id: str
    def __init__(self, group: _Optional[str] = ..., privilege: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToRoleAdd(_message.Message):
    __slots__ = ("privilege", "role", "object_type", "object_id")
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    privilege: str
    role: str
    object_type: str
    object_id: str
    def __init__(self, privilege: _Optional[str] = ..., role: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToRoleDelete(_message.Message):
    __slots__ = ("privilege", "role", "object_type", "object_id")
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    privilege: str
    role: str
    object_type: str
    object_id: str
    def __init__(self, privilege: _Optional[str] = ..., role: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToUserAdd(_message.Message):
    __slots__ = ("privilege", "user", "object_type", "object_id")
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    privilege: str
    user: str
    object_type: str
    object_id: str
    def __init__(self, privilege: _Optional[str] = ..., user: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToUserDelete(_message.Message):
    __slots__ = ("privilege", "user", "object_type", "object_id")
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    privilege: str
    user: str
    object_type: str
    object_id: str
    def __init__(self, privilege: _Optional[str] = ..., user: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnRoleToGroupAdd(_message.Message):
    __slots__ = ("group", "role")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    group: str
    role: str
    def __init__(self, group: _Optional[str] = ..., role: _Optional[str] = ...) -> None: ...

class AuthnRoleToGroupDelete(_message.Message):
    __slots__ = ("group", "role")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    group: str
    role: str
    def __init__(self, group: _Optional[str] = ..., role: _Optional[str] = ...) -> None: ...

class AuthnRoleToUserAdd(_message.Message):
    __slots__ = ("role", "user")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    role: str
    user: str
    def __init__(self, role: _Optional[str] = ..., user: _Optional[str] = ...) -> None: ...

class AuthnRoleToUserDelete(_message.Message):
    __slots__ = ("role", "user")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    role: str
    user: str
    def __init__(self, role: _Optional[str] = ..., user: _Optional[str] = ...) -> None: ...

class AuthnUserToGroupAdd(_message.Message):
    __slots__ = ("group", "user")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    group: str
    user: str
    def __init__(self, group: _Optional[str] = ..., user: _Optional[str] = ...) -> None: ...

class AuthnUserToGroupDelete(_message.Message):
    __slots__ = ("group", "user")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    group: str
    user: str
    def __init__(self, group: _Optional[str] = ..., user: _Optional[str] = ...) -> None: ...

class ConfigurationAdd(_message.Message):
    __slots__ = ("value", "property_name", "object_type", "object_id")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    value: _struct_pb2.Value
    property_name: str
    object_type: str
    object_id: str
    def __init__(self, value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class ConfigurationChange(_message.Message):
    __slots__ = ("new_value", "old_value", "property_name", "object_type", "object_id")
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    object_type: str
    object_id: str
    def __init__(self, new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class ConfigurationDelete(_message.Message):
    __slots__ = ("value", "property_name", "object_type", "object_id")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    value: _struct_pb2.Value
    property_name: str
    object_type: str
    object_id: str
    def __init__(self, value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class CredentialCreate(_message.Message):
    __slots__ = ("credential_id", "credential_type")
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    credential_id: str
    credential_type: CredentialType
    def __init__(self, credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ...) -> None: ...

class CredentialDelete(_message.Message):
    __slots__ = ("credential_id", "credential_type")
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    credential_id: str
    credential_type: CredentialType
    def __init__(self, credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ...) -> None: ...

class CredentialExpiration(_message.Message):
    __slots__ = ("credential_id", "credential_type", "expiration_date")
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    EXPIRATION_DATE_FIELD_NUMBER: _ClassVar[int]
    credential_id: str
    credential_type: CredentialType
    expiration_date: _timestamp_pb2.Timestamp
    def __init__(self, credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ..., expiration_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CredentialRevokation(_message.Message):
    __slots__ = ("credential_id", "credential_type", "revokation_date")
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    REVOKATION_DATE_FIELD_NUMBER: _ClassVar[int]
    credential_id: str
    credential_type: CredentialType
    revokation_date: _timestamp_pb2.Timestamp
    def __init__(self, credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ..., revokation_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class DataModelChange(_message.Message):
    __slots__ = ("model_id", "new_value", "old_value", "property_name")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    def __init__(self, model_id: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ...) -> None: ...

class DataModelCreate(_message.Message):
    __slots__ = ("model_id",)
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    def __init__(self, model_id: _Optional[str] = ...) -> None: ...

class DataModelDelete(_message.Message):
    __slots__ = ("model_id",)
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    def __init__(self, model_id: _Optional[str] = ...) -> None: ...

class DataAccess(_message.Message):
    __slots__ = ("channel_type", "channel_id", "object_type", "object_id", "attribute", "value", "attachment_type", "attachment_id")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ATTACHMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTACHMENT_ID_FIELD_NUMBER: _ClassVar[int]
    channel_type: str
    channel_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    attachment_type: str
    attachment_id: str
    def __init__(self, channel_type: _Optional[str] = ..., channel_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., attachment_type: _Optional[str] = ..., attachment_id: _Optional[str] = ...) -> None: ...

class DataCreate(_message.Message):
    __slots__ = ("object_type", "object_id", "attribute", "value")
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DataDelete(_message.Message):
    __slots__ = ("object_type", "object_id", "attribute", "value")
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DataModification(_message.Message):
    __slots__ = ("object_type", "object_id", "attribute", "new_value", "old_value")
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    object_type: str
    object_id: str
    attribute: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    def __init__(self, object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DataExport(_message.Message):
    __slots__ = ("channel_type", "channel_id", "object_type", "object_id", "destination_uri")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_URI_FIELD_NUMBER: _ClassVar[int]
    channel_type: DataExportChannelType
    channel_id: str
    object_type: str
    object_id: str
    destination_uri: str
    def __init__(self, channel_type: _Optional[_Union[DataExportChannelType, str]] = ..., channel_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., destination_uri: _Optional[str] = ...) -> None: ...

class DppDataAccess(_message.Message):
    __slots__ = ("channel_type", "channel_id", "data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "value", "attachment_type", "attachment_id")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ATTACHMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTACHMENT_ID_FIELD_NUMBER: _ClassVar[int]
    channel_type: str
    channel_id: str
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    attachment_type: str
    attachment_id: str
    def __init__(self, channel_type: _Optional[str] = ..., channel_id: _Optional[str] = ..., data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., attachment_type: _Optional[str] = ..., attachment_id: _Optional[str] = ...) -> None: ...

class DppDataCreate(_message.Message):
    __slots__ = ("data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "value")
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DppDataDelete(_message.Message):
    __slots__ = ("data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "value")
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DppDataModification(_message.Message):
    __slots__ = ("data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "new_value", "old_value")
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    def __init__(self, data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class JobChange(_message.Message):
    __slots__ = ("job_id", "new_value", "old_value", "property_name")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    def __init__(self, job_id: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ...) -> None: ...

class JobCreate(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class JobDelete(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class JobStatusChange(_message.Message):
    __slots__ = ("job_id", "new_value", "old_value", "property_name")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    def __init__(self, job_id: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ...) -> None: ...

class MaliciousRequestDetected(_message.Message):
    __slots__ = ("parameter", "expected_value", "received_value", "behavior")
    PARAMETER_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_VALUE_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_VALUE_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOR_FIELD_NUMBER: _ClassVar[int]
    parameter: str
    expected_value: str
    received_value: str
    behavior: MaliciousBehavior
    def __init__(self, parameter: _Optional[str] = ..., expected_value: _Optional[str] = ..., received_value: _Optional[str] = ..., behavior: _Optional[_Union[MaliciousBehavior, str]] = ...) -> None: ...

class PasswordChange(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class PasswordExpiration(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class PasswordReset(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class TenantModification(_message.Message):
    __slots__ = ("new_value", "old_value", "property_name", "tenant_id")
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    tenant_id: str
    def __init__(self, new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., tenant_id: _Optional[str] = ...) -> None: ...

class TenantOffboarding(_message.Message):
    __slots__ = ("tenant_id",)
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    tenant_id: str
    def __init__(self, tenant_id: _Optional[str] = ...) -> None: ...

class TenantOnboarding(_message.Message):
    __slots__ = ("tenant_id",)
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    tenant_id: str
    def __init__(self, tenant_id: _Optional[str] = ...) -> None: ...

class UnauthenticatedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UnauthorizedRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UserActivate(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserBlock(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserCreate(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserDataModification(_message.Message):
    __slots__ = ("new_value", "old_value", "property_name", "user_id")
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    user_id: str
    def __init__(self, new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class UserDelete(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserImpersonationStart(_message.Message):
    __slots__ = ("user_initiator_id", "user_initiator_type", "user_impersonated_id", "user_impersonated_type", "context")
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    user_initiator_id: str
    user_initiator_type: UserType
    user_impersonated_id: str
    user_impersonated_type: UserType
    context: str
    def __init__(self, user_initiator_id: _Optional[str] = ..., user_initiator_type: _Optional[_Union[UserType, str]] = ..., user_impersonated_id: _Optional[str] = ..., user_impersonated_type: _Optional[_Union[UserType, str]] = ..., context: _Optional[str] = ...) -> None: ...

class UserImpersonationFinish(_message.Message):
    __slots__ = ("user_initiator_id", "user_initiator_type", "user_impersonated_id", "user_impersonated_type", "context")
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    user_initiator_id: str
    user_initiator_type: UserType
    user_impersonated_id: str
    user_impersonated_type: UserType
    context: str
    def __init__(self, user_initiator_id: _Optional[str] = ..., user_initiator_type: _Optional[_Union[UserType, str]] = ..., user_impersonated_id: _Optional[str] = ..., user_impersonated_type: _Optional[_Union[UserType, str]] = ..., context: _Optional[str] = ...) -> None: ...

class UserLock(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserUnlock(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserVerify(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class UserLoginFailure(_message.Message):
    __slots__ = ("failure_reason", "method")
    FAILURE_REASON_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    failure_reason: FailureReason
    method: LoginMethod
    def __init__(self, failure_reason: _Optional[_Union[FailureReason, str]] = ..., method: _Optional[_Union[LoginMethod, str]] = ...) -> None: ...

class UserLoginSuccess(_message.Message):
    __slots__ = ("is_admin", "method", "mfa_type", "user_type")
    IS_ADMIN_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    MFA_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    is_admin: bool
    method: LoginMethod
    mfa_type: MfaType
    user_type: UserType
    def __init__(self, is_admin: _Optional[bool] = ..., method: _Optional[_Union[LoginMethod, str]] = ..., mfa_type: _Optional[_Union[MfaType, str]] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserLogoff(_message.Message):
    __slots__ = ("logoff_type",)
    LOGOFF_TYPE_FIELD_NUMBER: _ClassVar[int]
    logoff_type: LogoffType
    def __init__(self, logoff_type: _Optional[_Union[LogoffType, str]] = ...) -> None: ...

class ZzzCustomEvent(_message.Message):
    __slots__ = ("custom",)
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    custom: _struct_pb2.Value
    def __init__(self, custom: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class CMKOnboarding(_message.Message):
    __slots__ = ("system_id", "cmk_id")
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    system_id: str
    cmk_id: str
    def __init__(self, system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class CMKOffboarding(_message.Message):
    __slots__ = ("system_id", "cmk_id")
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    system_id: str
    cmk_id: str
    def __init__(self, system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class CMKSwitch(_message.Message):
    __slots__ = ("system_id", "cmk_id_old", "cmk_id_new")
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_OLD_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_NEW_FIELD_NUMBER: _ClassVar[int]
    system_id: str
    cmk_id_old: str
    cmk_id_new: str
    def __init__(self, system_id: _Optional[str] = ..., cmk_id_old: _Optional[str] = ..., cmk_id_new: _Optional[str] = ...) -> None: ...

class CMKTenantModification(_message.Message):
    __slots__ = ("system_id", "cmk_id", "cmk_action")
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ACTION_FIELD_NUMBER: _ClassVar[int]
    system_id: str
    cmk_id: str
    cmk_action: CMKAction
    def __init__(self, system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ..., cmk_action: _Optional[_Union[CMKAction, str]] = ...) -> None: ...

class CMKCreate(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKDelete(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKRestore(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKDisable(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKEnable(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKRotate(_message.Message):
    __slots__ = ("cmk_id",)
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    def __init__(self, cmk_id: _Optional[str] = ...) -> None: ...

class KeyCreate(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyDelete(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyRestore(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyPurge(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyRotate(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyEnable(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyDisable(_message.Message):
    __slots__ = ("key_type", "key_id", "system_id", "cmk_id")
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class CMKUnavailable(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKAvailable(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKDetach(_message.Message):
    __slots__ = ("cmk_id", "kms_system_id", "system_id")
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    cmk_id: str
    kms_system_id: str
    system_id: str
    def __init__(self, cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ..., system_id: _Optional[str] = ...) -> None: ...
