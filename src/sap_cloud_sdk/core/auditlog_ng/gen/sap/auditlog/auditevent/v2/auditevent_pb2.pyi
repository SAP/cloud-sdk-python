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

class AiRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_ROLE_UNSPECIFIED: _ClassVar[AiRole]
    AI_ROLE_USER: _ClassVar[AiRole]
    AI_ROLE_ASSISTANT: _ClassVar[AiRole]
    AI_ROLE_TOOL: _ClassVar[AiRole]
    AI_ROLE_AGENT: _ClassVar[AiRole]
    AI_ROLE_ORCHESTRATOR: _ClassVar[AiRole]
    AI_ROLE_RETRIEVER: _ClassVar[AiRole]
    AI_ROLE_OTHER: _ClassVar[AiRole]

class AiAgentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_AGENT_TYPE_UNSPECIFIED: _ClassVar[AiAgentType]
    AI_AGENT_TYPE_CONVERSATIONAL: _ClassVar[AiAgentType]
    AI_AGENT_TYPE_AUTONOMOUS: _ClassVar[AiAgentType]
    AI_AGENT_TYPE_RETRIEVAL: _ClassVar[AiAgentType]
    AI_AGENT_TYPE_MULTI_AGENT: _ClassVar[AiAgentType]
    AI_AGENT_TYPE_OTHER: _ClassVar[AiAgentType]

class AiSessionEndReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_SESSION_END_REASON_UNSPECIFIED: _ClassVar[AiSessionEndReason]
    AI_SESSION_END_REASON_NORMAL: _ClassVar[AiSessionEndReason]
    AI_SESSION_END_REASON_TIMEOUT: _ClassVar[AiSessionEndReason]
    AI_SESSION_END_REASON_USER_TERMINATED: _ClassVar[AiSessionEndReason]
    AI_SESSION_END_REASON_ERROR: _ClassVar[AiSessionEndReason]
    AI_SESSION_END_REASON_POLICY_VIOLATION: _ClassVar[AiSessionEndReason]
    AI_SESSION_END_REASON_OTHER: _ClassVar[AiSessionEndReason]

class AiGuardrailType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_GUARDRAIL_TYPE_UNSPECIFIED: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_INPUT: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_OUTPUT: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_CONTENT_POLICY: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_PROMPT_INJECTION: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_PII_FILTER: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_DATA_LEAKAGE: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_HALLUCINATION: _ClassVar[AiGuardrailType]
    AI_GUARDRAIL_TYPE_OTHER: _ClassVar[AiGuardrailType]

class AiGuardrailAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_GUARDRAIL_ACTION_UNSPECIFIED: _ClassVar[AiGuardrailAction]
    AI_GUARDRAIL_ACTION_ALLOW: _ClassVar[AiGuardrailAction]
    AI_GUARDRAIL_ACTION_BLOCK: _ClassVar[AiGuardrailAction]
    AI_GUARDRAIL_ACTION_MODIFY: _ClassVar[AiGuardrailAction]
    AI_GUARDRAIL_ACTION_WARN: _ClassVar[AiGuardrailAction]
    AI_GUARDRAIL_ACTION_LOG_ONLY: _ClassVar[AiGuardrailAction]
    AI_GUARDRAIL_ACTION_OTHER: _ClassVar[AiGuardrailAction]

class AiInvocationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_INVOCATION_STATUS_UNSPECIFIED: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_SUCCESS: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_FAILED: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_TIMEOUT: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_RATE_LIMITED: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_CANCELLED: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_PENDING: _ClassVar[AiInvocationStatus]
    AI_INVOCATION_STATUS_OTHER: _ClassVar[AiInvocationStatus]

class AiRetrievalType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_RETRIEVAL_TYPE_UNSPECIFIED: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_VECTOR_SEARCH: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_KEYWORD_SEARCH: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_HYBRID_SEARCH: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_KNOWLEDGE_GRAPH: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_MEMORY_CONTEXT: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_DOCUMENT: _ClassVar[AiRetrievalType]
    AI_RETRIEVAL_TYPE_OTHER: _ClassVar[AiRetrievalType]

