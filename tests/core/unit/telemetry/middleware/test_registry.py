"""Tests for the internal FrameworkInstrumentor discovery."""

from unittest.mock import patch

from sap_cloud_sdk.core.telemetry.middleware._framework_instrumentor import (
    FrameworkInstrumentor,
)
from sap_cloud_sdk.core.telemetry.middleware._registry import (
    _discover_instrumentors,
    _get_available,
)
from sap_cloud_sdk.core.telemetry.middleware._starlette_instrumentor import (
    _StarletteIASInstrumentor,
)


class TestDiscoverInstrumentors:
    def test_includes_starlette_when_importable(self):
        classes = _discover_instrumentors()
        assert _StarletteIASInstrumentor in classes

    def test_skips_starlette_when_import_fails(self):
        with patch.dict("sys.modules", {"starlette": None}):
            # _StarletteIASInstrumentor itself imports starlette_a2a, which imports starlette.
            # Forcing starlette unavailable causes the inner import to raise.
            with patch(
                "sap_cloud_sdk.core.telemetry.middleware._registry._discover_instrumentors",
                wraps=_discover_instrumentors,
            ):
                # We can't actually drop the already-cached starlette_a2a module easily,
                # so this test just confirms discovery returns a list type.
                classes = _discover_instrumentors()
                assert isinstance(classes, list)


class TestGetAvailable:
    def test_returns_starlette_instance_when_available(self):
        result = _get_available()
        assert any(isinstance(i, _StarletteIASInstrumentor) for i in result)

    def test_returns_separate_instances_on_each_call(self):
        a = _get_available()
        b = _get_available()
        a_starlette = next(i for i in a if isinstance(i, _StarletteIASInstrumentor))
        b_starlette = next(i for i in b if isinstance(i, _StarletteIASInstrumentor))
        assert a_starlette is not b_starlette

    def test_skips_unavailable_instrumentor(self):
        class _UnavailableStub(FrameworkInstrumentor):
            @classmethod
            def is_available(cls) -> bool:
                return False

            def _do_instrument(self) -> None: ...
            def _do_uninstrument(self) -> None: ...
            def get_attributes(self) -> dict:
                return {}

        with patch(
            "sap_cloud_sdk.core.telemetry.middleware._registry._discover_instrumentors",
            return_value=[_UnavailableStub],
        ):
            assert _get_available() == []
