"""Types for telemetry module definitions."""

from enum import Enum


class Module(str, Enum):
    """SDK module identifiers for telemetry."""

    ADMS = "adms"
    AGENT_MEMORY = "agent_memory"
    AGENTGATEWAY = "agentgateway"
    AICORE = "aicore"
    AUDITLOG = "auditlog"
    AUDITLOG_NG = "auditlog_ng"
    DATA_ANONYMIZATION = "data_anonymization"
    DESTINATION = "destination"
    DMS = "dms"
    EXTENSIBILITY = "extensibility"
    OBJECTSTORE = "objectstore"
    TELEMETRY = "telemetry"

    def __str__(self) -> str:
        return self.value