class AiFeedbackRating(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_FEEDBACK_RATING_UNSPECIFIED: _ClassVar[AiFeedbackRating]
    AI_FEEDBACK_RATING_POSITIVE: _ClassVar[AiFeedbackRating]
    AI_FEEDBACK_RATING_NEGATIVE: _ClassVar[AiFeedbackRating]
    AI_FEEDBACK_RATING_NEUTRAL: _ClassVar[AiFeedbackRating]
    AI_FEEDBACK_RATING_CORRECTION: _ClassVar[AiFeedbackRating]
    AI_FEEDBACK_RATING_OTHER: _ClassVar[AiFeedbackRating]

class AiToolCallDisposition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_TOOL_CALL_DISPOSITION_UNSPECIFIED: _ClassVar[AiToolCallDisposition]
    AI_TOOL_CALL_DISPOSITION_ALLOWED: _ClassVar[AiToolCallDisposition]
    AI_TOOL_CALL_DISPOSITION_DENIED: _ClassVar[AiToolCallDisposition]
    AI_TOOL_CALL_DISPOSITION_MODIFIED: _ClassVar[AiToolCallDisposition]
    AI_TOOL_CALL_DISPOSITION_PENDING_APPROVAL: _ClassVar[AiToolCallDisposition]
    AI_TOOL_CALL_DISPOSITION_OTHER: _ClassVar[AiToolCallDisposition]

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
    USER_TYPE_SAP_SUPPORT_USER: _ClassVar[UserType]
    USER_TYPE_AI_AGENT: _ClassVar[UserType]

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

class AiTaskUpdateType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AI_TASK_UPDATE_TYPE_UNSPECIFIED: _ClassVar[AiTaskUpdateType]
    AI_TASK_UPDATE_TYPE_STATUS: _ClassVar[AiTaskUpdateType]
    AI_TASK_UPDATE_TYPE_ARTIFACT: _ClassVar[AiTaskUpdateType]
    AI_TASK_UPDATE_TYPE_INPUT_REQUIRED: _ClassVar[AiTaskUpdateType]

class LoginProtocol(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOGIN_PROTOCOL_UNSPECIFIED: _ClassVar[LoginProtocol]
    LOGIN_PROTOCOL_SAML2: _ClassVar[LoginProtocol]
    LOGIN_PROTOCOL_OIDC: _ClassVar[LoginProtocol]
    LOGIN_PROTOCOL_HTTP: _ClassVar[LoginProtocol]
AI_ROLE_UNSPECIFIED: AiRole
AI_ROLE_USER: AiRole
AI_ROLE_ASSISTANT: AiRole
AI_ROLE_TOOL: AiRole
AI_ROLE_AGENT: AiRole
AI_ROLE_ORCHESTRATOR: AiRole
AI_ROLE_RETRIEVER: AiRole
AI_ROLE_OTHER: AiRole
AI_AGENT_TYPE_UNSPECIFIED: AiAgentType
AI_AGENT_TYPE_CONVERSATIONAL: AiAgentType
AI_AGENT_TYPE_AUTONOMOUS: AiAgentType
AI_AGENT_TYPE_RETRIEVAL: AiAgentType
AI_AGENT_TYPE_MULTI_AGENT: AiAgentType
AI_AGENT_TYPE_OTHER: AiAgentType
AI_SESSION_END_REASON_UNSPECIFIED: AiSessionEndReason
AI_SESSION_END_REASON_NORMAL: AiSessionEndReason
AI_SESSION_END_REASON_TIMEOUT: AiSessionEndReason
AI_SESSION_END_REASON_USER_TERMINATED: AiSessionEndReason
AI_SESSION_END_REASON_ERROR: AiSessionEndReason
AI_SESSION_END_REASON_POLICY_VIOLATION: AiSessionEndReason
AI_SESSION_END_REASON_OTHER: AiSessionEndReason
AI_GUARDRAIL_TYPE_UNSPECIFIED: AiGuardrailType
AI_GUARDRAIL_TYPE_INPUT: AiGuardrailType
AI_GUARDRAIL_TYPE_OUTPUT: AiGuardrailType
AI_GUARDRAIL_TYPE_CONTENT_POLICY: AiGuardrailType
AI_GUARDRAIL_TYPE_PROMPT_INJECTION: AiGuardrailType
AI_GUARDRAIL_TYPE_PII_FILTER: AiGuardrailType
AI_GUARDRAIL_TYPE_DATA_LEAKAGE: AiGuardrailType
AI_GUARDRAIL_TYPE_HALLUCINATION: AiGuardrailType
AI_GUARDRAIL_TYPE_OTHER: AiGuardrailType
AI_GUARDRAIL_ACTION_UNSPECIFIED: AiGuardrailAction
AI_GUARDRAIL_ACTION_ALLOW: AiGuardrailAction
AI_GUARDRAIL_ACTION_BLOCK: AiGuardrailAction
AI_GUARDRAIL_ACTION_MODIFY: AiGuardrailAction
AI_GUARDRAIL_ACTION_WARN: AiGuardrailAction
AI_GUARDRAIL_ACTION_LOG_ONLY: AiGuardrailAction
AI_GUARDRAIL_ACTION_OTHER: AiGuardrailAction
AI_INVOCATION_STATUS_UNSPECIFIED: AiInvocationStatus
AI_INVOCATION_STATUS_SUCCESS: AiInvocationStatus
AI_INVOCATION_STATUS_FAILED: AiInvocationStatus
AI_INVOCATION_STATUS_TIMEOUT: AiInvocationStatus
AI_INVOCATION_STATUS_RATE_LIMITED: AiInvocationStatus
AI_INVOCATION_STATUS_CANCELLED: AiInvocationStatus
AI_INVOCATION_STATUS_PENDING: AiInvocationStatus
AI_INVOCATION_STATUS_OTHER: AiInvocationStatus
AI_RETRIEVAL_TYPE_UNSPECIFIED: AiRetrievalType
AI_RETRIEVAL_TYPE_VECTOR_SEARCH: AiRetrievalType
AI_RETRIEVAL_TYPE_KEYWORD_SEARCH: AiRetrievalType
AI_RETRIEVAL_TYPE_HYBRID_SEARCH: AiRetrievalType
AI_RETRIEVAL_TYPE_KNOWLEDGE_GRAPH: AiRetrievalType
AI_RETRIEVAL_TYPE_MEMORY_CONTEXT: AiRetrievalType
AI_RETRIEVAL_TYPE_DOCUMENT: AiRetrievalType
AI_RETRIEVAL_TYPE_OTHER: AiRetrievalType
AI_FEEDBACK_RATING_UNSPECIFIED: AiFeedbackRating
AI_FEEDBACK_RATING_POSITIVE: AiFeedbackRating
AI_FEEDBACK_RATING_NEGATIVE: AiFeedbackRating
AI_FEEDBACK_RATING_NEUTRAL: AiFeedbackRating
AI_FEEDBACK_RATING_CORRECTION: AiFeedbackRating
AI_FEEDBACK_RATING_OTHER: AiFeedbackRating
AI_TOOL_CALL_DISPOSITION_UNSPECIFIED: AiToolCallDisposition
AI_TOOL_CALL_DISPOSITION_ALLOWED: AiToolCallDisposition
AI_TOOL_CALL_DISPOSITION_DENIED: AiToolCallDisposition
AI_TOOL_CALL_DISPOSITION_MODIFIED: AiToolCallDisposition
AI_TOOL_CALL_DISPOSITION_PENDING_APPROVAL: AiToolCallDisposition
AI_TOOL_CALL_DISPOSITION_OTHER: AiToolCallDisposition
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
USER_TYPE_SAP_SUPPORT_USER: UserType
USER_TYPE_AI_AGENT: UserType
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
AI_TASK_UPDATE_TYPE_UNSPECIFIED: AiTaskUpdateType
AI_TASK_UPDATE_TYPE_STATUS: AiTaskUpdateType
AI_TASK_UPDATE_TYPE_ARTIFACT: AiTaskUpdateType
AI_TASK_UPDATE_TYPE_INPUT_REQUIRED: AiTaskUpdateType
LOGIN_PROTOCOL_UNSPECIFIED: LoginProtocol
LOGIN_PROTOCOL_SAML2: LoginProtocol
LOGIN_PROTOCOL_OIDC: LoginProtocol
LOGIN_PROTOCOL_HTTP: LoginProtocol

class UserContext(_message.Message):
    __slots__ = ("type", "attributes")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    type: UserType
    attributes: _containers.ScalarMap[str, str]
    def __init__(self, type: _Optional[_Union[UserType, str]] = ..., attributes: _Optional[_Mapping[str, str]] = ...) -> None: ...

class TraceContext(_message.Message):
    __slots__ = ("trace_id", "span_id")
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    trace_id: str
    span_id: str
    def __init__(self, trace_id: _Optional[str] = ..., span_id: _Optional[str] = ...) -> None: ...

class AiModel(_message.Message):
    __slots__ = ("ai_provider", "name", "uid", "version")
    AI_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ai_provider: str
    name: str
    uid: str
    version: str
    def __init__(self, ai_provider: _Optional[str] = ..., name: _Optional[str] = ..., uid: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class AiAgent(_message.Message):
    __slots__ = ("uid", "name", "instance_uid", "type", "type_id", "version", "ai_model")
    UID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_UID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    AI_MODEL_FIELD_NUMBER: _ClassVar[int]
    uid: str
    name: str
    instance_uid: str
    type: str
    type_id: AiAgentType
    version: str
    ai_model: AiModel
    def __init__(self, uid: _Optional[str] = ..., name: _Optional[str] = ..., instance_uid: _Optional[str] = ..., type: _Optional[str] = ..., type_id: _Optional[_Union[AiAgentType, str]] = ..., version: _Optional[str] = ..., ai_model: _Optional[_Union[AiModel, _Mapping]] = ...) -> None: ...

class AiMessageContext(_message.Message):
    __slots__ = ("uid", "name", "ai_role_id", "prompt_text", "response_text", "prompt_tokens", "completion_tokens", "total_tokens")
    UID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    AI_ROLE_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_TEXT_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_TEXT_FIELD_NUMBER: _ClassVar[int]
    PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    uid: str
    name: str
    ai_role_id: AiRole
    prompt_text: str
    response_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    def __init__(self, uid: _Optional[str] = ..., name: _Optional[str] = ..., ai_role_id: _Optional[_Union[AiRole, str]] = ..., prompt_text: _Optional[str] = ..., response_text: _Optional[str] = ..., prompt_tokens: _Optional[int] = ..., completion_tokens: _Optional[int] = ..., total_tokens: _Optional[int] = ...) -> None: ...

class AiDelegation(_message.Message):
    __slots__ = ("delegator_id", "delegate_id", "scopes", "expires_at", "delegation_chain")
    DELEGATOR_ID_FIELD_NUMBER: _ClassVar[int]
    DELEGATE_ID_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_CHAIN_FIELD_NUMBER: _ClassVar[int]
    delegator_id: str
    delegate_id: str
    scopes: _containers.RepeatedScalarFieldContainer[str]
    expires_at: _timestamp_pb2.Timestamp
    delegation_chain: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, delegator_id: _Optional[str] = ..., delegate_id: _Optional[str] = ..., scopes: _Optional[_Iterable[str]] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., delegation_chain: _Optional[_Iterable[str]] = ...) -> None: ...

class Common(_message.Message):
    __slots__ = ("timestamp", "source_ip", "user_impersonated_id", "user_initiator_id", "app_id", "tenant_id", "user_session_context_id", "app_context", "user_global_id", "user_impersonated_global_id", "user_initiator_context", "user_impersonated_context", "trace_context")
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
    USER_GLOBAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_GLOBAL_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    TRACE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    source_ip: _containers.RepeatedScalarFieldContainer[str]
    user_impersonated_id: str
    user_initiator_id: str
    app_id: str
    tenant_id: str
    user_session_context_id: str
    app_context: _containers.ScalarMap[str, str]
    user_global_id: str
    user_impersonated_global_id: str
    user_initiator_context: UserContext
    user_impersonated_context: UserContext
    trace_context: TraceContext
    def __init__(self, timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source_ip: _Optional[_Iterable[str]] = ..., user_impersonated_id: _Optional[str] = ..., user_initiator_id: _Optional[str] = ..., app_id: _Optional[str] = ..., tenant_id: _Optional[str] = ..., user_session_context_id: _Optional[str] = ..., app_context: _Optional[_Mapping[str, str]] = ..., user_global_id: _Optional[str] = ..., user_impersonated_global_id: _Optional[str] = ..., user_initiator_context: _Optional[_Union[UserContext, _Mapping]] = ..., user_impersonated_context: _Optional[_Union[UserContext, _Mapping]] = ..., trace_context: _Optional[_Union[TraceContext, _Mapping]] = ...) -> None: ...

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

class AiSessionStart(_message.Message):
    __slots__ = ("common", "session_id", "ai_agent", "ai_model", "delegation")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    AI_MODEL_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    ai_agent: AiAgent
    ai_model: AiModel
    delegation: AiDelegation
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., ai_model: _Optional[_Union[AiModel, _Mapping]] = ..., delegation: _Optional[_Union[AiDelegation, _Mapping]] = ...) -> None: ...

class AiSessionEnd(_message.Message):
    __slots__ = ("common", "session_id", "end_reason", "total_tokens", "duration_ms")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    END_REASON_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    end_reason: AiSessionEndReason
    total_tokens: int
    duration_ms: int
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., end_reason: _Optional[_Union[AiSessionEndReason, str]] = ..., total_tokens: _Optional[int] = ..., duration_ms: _Optional[int] = ...) -> None: ...

