from enum import StrEnum

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor


class Library(StrEnum):
    """Known libraries that can be instrumented via :func:`~sap_cloud_sdk.core.telemetry.auto_instrument`."""

    AIOHTTP = "aiohttp"
    DJANGO = "django"
    FASTAPI = "fastapi"
    FLASK = "flask"
    GRPC = "grpc"
    HTTPX = "httpx"
    LOGGING = "logging"
    REQUESTS = "requests"
    SQLALCHEMY = "sqlalchemy"
    STARLETTE = "starlette"


_registry: list[LibraryInstrumentor] = []
_instrumented: list[Library] = []


def register(instrumentor: LibraryInstrumentor) -> None:
    """Add an instrumentor to the registry.

    Call this at module level in each concrete instrumentor file, or from
    third-party code that wants to plug in additional library coverage.
    """
    _registry.append(instrumentor)


def get_registry() -> list[LibraryInstrumentor]:
    return list(_registry)


def record_instrumented(name: Library) -> None:
    """Record a library as successfully instrumented. Called by LibraryInstrumentor."""
    if name not in _instrumented:
        _instrumented.append(name)


def get_instrumented_libraries() -> list[Library]:
    """Return the libraries successfully instrumented via auto_instrument().

    Each entry corresponds to a library that was installed and patched with OTel
    (e.g. :attr:`Library.HTTPX`, :attr:`Library.SQLALCHEMY`). Libraries that were
    skipped because they are not installed do not appear in this list. Returns an
    empty list if auto_instrument() has not been called yet.
    """
    return list(_instrumented)
