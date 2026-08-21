"""OData v4 client for the DPI Consent capability."""

from __future__ import annotations

import logging
from typing import Callable

from sap_cloud_sdk.core.dpi_ng.odata_client import BaseODataClient

logger = logging.getLogger(__name__)


class _ConsentODataClient(BaseODataClient):
    """OData v4 client for the DPI Consent module.

    Extends class `BaseODataClient` by registering the five consent service
    entity factories. The session also injects ``x-tenant-id`` when the config
    requires it (mTLS / ``ClientCertificateAuth``).
    """

    def _get_entity_factories(self) -> dict[str, Callable]:
        """Register entity factories for all five consent service endpoints."""
        from .entities.consent import _make_entities as consent_entities
        from .entities.consent_configuration import _make_entities as config_entities
        from .entities.consent_purpose import _make_entities as purpose_entities
        from .entities.consent_retention import _make_entities as retention_entities
        from .entities.consent_template import _make_entities as template_entities

        return {
            "consentServices": consent_entities,
            "consentPurposeExternalServices": purpose_entities,
            "consentTemplateExternalServices": template_entities,
            "consentRetentionExternalServices": retention_entities,
            "consentConfigurationExternalServices": config_entities,
        }


__all__ = ["_ConsentODataClient"]
