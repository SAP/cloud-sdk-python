"""Action input/output DTOs for consentServices - not OData entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .utils import _CamelSerializable


@dataclass
class CheckConsentExistsResult:
    """Returned by checkConsentExists action."""

    consent_id: str | None = None
    consent_exists: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckConsentExistsResult:
        """Construct from a raw OData action response dict."""
        return cls(
            consent_id=data.get("consentId"), consent_exists=data.get("consentExists")
        )


@dataclass
class CreateConsentRequest(_CamelSerializable):
    """Input for createConsentFromTemplate / createConsentFromTemplateAsync."""

    data_subject_id: str
    template_name: str
    language_code: str
    data_subject_type_name: str
    jurisdiction_code: str
    data_subject_description: str | None = None
    outbound_channel_type_name: str | None = None
    outbound_channel: str | None = None
    valid_from: str | None = None
    application_template_id: str | None = None
    controller_name: str | None = None
    granted_by: str | None = None
    granted_at: str | None = None
    submission_site: str | None = None


@dataclass
class WithdrawConsentRequest(_CamelSerializable):
    """Input for withdrawConsent and terminateConsent."""

    consent_id: str
    withdrawn_by: str
    withdrawn_at: str | None = None
