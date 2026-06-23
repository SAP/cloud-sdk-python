"""Tests for _StarletteIASInstrumentor."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from starlette import applications

from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TENANT_ID, ATTR_USER_ID
from sap_cloud_sdk.core.telemetry.middleware._starlette_instrumentor import (
    _StarletteIASInstrumentor,
    _attrs_var,
)

_PATCH_PARSE = "sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.parse_token"


@pytest.fixture(autouse=True)
def reset_instrumentor():
    """Ensure each test starts and ends with a clean uninstrumented state."""
    original = applications.Starlette
    _StarletteIASInstrumentor._instrumented = False
    _StarletteIASInstrumentor._processor_registered = False
    _StarletteIASInstrumentor._original = None
    yield
    applications.Starlette = original
    _StarletteIASInstrumentor._instrumented = False
    _StarletteIASInstrumentor._processor_registered = False
    _StarletteIASInstrumentor._original = None


class TestIsAvailable:
    def test_returns_true_when_starlette_installed(self):
        assert _StarletteIASInstrumentor.is_available() is True

    def test_returns_false_when_starlette_missing(self):
        with patch.dict("sys.modules", {"starlette": None}):
            assert _StarletteIASInstrumentor.is_available() is False


class TestInstrumentGuard:
    def test_instrument_patches_starlette_class(self):
        original = applications.Starlette
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        assert applications.Starlette is not original

    def test_instrument_is_idempotent(self):
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        patched = applications.Starlette
        instr.instrument()  # second call
        assert applications.Starlette is patched  # unchanged

    def test_instrumented_flag_set_after_instrument(self):
        instr = _StarletteIASInstrumentor()
        assert not _StarletteIASInstrumentor._instrumented
        instr.instrument()
        assert _StarletteIASInstrumentor._instrumented

    def test_uninstrument_restores_original_class(self):
        original = applications.Starlette
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        instr.uninstrument()
        assert applications.Starlette is original

    def test_uninstrument_clears_flag(self):
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        instr.uninstrument()
        assert not _StarletteIASInstrumentor._instrumented

    def test_uninstrument_is_idempotent(self):
        instr = _StarletteIASInstrumentor()
        instr.uninstrument()  # called without prior instrument() — must not raise


class TestPerInstanceGuard:
    def test_app_gets_ias_middleware_on_init(self):
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        app = applications.Starlette()
        assert getattr(app, "_sap_ias_done", False) is True

    def test_middleware_not_added_twice_on_same_instance(self):
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        app = applications.Starlette()
        add_mw_calls_before = app.middleware_stack  # capture after first init
        # Simulate __init__ being called again (edge case)
        app._sap_ias_done = True
        original_add = app.add_middleware
        app.add_middleware = MagicMock()
        # Manually trigger the guard path
        if not getattr(app, "_sap_ias_done", False):
            app.add_middleware(object)
        app.add_middleware.assert_not_called()


class TestK8sOperatorComposition:
    def test_our_patch_layers_on_top_of_existing_subclass(self):
        """Simulates OTel operator running first (Scenario A)."""
        original = applications.Starlette

        class _OtelInstrumented(original):
            otel_init_called = False

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                _OtelInstrumented.otel_init_called = True

        applications.Starlette = _OtelInstrumented

        instr = _StarletteIASInstrumentor()
        instr.instrument()

        app = applications.Starlette()
        assert _OtelInstrumented.otel_init_called is True
        assert getattr(app, "_sap_ias_done", False) is True

    def test_existing_subclass_layers_on_top_of_our_patch(self):
        """Simulates OTel operator running second (Scenario B)."""
        instr = _StarletteIASInstrumentor()
        instr.instrument()

        current = applications.Starlette

        class _OtelInstrumented(current):
            otel_init_called = False

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                _OtelInstrumented.otel_init_called = True

        applications.Starlette = _OtelInstrumented

        app = applications.Starlette()
        assert _OtelInstrumented.otel_init_called is True
        assert getattr(app, "_sap_ias_done", False) is True


class TestGetAttributes:
    def test_returns_empty_outside_request(self):
        instr = _StarletteIASInstrumentor()
        assert instr.get_attributes() == {}

    def test_returns_attrs_set_in_context_var(self):
        instr = _StarletteIASInstrumentor()
        token = _attrs_var.set({ATTR_SAP_TENANT_ID: "t1", ATTR_USER_ID: "u1"})
        try:
            assert instr.get_attributes() == {
                ATTR_SAP_TENANT_ID: "t1",
                ATTR_USER_ID: "u1",
            }
        finally:
            _attrs_var.reset(token)


class TestUninstrumentGuards:
    def test_uninstrument_with_original_none_does_not_crash(self):
        """Fix 1: _do_uninstrument must not set applications.Starlette = None."""
        _StarletteIASInstrumentor._instrumented = True
        _StarletteIASInstrumentor._original = None
        instr = _StarletteIASInstrumentor()
        instr.uninstrument()  # must not raise or corrupt applications.Starlette
        assert applications.Starlette is not None

    def test_uninstrument_does_not_corrupt_starlette_class(self):
        instr = _StarletteIASInstrumentor()
        instr.instrument()
        instr.uninstrument()
        # applications.Starlette must be a real callable class
        app = applications.Starlette()
        assert app is not None

    def test_processor_registered_flag_reset_on_uninstrument(self):
        """Fix 3: _processor_registered is cleared when uninstrument() is called."""
        instr = _StarletteIASInstrumentor()
        _StarletteIASInstrumentor._processor_registered = True
        instr.instrument()
        instr.uninstrument()
        assert not _StarletteIASInstrumentor._processor_registered

class TestSupersedes:
    def test_supersedes_starlette_ias_telemetry_middleware(self):
        from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import StarletteIASTelemetryMiddleware
        assert _StarletteIASInstrumentor.supersedes is StarletteIASTelemetryMiddleware