class AiPromptReceived(_message.Message):
    __slots__ = ("common", "session_id", "message_context", "ai_agent")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    message_context: AiMessageContext
    ai_agent: AiAgent
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ...) -> None: ...

class AiGuardrailTriggered(_message.Message):
    __slots__ = ("common", "session_id", "guardrail_name", "guardrail_type", "action_taken", "violation_category", "message_context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    GUARDRAIL_NAME_FIELD_NUMBER: _ClassVar[int]
    GUARDRAIL_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTION_TAKEN_FIELD_NUMBER: _ClassVar[int]
    VIOLATION_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    guardrail_name: str
    guardrail_type: AiGuardrailType
    action_taken: AiGuardrailAction
    violation_category: str
    message_context: AiMessageContext
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., guardrail_name: _Optional[str] = ..., guardrail_type: _Optional[_Union[AiGuardrailType, str]] = ..., action_taken: _Optional[_Union[AiGuardrailAction, str]] = ..., violation_category: _Optional[str] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ...) -> None: ...

class AiModelInvocation(_message.Message):
    __slots__ = ("common", "session_id", "ai_model", "ai_agent", "message_context", "latency_ms", "status", "error_message")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    AI_MODEL_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    ai_model: AiModel
    ai_agent: AiAgent
    message_context: AiMessageContext
    latency_ms: int
    status: AiInvocationStatus
    error_message: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., ai_model: _Optional[_Union[AiModel, _Mapping]] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ..., latency_ms: _Optional[int] = ..., status: _Optional[_Union[AiInvocationStatus, str]] = ..., error_message: _Optional[str] = ...) -> None: ...

