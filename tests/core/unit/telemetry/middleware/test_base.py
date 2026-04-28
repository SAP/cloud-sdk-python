"""Tests for TelemetryMiddleware abstract base class."""

import pytest

from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware


class TestTelemetryMiddlewareAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            TelemetryMiddleware()

    def test_concrete_subclass_with_both_methods_works(self):
        class Concrete(TelemetryMiddleware):
            def register(self):
                pass

            def get_attributes(self):
                return {"k": "v"}

        obj = Concrete()
        obj.register()
        assert obj.get_attributes() == {"k": "v"}

    def test_missing_register_raises(self):
        class Incomplete(TelemetryMiddleware):
            def get_attributes(self):
                return {}

        with pytest.raises(TypeError):
            Incomplete()

    def test_missing_get_attributes_raises(self):
        class Incomplete(TelemetryMiddleware):
            def register(self):
                pass

        with pytest.raises(TypeError):
            Incomplete()
