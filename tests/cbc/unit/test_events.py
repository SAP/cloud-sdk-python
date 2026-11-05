"""Unit tests for CBCEventHandler and CBC event models."""

from __future__ import annotations

import json

import pytest

from sap_cloud_sdk.cbc._events import CBCEventHandler
from sap_cloud_sdk.cbc._models import (
    ConsumptionVersionEvent,
    FeatureActivationData,
    FeatureActivationEvent,
)
from sap_cloud_sdk.cbc.exceptions import CBCEventError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _structured_headers() -> dict[str, str]:
    return {"Content-Type": "application/cloudevents+json"}


def _binary_headers(event_type: str) -> dict[str, str]:
    return {
        "ce-specversion": "1.0",
        "ce-id": "0001",
        "ce-source": "/test",
        "ce-type": event_type,
        "Content-Type": "application/json",
    }


def _cv_body(
    *,
    consumption_version_id: str = "cv-1",
    status: str = "FINETUNE",
    app_tenant_id: str = "app-tenant-123",
    cbc_tenant_id: str = "cbc-tenant-123",
    include_context: bool = True,
) -> bytes:
    data: dict = {
        "consumption": {
            "consumptionVersionId": consumption_version_id,
            "status": status,
        }
    }
    if include_context:
        data["context"] = {"cbcTenantId": cbc_tenant_id, "appTenantId": app_tenant_id}
    return json.dumps(
        {
            "specversion": "1.0",
            "id": "0001",
            "source": "/eu10/sap.alpha/cbc-tenant-123",
            "type": "cbc.notification.consumptionversion.updated",
            "datacontenttype": "application/json",
            "data": data,
        }
    ).encode()


def _fa_body(
    *,
    features: list[dict] | None = None,
    app_tenant_id: str = "app-tenant-123",
    cbc_tenant_id: str = "cbc-tenant-123",
    include_context: bool = True,
) -> bytes:
    data: dict = {
        "features": features
        if features is not None
        else [
            {"featureId": "ai_assisted_supplier_bid_analysis", "enabled": True},
            {"featureId": "ai_assisted_tco_analysis", "enabled": False},
        ]
    }
    if include_context:
        data["context"] = {"cbcTenantId": cbc_tenant_id, "appTenantId": app_tenant_id}
    return json.dumps(
        {
            "specversion": "1.0",
            "id": "0001",
            "source": "/test",
            "type": "cbc.notification.feature.activation.v1",
            "data": data,
        }
    ).encode()


# ---------------------------------------------------------------------------
# TestHandleRequest — consumption version events
# ---------------------------------------------------------------------------


class TestHandleRequestConsumptionVersion:
    def test_created_event_dispatches_to_cv_callback(self):
        handler = CBCEventHandler()
        received: list[ConsumptionVersionEvent] = []
        handler.on_consumption_version_event(received.append)

        body = json.dumps(
            {
                "specversion": "1.0",
                "id": "0001",
                "source": "/test",
                "type": "cbc.notification.consumptionversion.created",
                "data": {
                    "consumption": {"consumptionVersionId": "cv-1", "status": "INITIALDEPLOY"},
                    "context": {"cbcTenantId": "cbc-t1", "appTenantId": "app-t1"},
                },
            }
        ).encode()
        handler.handle_request(_structured_headers(), body)

        assert len(received) == 1
        assert received[0].app_tenant_id == "app-t1"
        assert received[0].consumption_version_id == "cv-1"

    def test_updated_event_dispatches_to_cv_callback(self):
        handler = CBCEventHandler()
        received: list[ConsumptionVersionEvent] = []
        handler.on_consumption_version_event(received.append)

        handler.handle_request(_structured_headers(), _cv_body())

        assert len(received) == 1
        assert received[0].app_tenant_id == "app-tenant-123"
        assert received[0].consumption_version_id == "cv-1"

    def test_cv_event_without_callback_does_not_raise(self):
        handler = CBCEventHandler()
        handler.handle_request(_structured_headers(), _cv_body())

    def test_cv_event_missing_context_raises_cbc_event_error(self):
        handler = CBCEventHandler()
        handler.on_consumption_version_event(lambda e: None)
        with pytest.raises(CBCEventError, match="context"):
            handler.handle_request(_structured_headers(), _cv_body(include_context=False))

    def test_cv_event_missing_consumption_raises_cbc_event_error(self):
        handler = CBCEventHandler()
        handler.on_consumption_version_event(lambda e: None)
        body = json.dumps(
            {
                "specversion": "1.0",
                "id": "0001",
                "source": "/test",
                "type": "cbc.notification.consumptionversion.updated",
                "data": {
                    "context": {"cbcTenantId": "cbc-t1", "appTenantId": "app-t1"},
                },
            }
        ).encode()
        with pytest.raises(CBCEventError, match="consumption"):
            handler.handle_request(_structured_headers(), body)

    def test_cv_event_empty_consumption_version_id_raises_cbc_event_error(self):
        handler = CBCEventHandler()
        handler.on_consumption_version_event(lambda e: None)
        with pytest.raises(CBCEventError):
            handler.handle_request(_structured_headers(), _cv_body(consumption_version_id=""))

    def test_cv_event_binary_mode_dispatches_correctly(self):
        handler = CBCEventHandler()
        received: list[ConsumptionVersionEvent] = []
        handler.on_consumption_version_event(received.append)

        body = json.dumps(
            {
                "consumption": {"consumptionVersionId": "cv-binary", "status": "UPGRADE"},
                "context": {"cbcTenantId": "cbc-t1", "appTenantId": "app-t1"},
            }
        ).encode()
        handler.handle_request(
            _binary_headers("cbc.notification.consumptionversion.updated"), body
        )

        assert len(received) == 1
        assert received[0].consumption_version_id == "cv-binary"


