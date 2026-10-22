"""CBC CloudEvent parsing and dispatch."""

from __future__ import annotations

from collections.abc import Callable

from cloudevents.core.base import BaseCloudEvent
from cloudevents.core.bindings.http import HTTPMessage, from_http_event
from pydantic import ValidationError

from sap_cloud_sdk.cbc._models import (
    ConsumptionVersionEvent,
    FeatureActivationData,
    FeatureActivationEvent,
    _ConsumptionVersionPayload,
    _FeatureActivationItem,
    _TenantContext,
)
from sap_cloud_sdk.cbc.exceptions import CBCEventError
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

_CV_CREATED = "cbc.notification.consumptionversion.created"
_CV_UPDATED = "cbc.notification.consumptionversion.updated"
_FA_ACTIVATION = "cbc.notification.feature.activation.v1"


def _require(data: dict, key: str, event_type: str) -> object:
    """Return ``data[key]``, raising ``CBCEventError`` if the key is absent."""
    value = data.get(key)
    if value is None:
        raise CBCEventError(
            f"CBC event '{event_type}' is missing required field '{key}'"
        )
    return value


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

ConsumptionVersionCallback = Callable[[ConsumptionVersionEvent], None]
FeatureActivationCallback = Callable[[FeatureActivationEvent], None]


class CBCEventHandler:
    """Parses and dispatches incoming CBC CloudEvents to registered callbacks.

    Register one callback per event category, then call :meth:`handle_request`
    from your webhook endpoint for every incoming POST::

        handler = cbc.CBCEventHandler()

        def on_cv(event: cbc.ConsumptionVersionEvent) -> None:
            ...

        def on_fa(event: cbc.FeatureActivationEvent) -> None:
            for f in event.features:
                update_cache(f.feature_id, f.enabled)

        handler.on_consumption_version_event(on_cv)
        handler.on_feature_activation_event(on_fa)

        # In your webhook route:
        handler.handle_request(request.headers, request.body)

    Raises:
        CBCEventError: If the incoming request cannot be parsed as a valid
            CloudEvent, or if the event data is structurally invalid for a
            known event type.  Unknown event types are silently ignored.
    """

    def __init__(self) -> None:
        self._cv_callback: ConsumptionVersionCallback | None = None
        self._fa_callback: FeatureActivationCallback | None = None

    @staticmethod
    def _parse_cloud_event(
        headers: dict[str, str], body: str | bytes
    ) -> BaseCloudEvent:
        """Parse raw HTTP headers and body into a :class:`BaseCloudEvent`.

        Raises:
            CBCEventError: If the request cannot be parsed as a valid CloudEvent.
        """
        raw = body.encode() if isinstance(body, str) else body
        try:
            return from_http_event(HTTPMessage(headers, raw))
        except Exception as exc:
            raise CBCEventError(
                f"Failed to parse incoming request as a CloudEvent: {exc}"
            ) from exc

    @staticmethod
    def _extract_app_tenant_id(raw_data: dict, event_type: str) -> str:
        """Extract the app tenant id from the event context block.

        Raises:
            CBCEventError: If the context field is absent or structurally invalid.
        """
        try:
            context = _TenantContext.model_validate(
                _require(raw_data, "context", event_type)
            )
        except ValidationError as exc:
            raise CBCEventError(
                f"CBC event '{event_type}' data is invalid: {exc}"
            ) from exc
        return context.app_tenant_id

    @staticmethod
    def _parse_consumption_version_event(ce: BaseCloudEvent) -> ConsumptionVersionEvent:
        """Parse a consumption-version CloudEvent into a :class:`ConsumptionVersionEvent`.

        Raises:
            CBCEventError: If the data block is missing or structurally invalid.
        """
        event_type = ce.get_type()
        raw_data = ce.get_data()
        if not isinstance(raw_data, dict):
            raise CBCEventError(f"CBC event '{event_type}' has no parseable data block")

        context = CBCEventHandler._extract_app_tenant_id(raw_data, event_type)
        try:
            consumption = _ConsumptionVersionPayload.model_validate(
                _require(raw_data, "consumption", event_type)
            )
        except ValidationError as exc:
            raise CBCEventError(
                f"CBC event '{event_type}' data is invalid: {exc}"
            ) from exc

        return ConsumptionVersionEvent(
            app_tenant_id=context,
            consumption_version_id=consumption.consumption_version_id,
        )

    @staticmethod
    def _parse_feature_activation_event(ce: BaseCloudEvent) -> FeatureActivationEvent:
        """Parse a feature-activation CloudEvent into a :class:`FeatureActivationEvent`.

        Raises:
            CBCEventError: If the data block is missing, the context is absent, or
                the features list is missing or empty.
        """
        event_type = ce.get_type()
        raw_data = ce.get_data()
        if not isinstance(raw_data, dict):
            raise CBCEventError(f"CBC event '{event_type}' has no parseable data block")

        app_tenant_id = CBCEventHandler._extract_app_tenant_id(raw_data, event_type)

        raw_features = raw_data.get("features")
        if not raw_features:
            raise CBCEventError(f"CBC event '{event_type}' has no features")

        try:
            items = [_FeatureActivationItem.model_validate(f) for f in raw_features]
        except ValidationError as exc:
            raise CBCEventError(
                f"CBC event '{event_type}' features are invalid: {exc}"
            ) from exc

        features = [
            FeatureActivationData(feature_id=f.feature_id, enabled=f.enabled)
            for f in items
        ]
        return FeatureActivationEvent(app_tenant_id=app_tenant_id, features=features)

    def on_consumption_version_event(
        self, callback: ConsumptionVersionCallback
    ) -> None:
        """Register a callback for consumption-version events (created and updated).

        Args:
            callback: Callable invoked with a :class:`ConsumptionVersionEvent` for
                each ``consumptionversion.created`` or ``consumptionversion.updated``
                event received.  Replaces any previously registered callback.
        """
        self._cv_callback = callback

    def on_feature_activation_event(self, callback: FeatureActivationCallback) -> None:
        """Register a callback for feature-activation events.

        Args:
            callback: Callable invoked with a :class:`FeatureActivationEvent` for
                each ``feature.activation.v1`` event received.  Replaces any
                previously registered callback.
        """
        self._fa_callback = callback

    @record_metrics(Module.CBC, Operation.CBC_HANDLE_EVENT)
    def handle_request(
        self,
        headers: dict[str, str],
        body: str | bytes,
    ) -> None:
        """Parse an incoming CBC CloudEvent and dispatch it to registered callbacks.

        Args:
            headers: HTTP request headers (needed for binary-mode CloudEvents).
            body: Raw HTTP request body.

        Raises:
            CBCEventError: If the request is not a valid CloudEvent, or if the
                event data is structurally invalid for a known CBC event type.
        """
        ce = self._parse_cloud_event(headers, body)
        event_type: str = ce.get_type()

        if event_type in (_CV_CREATED, _CV_UPDATED):
            if self._cv_callback is None:
                return
            self._cv_callback(self._parse_consumption_version_event(ce))

        elif event_type == _FA_ACTIVATION:
            if self._fa_callback is None:
                return
            self._fa_callback(self._parse_feature_activation_event(ce))

        # unknown event type: silently ignored
