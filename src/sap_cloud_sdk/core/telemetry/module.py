"""Types for telemetry module definitions."""

from enum import Enum


class Module(str, Enum):
    """SDK module identifiers for telemetry."""

    AICORE = "aicore"
    AUDITLOG = "auditlog"
    AUDITLOG_NG = "auditlog_ng"
    AGENT_MEMORY = "agent_memory"
    DESTINATION = "destination"
    EXTENSIBILITY = "extensibility"
    OBJECTSTORE = "objectstore"
    DMS = "dms"
    AGENTGATEWAY = "agentgateway"

    def __str__(self) -> str:
        return self.value
