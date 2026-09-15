"""Action input/output DTOs for consentServices - not OData entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .utils import _CamelSerializable


@dataclass
class CheckConsentExistsResult:
    """Result returned by the ``checkConsentExists`` OData action.

    Attributes:
        consent_id: UUID of the matching Consent record, or ``None`` if none was found.
        consent_exists: ``True`` if an active consent exists for the queried
            data subject and template, ``False`` otherwise.
    """

    consent_id: str | None = None
    consent_exists: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckConsentExistsResult:
        """Construct a ``CheckConsentExistsResult`` from a raw OData action response dict.

        Args:
            data: Parsed JSON response body from the ``checkConsentExists`` action.

        Returns:
            A populated ``CheckConsentExistsResult`` instance.
        """
        return cls(
            consent_id=data.get("consentId"), consent_exists=data.get("consentExists")
        )


@dataclass
class CreateConsentRequest(_CamelSerializable):
    """Input DTO for the ``createConsentFromTemplate`` OData action.

    Required fields must be provided; optional fields default to ``None`` and are
    omitted from the serialised payload when not set.

    Attributes:
        data_subject_id: Identifier of the data subject giving consent.
        template_name: Name of the ConsentTemplate to create from.
        language_code: BCP-47 language code for the consent text (e.g. ``"en"``).
        data_subject_type_name: Name of the DataSubjectType.
        jurisdiction_code: Code of the applicable Jurisdiction.
        data_subject_description: Optional human-readable description of the data subject.
        outbound_channel_type_name: Optional name of the outbound communication channel type.
        outbound_channel: Optional identifier of the specific outbound channel.
        valid_from: Optional ISO-8601 date string for the consent start date.
        application_template_id: Optional application-level template identifier.
        controller_name: Optional name of the data controller.
        granted_by: Optional identifier of the person who recorded the consent grant.
        granted_at: Optional ISO-8601 datetime string when consent was granted.
        submission_site: Optional site identifier where consent was collected.
    """

    data_subject_id: str
    template_name: str
    language_code: str
    data_subject_type_name: str
    jurisdiction_code: str | None = None
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
    """Input DTO for the ``withdrawConsent`` and ``terminateConsent`` OData actions.

    Attributes:
        consent_id: UUID of the Consent record to withdraw or terminate.
        withdrawn_by: Identifier of the person or system initiating the withdrawal.
        withdrawn_at: Optional ISO-8601 datetime string when the withdrawal occurred.
            Defaults to the server timestamp when omitted.
    """

    consent_id: str
    withdrawn_by: str | None = None
    withdrawn_at: str | None = None