class AiSkillSelected(_message.Message):
    __slots__ = ("common", "session_id", "skill_name", "skill_id", "confidence_score", "ai_agent", "alternatives_considered")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    SKILL_NAME_FIELD_NUMBER: _ClassVar[int]
    SKILL_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_SCORE_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    ALTERNATIVES_CONSIDERED_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    skill_name: str
    skill_id: str
    confidence_score: float
    ai_agent: AiAgent
    alternatives_considered: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., skill_name: _Optional[str] = ..., skill_id: _Optional[str] = ..., confidence_score: _Optional[float] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., alternatives_considered: _Optional[_Iterable[str]] = ...) -> None: ...

class AiAgentDelegated(_message.Message):
    __slots__ = ("common", "session_id", "source_agent", "target_agent", "delegation", "task_description")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_AGENT_FIELD_NUMBER: _ClassVar[int]
    TARGET_AGENT_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_FIELD_NUMBER: _ClassVar[int]
    TASK_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    source_agent: AiAgent
    target_agent: AiAgent
    delegation: AiDelegation
    task_description: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., source_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., target_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., delegation: _Optional[_Union[AiDelegation, _Mapping]] = ..., task_description: _Optional[str] = ...) -> None: ...

class AiMcpToolCall(_message.Message):
    __slots__ = ("common", "session_id", "tool_name", "target_mcp_server_id", "ai_agent", "status", "latency_ms", "error_message")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    TARGET_MCP_SERVER_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    tool_name: str
    target_mcp_server_id: str
    ai_agent: AiAgent
    status: AiInvocationStatus
    latency_ms: int
    error_message: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., tool_name: _Optional[str] = ..., target_mcp_server_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., status: _Optional[_Union[AiInvocationStatus, str]] = ..., latency_ms: _Optional[int] = ..., error_message: _Optional[str] = ...) -> None: ...

