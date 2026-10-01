"""python-odata entity classes for consentRetentionExternalServices."""

from __future__ import annotations

from typing import Any

from odata.property import (
    DatetimeProperty,
    IntegerProperty,
    StringProperty,
    UUIDProperty,
)


def _make_entities(Service: Any) -> tuple:
    """Create and return all entity classes bound to the given ODataService instance."""

    class ConsentRetentionRule(Service.Entity):
        """OData entity representing a data retention rule for consents."""

        __odata_collection__ = "consentRetentionRules"
        tenant = StringProperty("tenant")
        rule_id = UUIDProperty("ruleId", primary_key=True)
        rule_name = StringProperty("ruleName")
        lifecycle_status_code = StringProperty("lifecycleStatusCode")
        purpose_id = UUIDProperty("purposeId")
        controller_id = UUIDProperty("controllerId")
        jurisdiction_code = StringProperty("jurisdictionCode")
        consent_model_code = StringProperty("consentModelCode")
        retention_period = IntegerProperty("retentionPeriod")
        retention_years = IntegerProperty("retentionYears")
        retention_months = IntegerProperty("retentionMonths")
        retention_days = IntegerProperty("retentionDays")
        purpose_name = StringProperty("purposeName")
        controller_name = StringProperty("controllerName")
        created_at = DatetimeProperty("createdAt")
        created_by = StringProperty("createdBy")
        changed_at = DatetimeProperty("changedAt")
        changed_by = StringProperty("changedBy")

    return (ConsentRetentionRule,)
