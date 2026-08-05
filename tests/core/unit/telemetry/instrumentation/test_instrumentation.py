import importlib
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import (
    _registry,
    get_registry,
    register,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ConcreteInstrumentor(LibraryInstrumentor):
    library_name = "sys"  # always installed

    def __init__(self):
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented

    def _instrument(self, **kwargs) -> None:
        self._instrumented = True

    def _uninstrument(self) -> None:
        self._instrumented = False


class _MissingLibraryInstrumentor(LibraryInstrumentor):
    library_name = "_nonexistent_library_xyz"

    def __init__(self):
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented

    def _instrument(self, **kwargs) -> None:
        self._instrumented = True

    def _uninstrument(self) -> None:
        self._instrumented = False


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class TestLibraryInstrumentor:
    def test_instrument_calls_inner_when_library_present(self):
        inst = _ConcreteInstrumentor()
        inst.instrument()
        assert inst.is_instrumented()

    def test_instrument_is_idempotent(self):
        inst = _ConcreteInstrumentor()
        inst.instrument()
        inst._instrument = MagicMock()
        inst.instrument()
        inst._instrument.assert_not_called()

    def test_instrument_skips_when_library_missing(self):
        inst = _MissingLibraryInstrumentor()
        inst.instrument()
        assert not inst.is_instrumented()

    def test_uninstrument_calls_inner_when_instrumented(self):
        inst = _ConcreteInstrumentor()
        inst.instrument()
        inst.uninstrument()
        assert not inst.is_instrumented()

    def test_uninstrument_is_noop_when_not_instrumented(self):
        inst = _ConcreteInstrumentor()
        inst._uninstrument = MagicMock()
        inst.uninstrument()
        inst._uninstrument.assert_not_called()

    def test_is_library_installed_true_for_stdlib(self):
        inst = _ConcreteInstrumentor()
        assert inst._is_library_installed()

    def test_is_library_installed_false_for_missing(self):
        inst = _MissingLibraryInstrumentor()
        assert not inst._is_library_installed()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_register_appends_to_registry(self):
        before = len(_registry)
        inst = _ConcreteInstrumentor()
        register(inst)
        assert len(_registry) == before + 1
        _registry.remove(inst)

    def test_get_registry_returns_copy(self):
        snapshot = get_registry()
        snapshot.clear()
        assert len(get_registry()) > 0  # original unchanged

    def test_builtin_instrumentors_are_registered(self):
        names = {type(i).__name__ for i in get_registry()}
        assert "HttpxInstrumentor" in names
        assert "RequestsInstrumentorWrapper" in names
        assert "GrpcInstrumentorWrapper" in names
        assert "LoggingInstrumentorWrapper" in names


# ---------------------------------------------------------------------------
# Concrete instrumentors — instrument / uninstrument / is_instrumented
# ---------------------------------------------------------------------------

def _make_otel_instrumentor_mock(is_instrumented: bool = False) -> MagicMock:
    m = MagicMock()
    m.is_instrumented_by_opentelemetry = is_instrumented
    return m


class TestHttpxInstrumentor:
    def test_instrument_delegates_to_otel(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import httpx as httpx_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(httpx_mod, "_instrumentor", mock):
            httpx_mod.HttpxInstrumentor().instrument()
        mock.instrument.assert_called_once()

    def test_is_instrumented_reflects_otel_state(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import httpx as httpx_mod
        mock = _make_otel_instrumentor_mock(is_instrumented=True)
        with patch.object(httpx_mod, "_instrumentor", mock):
            assert httpx_mod.HttpxInstrumentor().is_instrumented()

    def test_uninstrument_delegates_to_otel(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import httpx as httpx_mod
        mock = _make_otel_instrumentor_mock(is_instrumented=True)
        with patch.object(httpx_mod, "_instrumentor", mock):
            httpx_mod.HttpxInstrumentor().uninstrument()
        mock.uninstrument.assert_called_once()


class TestRequestsInstrumentor:
    def test_instrument_delegates_to_otel(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import requests as req_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(req_mod, "_instrumentor", mock):
            req_mod.RequestsInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once()

    def test_uninstrument_delegates_to_otel(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import requests as req_mod
        mock = _make_otel_instrumentor_mock(is_instrumented=True)
        with patch.object(req_mod, "_instrumentor", mock):
            req_mod.RequestsInstrumentorWrapper().uninstrument()
        mock.uninstrument.assert_called_once()


class TestLoggingInstrumentor:
    def test_instrument_delegates_to_otel(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import logging as logging_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(logging_mod, "_instrumentor", mock):
            logging_mod.LoggingInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once_with(set_logging_format=True)


class TestGrpcInstrumentor:
    def test_instrument_delegates_to_otel(self):
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import grpc as grpc_mod
        client_mock = _make_otel_instrumentor_mock()
        server_mock = _make_otel_instrumentor_mock()
        with (
            patch.object(grpc_mod, "_client_instrumentor", client_mock),
            patch.object(grpc_mod, "_server_instrumentor", server_mock),
        ):
            grpc_mod.GrpcInstrumentorWrapper().instrument()
        client_mock.instrument.assert_called_once()
        server_mock.instrument.assert_called_once()


class TestStarletteInstrumentor:
    def test_instrument_delegates_to_otel(self):
        pytest.importorskip("starlette")
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import starlette as starlette_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(starlette_mod, "_instrumentor", mock):
            starlette_mod.StarletteInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once()


class TestFastAPIInstrumentor:
    def test_instrument_delegates_to_otel(self):
        pytest.importorskip("fastapi")
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import fastapi as fastapi_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(fastapi_mod, "_instrumentor", mock):
            fastapi_mod.FastAPIInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once()


class TestAiohttpInstrumentor:
    def test_instrument_delegates_to_otel(self):
        pytest.importorskip("aiohttp")
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import aiohttp as aiohttp_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(aiohttp_mod, "_instrumentor", mock):
            aiohttp_mod.AiohttpInstrumentor().instrument()
        mock.instrument.assert_called_once()


class TestSQLAlchemyInstrumentor:
    def test_instrument_delegates_to_otel(self):
        pytest.importorskip("sqlalchemy")
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import sqlalchemy as sqlalchemy_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(sqlalchemy_mod, "_instrumentor", mock):
            sqlalchemy_mod.SQLAlchemyInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once()

class TestDjangoInstrumentor:
    def test_instrument_delegates_to_otel(self):
        pytest.importorskip("django")
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import django as django_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(django_mod, "_instrumentor", mock):
            django_mod.DjangoInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once()


class TestFlaskInstrumentor:
    def test_instrument_delegates_to_otel(self):
        pytest.importorskip("flask")
        from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import flask as flask_mod
        mock = _make_otel_instrumentor_mock()
        with patch.object(flask_mod, "_instrumentor", mock):
            flask_mod.FlaskInstrumentorWrapper().instrument()
        mock.instrument.assert_called_once()


# ---------------------------------------------------------------------------
# auto_instrument integration
# ---------------------------------------------------------------------------

class TestAutoInstrumentCallsRegistry:
    def test_instrument_libraries_calls_all_registered(self):
        from sap_cloud_sdk.core.telemetry.auto_instrument import _instrument_libraries
        from sap_cloud_sdk.core.telemetry.instrumentation import _registry as registry_mod

        mock_inst = MagicMock(spec=LibraryInstrumentor)
        with patch.object(registry_mod, "_registry", [mock_inst]):
            _instrument_libraries()
        mock_inst.instrument.assert_called_once()