class AiDirectApiAccess(_message.Message):
    __slots__ = ("common", "session_id", "target_api_id", "ai_agent", "http_method", "status", "response_status_code", "latency_ms")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_API_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    HTTP_METHOD_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    target_api_id: str
    ai_agent: AiAgent
    http_method: str
    status: AiInvocationStatus
    response_status_code: int
    latency_ms: int
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., target_api_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., http_method: _Optional[str] = ..., status: _Optional[_Union[AiInvocationStatus, str]] = ..., response_status_code: _Optional[int] = ..., latency_ms: _Optional[int] = ...) -> None: ...

class AiDataRetrieval(_message.Message):
    __slots__ = ("common", "session_id", "data_source_id", "data_source_type", "retrieval_type", "results_count", "ai_agent", "latency_ms")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    RETRIEVAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    RESULTS_COUNT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    data_source_id: str
    data_source_type: str
    retrieval_type: AiRetrievalType
    results_count: int
    ai_agent: AiAgent
    latency_ms: int
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., data_source_id: _Optional[str] = ..., data_source_type: _Optional[str] = ..., retrieval_type: _Optional[_Union[AiRetrievalType, str]] = ..., results_count: _Optional[int] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., latency_ms: _Optional[int] = ...) -> None: ...

class AiResponseGenerated(_message.Message):
    __slots__ = ("common", "session_id", "message_context", "ai_agent", "ai_model", "latency_ms")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    AI_MODEL_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    message_context: AiMessageContext
    ai_agent: AiAgent
    ai_model: AiModel
    latency_ms: int
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., ai_model: _Optional[_Union[AiModel, _Mapping]] = ..., latency_ms: _Optional[int] = ...) -> None: ...

