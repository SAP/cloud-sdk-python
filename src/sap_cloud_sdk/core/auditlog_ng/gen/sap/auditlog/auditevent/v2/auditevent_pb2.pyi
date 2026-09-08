import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
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
    FAILURE_REASON_GEOBLOCK: _ClassVar[FailureReason]
    FAILURE_REASON_MFA_REQUESTED: _ClassVar[FailureReason]
    FAILURE_REASON_CRED_REQUESTED: _ClassVar[FailureReason]

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
    LOGIN_METHOD_REMCOOKIE: _ClassVar[LoginMethod]
    LOGIN_METHOD_BIOMETRIC: _ClassVar[LoginMethod]
    LOGIN_METHOD_PASSCODE: _ClassVar[LoginMethod]
    LOGIN_METHOD_MOBSSO: _ClassVar[LoginMethod]
    LOGIN_METHOD_EMAIL_TOKEN: _ClassVar[LoginMethod]
    LOGIN_METHOD_BEARER_TOKEN: _ClassVar[LoginMethod]

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
    MFA_TYPE_SMS: _ClassVar[MfaType]
    MFA_TYPE_EMAIL: _ClassVar[MfaType]

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

class VirusChannel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VIRUS_CHANNEL_UNSPECIFIED: _ClassVar[VirusChannel]
    VIRUS_CHANNEL_UPLOAD: _ClassVar[VirusChannel]
    VIRUS_CHANNEL_SCAN: _ClassVar[VirusChannel]

class LoginProtocol(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOGIN_PROTOCOL_UNSPECIFIED: _ClassVar[LoginProtocol]
    LOGIN_PROTOCOL_SAML2: _ClassVar[LoginProtocol]
    LOGIN_PROTOCOL_OIDC: _ClassVar[LoginProtocol]
    LOGIN_PROTOCOL_HTTP: _ClassVar[LoginProtocol]
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
FAILURE_REASON_GEOBLOCK: FailureReason
FAILURE_REASON_MFA_REQUESTED: FailureReason
FAILURE_REASON_CRED_REQUESTED: FailureReason
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
LOGIN_METHOD_REMCOOKIE: LoginMethod
LOGIN_METHOD_BIOMETRIC: LoginMethod
LOGIN_METHOD_PASSCODE: LoginMethod
LOGIN_METHOD_MOBSSO: LoginMethod
LOGIN_METHOD_EMAIL_TOKEN: LoginMethod
LOGIN_METHOD_BEARER_TOKEN: LoginMethod
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
MFA_TYPE_SMS: MfaType
MFA_TYPE_EMAIL: MfaType
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
VIRUS_CHANNEL_UNSPECIFIED: VirusChannel
VIRUS_CHANNEL_UPLOAD: VirusChannel
VIRUS_CHANNEL_SCAN: VirusChannel
LOGIN_PROTOCOL_UNSPECIFIED: LoginProtocol
LOGIN_PROTOCOL_SAML2: LoginProtocol
LOGIN_PROTOCOL_OIDC: LoginProtocol
LOGIN_PROTOCOL_HTTP: LoginProtocol

class Common(_message.Message):
    __slots__ = ("timestamp", "source_ip", "user_impersonated_id", "user_initiator_id", "app_id", "tenant_id", "user_session_context_id", "app_context")
    class AppContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_IP_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    APP_ID_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_SESSION_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    APP_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    source_ip: _containers.RepeatedScalarFieldContainer[str]
    user_impersonated_id: str
    user_initiator_id: str
    app_id: str
    tenant_id: str
    user_session_context_id: str
    app_context: _containers.ScalarMap[str, str]
    def __init__(self, timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source_ip: _Optional[_Iterable[str]] = ..., user_impersonated_id: _Optional[str] = ..., user_initiator_id: _Optional[str] = ..., app_id: _Optional[str] = ..., tenant_id: _Optional[str] = ..., user_session_context_id: _Optional[str] = ..., app_context: _Optional[_Mapping[str, str]] = ...) -> None: ...

class AuditlogClear(_message.Message):
    __slots__ = ("common", "number_of_events")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    NUMBER_OF_EVENTS_FIELD_NUMBER: _ClassVar[int]
    common: Common
    number_of_events: int
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., number_of_events: _Optional[int] = ...) -> None: ...

