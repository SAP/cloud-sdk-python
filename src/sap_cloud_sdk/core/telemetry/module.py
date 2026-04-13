"""Types for telemetry module definitions."""

from enum import Enum


class Module(str, Enum):
    """SDK module identifiers for telemetry."""

    AICORE = "aicore"
    AUDITLOG = "auditlog"
    DESTINATION = "destination"
    OBJECTSTORE = "objectstore"
    DMS = "dms"

    def __str__(self) -> str:
        return self.value
