"""Tests for the FrameworkInstrumentor registry."""

import pytest

from sap_cloud_sdk.core.telemetry.middleware.base import FrameworkInstrumentor
from sap_cloud_sdk.core.telemetry.middleware.registry import (
    _registry,
    get_available,
    register,
)


def _make_instrumentor(available: bool) -> type[FrameworkInstrumentor]:
    class _Stub(FrameworkInstrumentor):
        _instrumented = False
        _processor_registered = False

        @classmethod
        def is_available(cls) -> bool:
            return available

        def _do_instrument(self) -> None:
            pass

        def _do_uninstrument(self) -> None:
            pass

        def get_attributes(self) -> dict:
            return {}

    return _Stub


@pytest.fixture()
def registered_cls():
    """Register a stub class and guarantee cleanup even if the test fails."""
    registered = []

    def _register(available: bool = True) -> type[FrameworkInstrumentor]:
        cls = _make_instrumentor(available=available)
        register(cls)
        registered.append(cls)
        return cls

    yield _register

    for cls in registered:
        if cls in _registry:
            _registry.remove(cls)


class TestRegister:
    def test_register_adds_to_registry(self, registered_cls):
        before = len(_registry) - 1  # registered_cls already added one
        cls = registered_cls()
        assert cls in _registry

    def test_register_returns_class_unchanged(self, registered_cls):
        cls = _make_instrumentor(available=True)
        result = register(cls)
        assert result is cls
        _registry.remove(cls)

    def test_register_usable_as_decorator(self, registered_cls):
        base = _make_instrumentor(available=True)

        @register
        class _Decorated(base):
            pass

        assert _Decorated in _registry
        _registry.remove(_Decorated)


class TestGetAvailable:
    def test_returns_instance_of_available_instrumentor(self, registered_cls):
        cls = registered_cls(available=True)
        result = get_available()
        assert any(isinstance(i, cls) for i in result)

    def test_skips_unavailable_instrumentor(self, registered_cls):
        cls = registered_cls(available=False)
        result = get_available()
        assert not any(isinstance(i, cls) for i in result)

    def test_returns_separate_instances_on_each_call(self, registered_cls):
        cls = registered_cls(available=True)
        a = [i for i in get_available() if isinstance(i, cls)]
        b = [i for i in get_available() if isinstance(i, cls)]
        assert a[0] is not b[0]