class AiUserFeedback(_message.Message):
    __slots__ = ("common", "session_id", "feedback_rating", "feedback_score", "feedback_category", "feedback_comment", "message_uid")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_RATING_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_SCORE_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_COMMENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_UID_FIELD_NUMBER: _ClassVar[int]
    common: Common
    session_id: str
    feedback_rating: AiFeedbackRating
    feedback_score: int
    feedback_category: str
    feedback_comment: str
    message_uid: str
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., session_id: _Optional[str] = ..., feedback_rating: _Optional[_Union[AiFeedbackRating, str]] = ..., feedback_score: _Optional[int] = ..., feedback_category: _Optional[str] = ..., feedback_comment: _Optional[str] = ..., message_uid: _Optional[str] = ...) -> None: ...

class AiMessageSent(_message.Message):
    __slots__ = ("common", "target_agent", "source_agent", "a2a_task_id", "a2a_context_id", "message_context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    TARGET_AGENT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_AGENT_FIELD_NUMBER: _ClassVar[int]
    A2A_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    target_agent: AiAgent
    source_agent: AiAgent
    a2a_task_id: str
    a2a_context_id: str
    message_context: AiMessageContext
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., target_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., source_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., a2a_task_id: _Optional[str] = ..., a2a_context_id: _Optional[str] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ...) -> None: ...