class AuditlogDisable(_message.Message):
    __slots__ = ("common",)
    COMMON_FIELD_NUMBER: _ClassVar[int]
    common: Common
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ...) -> None: ...

class AuditlogEnable(_message.Message):
    __slots__ = ("common",)
    COMMON_FIELD_NUMBER: _ClassVar[int]
    common: Common
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ...) -> None: ...

class AuthnPrivilegeToGroupAdd(_message.Message):
    __slots__ = ("common", "group", "privilege", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    group: str
    privilege: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., group: _Optional[str] = ..., privilege: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToGroupDelete(_message.Message):
    __slots__ = ("common", "group", "privilege", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    group: str
    privilege: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., group: _Optional[str] = ..., privilege: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToRoleAdd(_message.Message):
    __slots__ = ("common", "privilege", "role", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    privilege: str
    role: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., privilege: _Optional[str] = ..., role: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToRoleDelete(_message.Message):
    __slots__ = ("common", "privilege", "role", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    privilege: str
    role: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., privilege: _Optional[str] = ..., role: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class AuthnPrivilegeToUserAdd(_message.Message):
    __slots__ = ("common", "privilege", "user", "object_type", "object_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    privilege: str
    user: str
    object_type: str
    object_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., privilege: _Optional[str] = ..., user: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class AuthnPrivilegeToUserDelete(_message.Message):
    __slots__ = ("common", "privilege", "user", "object_type", "object_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    privilege: str
    user: str
    object_type: str
    object_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., privilege: _Optional[str] = ..., user: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class AuthnRoleToGroupAdd(_message.Message):
    __slots__ = ("common", "group", "role")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    group: str
    role: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., group: _Optional[str] = ..., role: _Optional[str] = ...) -> None: ...

class AuthnRoleToGroupDelete(_message.Message):
    __slots__ = ("common", "group", "role")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    group: str
    role: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., group: _Optional[str] = ..., role: _Optional[str] = ...) -> None: ...

class AuthnRoleToUserAdd(_message.Message):
    __slots__ = ("common", "role", "user", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    role: str
    user: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., role: _Optional[str] = ..., user: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class AuthnRoleToUserDelete(_message.Message):
    __slots__ = ("common", "role", "user", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    role: str
    user: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., role: _Optional[str] = ..., user: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class AuthnUserToGroupAdd(_message.Message):
    __slots__ = ("common", "group", "user", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    group: str
    user: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., group: _Optional[str] = ..., user: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class AuthnUserToGroupDelete(_message.Message):
    __slots__ = ("common", "group", "user", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    group: str
    user: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., group: _Optional[str] = ..., user: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class ConfigurationAdd(_message.Message):
    __slots__ = ("common", "value", "property_name", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    value: _struct_pb2.Value
    property_name: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class ConfigurationChange(_message.Message):
    __slots__ = ("common", "new_value", "old_value", "property_name", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class ConfigurationDelete(_message.Message):
    __slots__ = ("common", "value", "property_name", "object_type", "object_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    value: _struct_pb2.Value
    property_name: str
    object_type: str
    object_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ...) -> None: ...

class CredentialCreate(_message.Message):
    __slots__ = ("common", "credential_id", "credential_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    credential_id: str
    credential_type: CredentialType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ...) -> None: ...

class CredentialDelete(_message.Message):
    __slots__ = ("common", "credential_id", "credential_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    credential_id: str
    credential_type: CredentialType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ...) -> None: ...

class CredentialExpiration(_message.Message):
    __slots__ = ("common", "credential_id", "credential_type", "expiration_date")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    EXPIRATION_DATE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    credential_id: str
    credential_type: CredentialType
    expiration_date: _timestamp_pb2.Timestamp
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ..., expiration_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CredentialRevokation(_message.Message):
    __slots__ = ("common", "credential_id", "credential_type", "revokation_date")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    REVOKATION_DATE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    credential_id: str
    credential_type: CredentialType
    revokation_date: _timestamp_pb2.Timestamp
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., credential_id: _Optional[str] = ..., credential_type: _Optional[_Union[CredentialType, str]] = ..., revokation_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class DataModelChange(_message.Message):
    __slots__ = ("common", "model_id", "new_value", "old_value", "property_name")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    common: Common
    model_id: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., model_id: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ...) -> None: ...

class DataModelCreate(_message.Message):
    __slots__ = ("common", "model_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    model_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., model_id: _Optional[str] = ...) -> None: ...

class DataModelDelete(_message.Message):
    __slots__ = ("common", "model_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    model_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., model_id: _Optional[str] = ...) -> None: ...

class DataAccess(_message.Message):
    __slots__ = ("common", "channel_type", "channel_id", "object_type", "object_id", "attribute", "value", "attachment_type", "attachment_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ATTACHMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTACHMENT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    channel_type: str
    channel_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    attachment_type: str
    attachment_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., channel_type: _Optional[str] = ..., channel_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., attachment_type: _Optional[str] = ..., attachment_id: _Optional[str] = ...) -> None: ...

class DataCreate(_message.Message):
    __slots__ = ("common", "object_type", "object_id", "attribute", "value")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DataDelete(_message.Message):
    __slots__ = ("common", "object_type", "object_id", "attribute", "value")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DataModification(_message.Message):
    __slots__ = ("common", "object_type", "object_id", "attribute", "new_value", "old_value")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    object_type: str
    object_id: str
    attribute: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DataExport(_message.Message):
    __slots__ = ("common", "channel_type", "channel_id", "object_type", "object_id", "destination_uri")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_URI_FIELD_NUMBER: _ClassVar[int]
    common: Common
    channel_type: DataExportChannelType
    channel_id: str
    object_type: str
    object_id: str
    destination_uri: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., channel_type: _Optional[_Union[DataExportChannelType, str]] = ..., channel_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., destination_uri: _Optional[str] = ...) -> None: ...

class DppDataAccess(_message.Message):
    __slots__ = ("common", "channel_type", "channel_id", "data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "value", "attachment_type", "attachment_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
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
    common: Common
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
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., channel_type: _Optional[str] = ..., channel_id: _Optional[str] = ..., data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., attachment_type: _Optional[str] = ..., attachment_id: _Optional[str] = ...) -> None: ...

class DppDataCreate(_message.Message):
    __slots__ = ("common", "data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "value")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DppDataDelete(_message.Message):
    __slots__ = ("common", "data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "value")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    value: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class DppDataModification(_message.Message):
    __slots__ = ("common", "data_subject_type", "data_subject_id", "object_type", "object_id", "attribute", "new_value", "old_value")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    data_subject_type: str
    data_subject_id: str
    object_type: str
    object_id: str
    attribute: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., data_subject_type: _Optional[str] = ..., data_subject_id: _Optional[str] = ..., object_type: _Optional[str] = ..., object_id: _Optional[str] = ..., attribute: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class JobChange(_message.Message):
    __slots__ = ("common", "job_id", "new_value", "old_value", "property_name")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    common: Common
    job_id: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., job_id: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ...) -> None: ...

class JobCreate(_message.Message):
    __slots__ = ("common", "job_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    job_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., job_id: _Optional[str] = ...) -> None: ...

class JobDelete(_message.Message):
    __slots__ = ("common", "job_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    job_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., job_id: _Optional[str] = ...) -> None: ...

class JobStatusChange(_message.Message):
    __slots__ = ("common", "job_id", "new_value", "old_value", "property_name")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    common: Common
    job_id: str
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., job_id: _Optional[str] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ...) -> None: ...

class MaliciousRequestDetected(_message.Message):
    __slots__ = ("common", "parameter", "expected_value", "received_value", "behavior")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_VALUE_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_VALUE_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOR_FIELD_NUMBER: _ClassVar[int]
    common: Common
    parameter: str
    expected_value: str
    received_value: str
    behavior: MaliciousBehavior
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., parameter: _Optional[str] = ..., expected_value: _Optional[str] = ..., received_value: _Optional[str] = ..., behavior: _Optional[_Union[MaliciousBehavior, str]] = ...) -> None: ...

class PasswordChange(_message.Message):
    __slots__ = ("common", "user_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ...) -> None: ...

class PasswordExpiration(_message.Message):
    __slots__ = ("common", "user_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ...) -> None: ...

class PasswordReset(_message.Message):
    __slots__ = ("common", "user_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ...) -> None: ...

class TenantModification(_message.Message):
    __slots__ = ("common", "new_value", "old_value", "property_name", "tenant_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    tenant_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., tenant_id: _Optional[str] = ...) -> None: ...

class TenantOffboarding(_message.Message):
    __slots__ = ("common", "tenant_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    tenant_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., tenant_id: _Optional[str] = ...) -> None: ...

class TenantOnboarding(_message.Message):
    __slots__ = ("common", "tenant_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    tenant_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., tenant_id: _Optional[str] = ...) -> None: ...

class UnauthenticatedRequest(_message.Message):
    __slots__ = ("common",)
    COMMON_FIELD_NUMBER: _ClassVar[int]
    common: Common
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ...) -> None: ...

class UnauthorizedRequest(_message.Message):
    __slots__ = ("common", "unauthorized_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    UNAUTHORIZED_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    unauthorized_type: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., unauthorized_type: _Optional[str] = ...) -> None: ...

class UserActivate(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserBlock(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserCreate(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserDataModification(_message.Message):
    __slots__ = ("common", "new_value", "old_value", "property_name", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    NEW_VALUE_FIELD_NUMBER: _ClassVar[int]
    OLD_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    new_value: _struct_pb2.Value
    old_value: _struct_pb2.Value
    property_name: str
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., new_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., old_value: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., property_name: _Optional[str] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserDelete(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserImpersonationStart(_message.Message):
    __slots__ = ("common", "user_initiator_id", "user_initiator_type", "user_impersonated_id", "user_impersonated_type", "context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_initiator_id: str
    user_initiator_type: UserType
    user_impersonated_id: str
    user_impersonated_type: UserType
    context: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_initiator_id: _Optional[str] = ..., user_initiator_type: _Optional[_Union[UserType, str]] = ..., user_impersonated_id: _Optional[str] = ..., user_impersonated_type: _Optional[_Union[UserType, str]] = ..., context: _Optional[str] = ...) -> None: ...

class UserImpersonationFinish(_message.Message):
    __slots__ = ("common", "user_initiator_id", "user_initiator_type", "user_impersonated_id", "user_impersonated_type", "context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_initiator_id: str
    user_initiator_type: UserType
    user_impersonated_id: str
    user_impersonated_type: UserType
    context: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_initiator_id: _Optional[str] = ..., user_initiator_type: _Optional[_Union[UserType, str]] = ..., user_impersonated_id: _Optional[str] = ..., user_impersonated_type: _Optional[_Union[UserType, str]] = ..., context: _Optional[str] = ...) -> None: ...

class UserLock(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserUnlock(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserVerify(_message.Message):
    __slots__ = ("common", "user_id", "user_type")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_id: str
    user_type: UserType
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_id: _Optional[str] = ..., user_type: _Optional[_Union[UserType, str]] = ...) -> None: ...

class UserLoginFailure(_message.Message):
    __slots__ = ("common", "failure_reason", "method", "is_admin", "mfa_type", "user_type", "login_protocol")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    FAILURE_REASON_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    IS_ADMIN_FIELD_NUMBER: _ClassVar[int]
    MFA_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    LOGIN_PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    common: Common
    failure_reason: FailureReason
    method: LoginMethod
    is_admin: bool
    mfa_type: MfaType
    user_type: UserType
    login_protocol: LoginProtocol
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., failure_reason: _Optional[_Union[FailureReason, str]] = ..., method: _Optional[_Union[LoginMethod, str]] = ..., is_admin: _Optional[bool] = ..., mfa_type: _Optional[_Union[MfaType, str]] = ..., user_type: _Optional[_Union[UserType, str]] = ..., login_protocol: _Optional[_Union[LoginProtocol, str]] = ...) -> None: ...

class UserLoginSuccess(_message.Message):
    __slots__ = ("common", "is_admin", "method", "mfa_type", "user_type", "login_protocol")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    IS_ADMIN_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    MFA_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_TYPE_FIELD_NUMBER: _ClassVar[int]
    LOGIN_PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    common: Common
    is_admin: bool
    method: LoginMethod
    mfa_type: MfaType
    user_type: UserType
    login_protocol: LoginProtocol
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., is_admin: _Optional[bool] = ..., method: _Optional[_Union[LoginMethod, str]] = ..., mfa_type: _Optional[_Union[MfaType, str]] = ..., user_type: _Optional[_Union[UserType, str]] = ..., login_protocol: _Optional[_Union[LoginProtocol, str]] = ...) -> None: ...

class UserLogoff(_message.Message):
    __slots__ = ("common", "logoff_type", "login_protocol")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    LOGOFF_TYPE_FIELD_NUMBER: _ClassVar[int]
    LOGIN_PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    common: Common
    logoff_type: LogoffType
    login_protocol: LoginProtocol
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., logoff_type: _Optional[_Union[LogoffType, str]] = ..., login_protocol: _Optional[_Union[LoginProtocol, str]] = ...) -> None: ...

class ZzzCustomEvent(_message.Message):
    __slots__ = ("common", "custom")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    common: Common
    custom: _struct_pb2.Value
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., custom: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ...) -> None: ...

class CMKOnboarding(_message.Message):
    __slots__ = ("common", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class CMKOffboarding(_message.Message):
    __slots__ = ("common", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class CMKSwitch(_message.Message):
    __slots__ = ("common", "system_id", "cmk_id_old", "cmk_id_new")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_OLD_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_NEW_FIELD_NUMBER: _ClassVar[int]
    common: Common
    system_id: str
    cmk_id_old: str
    cmk_id_new: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., system_id: _Optional[str] = ..., cmk_id_old: _Optional[str] = ..., cmk_id_new: _Optional[str] = ...) -> None: ...

class CMKTenantModification(_message.Message):
    __slots__ = ("common", "system_id", "cmk_id", "cmk_action")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ACTION_FIELD_NUMBER: _ClassVar[int]
    common: Common
    system_id: str
    cmk_id: str
    cmk_action: CMKAction
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ..., cmk_action: _Optional[_Union[CMKAction, str]] = ...) -> None: ...

class CMKCreate(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKDelete(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKRestore(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKDisable(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKEnable(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKRotate(_message.Message):
    __slots__ = ("common", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyCreate(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyDelete(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyRestore(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyPurge(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyRotate(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyEnable(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyDisable(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeySuspend(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class KeyOnboardKeyChain(_message.Message):
    __slots__ = ("common", "key_type", "key_id", "system_id", "cmk_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    key_type: KeyType
    key_id: str
    system_id: str
    cmk_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., key_id: _Optional[str] = ..., system_id: _Optional[str] = ..., cmk_id: _Optional[str] = ...) -> None: ...

class CMKDrop(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKSuspend(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class VirusFinding(_message.Message):
    __slots__ = ("common", "virus_name", "file_name", "virus_channel")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    VIRUS_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    VIRUS_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    common: Common
    virus_name: str
    file_name: str
    virus_channel: VirusChannel
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., virus_name: _Optional[str] = ..., file_name: _Optional[str] = ..., virus_channel: _Optional[_Union[VirusChannel, str]] = ...) -> None: ...

class CMKUnavailable(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKAvailable(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ...) -> None: ...

class CMKDetach(_message.Message):
    __slots__ = ("common", "cmk_id", "kms_system_id", "system_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CMK_ID_FIELD_NUMBER: _ClassVar[int]
    KMS_SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    cmk_id: str
    kms_system_id: str
    system_id: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., cmk_id: _Optional[str] = ..., kms_system_id: _Optional[str] = ..., system_id: _Optional[str] = ...) -> None: ...