# ---------------------------------------------------------------------------
# TestHandleRequest — feature activation events
# ---------------------------------------------------------------------------


class TestHandleRequestFeatureActivation:
    def test_fa_event_dispatches_to_fa_callback(self):
        handler = CBCEventHandler()
        received: list[FeatureActivationEvent] = []
        handler.on_feature_activation_event(received.append)

        handler.handle_request(_structured_headers(), _fa_body())

        assert len(received) == 1
        assert received[0].app_tenant_id == "app-tenant-123"
        assert len(received[0].features) == 2

    def test_fa_event_parses_feature_ids_and_enabled_flags(self):
        handler = CBCEventHandler()
        received: list[FeatureActivationEvent] = []
        handler.on_feature_activation_event(received.append)

        handler.handle_request(_structured_headers(), _fa_body())

        features = received[0].features
        assert features[0].feature_id == "ai_assisted_supplier_bid_analysis"
        assert features[0].enabled is True
        assert features[1].feature_id == "ai_assisted_tco_analysis"
        assert features[1].enabled is False

    def test_fa_event_without_callback_does_not_raise(self):
        handler = CBCEventHandler()
        handler.handle_request(_structured_headers(), _fa_body())

    def test_fa_event_missing_context_raises_cbc_event_error(self):
        handler = CBCEventHandler()
        handler.on_feature_activation_event(lambda e: None)
        with pytest.raises(CBCEventError, match="context"):
            handler.handle_request(_structured_headers(), _fa_body(include_context=False))

    def test_fa_event_empty_features_raises_cbc_event_error(self):
        handler = CBCEventHandler()
        handler.on_feature_activation_event(lambda e: None)
        with pytest.raises(CBCEventError, match="features"):
            handler.handle_request(_structured_headers(), _fa_body(features=[]))

    def test_fa_event_binary_mode_dispatches_correctly(self):
        handler = CBCEventHandler()
        received: list[FeatureActivationEvent] = []
        handler.on_feature_activation_event(received.append)

        body = json.dumps(
            {
                "features": [{"featureId": "ai_assisted_lead_routing", "enabled": True}],
                "context": {"cbcTenantId": "cbc-t1", "appTenantId": "app-t1"},
            }
        ).encode()
        handler.handle_request(_binary_headers("cbc.notification.feature.activation.v1"), body)

        assert len(received) == 1
        assert received[0].features[0].feature_id == "ai_assisted_lead_routing"


# ---------------------------------------------------------------------------
# TestHandleRequest — unknown and malformed events
# ---------------------------------------------------------------------------


class TestHandleRequestUnknownAndMalformed:
    def test_unknown_event_type_is_silently_ignored(self):
        handler = CBCEventHandler()
        handler.on_consumption_version_event(lambda e: (_ for _ in ()).throw(AssertionError()))
        handler.on_feature_activation_event(lambda e: (_ for _ in ()).throw(AssertionError()))

        body = json.dumps(
            {
                "specversion": "1.0",
                "id": "0001",
                "source": "/test",
                "type": "cbc.notification.some.unknown.event",
                "data": {},
            }
        ).encode()
        handler.handle_request(_structured_headers(), body)

    def test_malformed_body_raises_cbc_event_error(self):
        handler = CBCEventHandler()
        with pytest.raises(CBCEventError):
            handler.handle_request(_structured_headers(), b"not json at all")

    def test_body_as_str_is_accepted(self):
        handler = CBCEventHandler()
        received: list[ConsumptionVersionEvent] = []
        handler.on_consumption_version_event(received.append)

        handler.handle_request(_structured_headers(), _cv_body().decode())

        assert len(received) == 1


# ---------------------------------------------------------------------------
# TestEventModels
# ---------------------------------------------------------------------------


class TestConsumptionVersionEvent:
    def test_repr_contains_key_fields(self):
        e = ConsumptionVersionEvent(app_tenant_id="app-t1", consumption_version_id="cv-1")
        assert "app-t1" in repr(e)
        assert "cv-1" in repr(e)


class TestFeatureActivationData:
    def test_enabled_returns_correct_value(self):
        assert FeatureActivationData("f1", True).enabled is True
        assert FeatureActivationData("f2", False).enabled is False

    def test_repr_contains_key_fields(self):
        d = FeatureActivationData("ai_assisted_lead_routing", True)
        assert "ai_assisted_lead_routing" in repr(d)
        assert "True" in repr(d)


class TestFeatureActivationEvent:
    def test_repr_contains_key_fields(self):
        e = FeatureActivationEvent(
            app_tenant_id="app-t1",
            features=[FeatureActivationData("f1", True)],
        )
        assert "app-t1" in repr(e)
