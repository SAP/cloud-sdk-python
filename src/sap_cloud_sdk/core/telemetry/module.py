"""Types for telemetry module definitions."""

from enum import Enum


class Module(str, Enum):
    """SDK module identifiers for telemetry."""

    AICORE = "aicore"
    AUDITLOG = "auditlog"
    AUDITLOG_NG = "auditlog_ng"
    DATA_ANONYMIZATION = "data_anonymization"
    DESTINATION = "destination"
    OBJECTSTORE = "objectstore"
    DMS = "dms"

    def __str__(self) -> str:
        return self.value