class AiTaskCreated(_message.Message):
    __slots__ = ("common", "a2a_task_id", "a2a_context_id", "ai_agent", "message_context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    A2A_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    a2a_task_id: str
    a2a_context_id: str
    ai_agent: AiAgent
    message_context: AiMessageContext
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., a2a_task_id: _Optional[str] = ..., a2a_context_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ...) -> None: ...

class AiTaskUpdated(_message.Message):
    __slots__ = ("common", "a2a_task_id", "a2a_context_id", "update_type", "ai_agent", "message_context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    A2A_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TYPE_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    a2a_task_id: str
    a2a_context_id: str
    update_type: AiTaskUpdateType
    ai_agent: AiAgent
    message_context: AiMessageContext
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., a2a_task_id: _Optional[str] = ..., a2a_context_id: _Optional[str] = ..., update_type: _Optional[_Union[AiTaskUpdateType, str]] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ...) -> None: ...

class AiTaskAccessed(_message.Message):
    __slots__ = ("common", "a2a_task_id", "a2a_context_id", "ai_agent")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    A2A_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    a2a_task_id: str
    a2a_context_id: str
    ai_agent: AiAgent
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., a2a_task_id: _Optional[str] = ..., a2a_context_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ...) -> None: ...

class AiPushNotificationSent(_message.Message):
    __slots__ = ("common", "push_notification_url", "a2a_task_id", "a2a_context_id", "ai_agent", "response_status")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PUSH_NOTIFICATION_URL_FIELD_NUMBER: _ClassVar[int]
    A2A_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_STATUS_FIELD_NUMBER: _ClassVar[int]
    common: Common
    push_notification_url: str
    a2a_task_id: str
    a2a_context_id: str
    ai_agent: AiAgent
    response_status: int
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., push_notification_url: _Optional[str] = ..., a2a_task_id: _Optional[str] = ..., a2a_context_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., response_status: _Optional[int] = ...) -> None: ...

class UserImpersonationRequested(_message.Message):
    __slots__ = ("common", "user_initiator_id", "user_initiator_type", "user_impersonated_id", "user_impersonated_type", "context", "ai_agent")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_initiator_id: str
    user_initiator_type: UserType
    user_impersonated_id: str
    user_impersonated_type: UserType
    context: str
    ai_agent: AiAgent
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_initiator_id: _Optional[str] = ..., user_initiator_type: _Optional[_Union[UserType, str]] = ..., user_impersonated_id: _Optional[str] = ..., user_impersonated_type: _Optional[_Union[UserType, str]] = ..., context: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ...) -> None: ...

class UserImpersonationDeclined(_message.Message):
    __slots__ = ("common", "user_initiator_id", "user_initiator_type", "user_impersonated_id", "user_impersonated_type", "context", "ai_agent")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_ID_FIELD_NUMBER: _ClassVar[int]
    USER_INITIATOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_ID_FIELD_NUMBER: _ClassVar[int]
    USER_IMPERSONATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    user_initiator_id: str
    user_initiator_type: UserType
    user_impersonated_id: str
    user_impersonated_type: UserType
    context: str
    ai_agent: AiAgent
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., user_initiator_id: _Optional[str] = ..., user_initiator_type: _Optional[_Union[UserType, str]] = ..., user_impersonated_id: _Optional[str] = ..., user_impersonated_type: _Optional[_Union[UserType, str]] = ..., context: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ...) -> None: ...

class AiUserInputRequested(_message.Message):
    __slots__ = ("common", "requested_from_user_id", "a2a_task_id", "a2a_context_id", "ai_agent", "message_context")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    REQUESTED_FROM_USER_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    A2A_CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    common: Common
    requested_from_user_id: str
    a2a_task_id: str
    a2a_context_id: str
    ai_agent: AiAgent
    message_context: AiMessageContext
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ..., requested_from_user_id: _Optional[str] = ..., a2a_task_id: _Optional[str] = ..., a2a_context_id: _Optional[str] = ..., ai_agent: _Optional[_Union[AiAgent, _Mapping]] = ..., message_context: _Optional[_Union[AiMessageContext, _Mapping]] = ...) -> None: ...
