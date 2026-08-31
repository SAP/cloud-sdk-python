from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor

_registry: list[LibraryInstrumentor] = []
_instrumented: list[str] = []


def register(instrumentor: LibraryInstrumentor) -> None:
    """Add an instrumentor to the registry.

    Call this at module level in each concrete instrumentor file, or from
    third-party code that wants to plug in additional library coverage.
    """
    _registry.append(instrumentor)


def get_registry() -> list[LibraryInstrumentor]:
    return list(_registry)


def record_instrumented(name: str) -> None:
    """Record a library as successfully instrumented. Called by LibraryInstrumentor."""
    _instrumented.append(name)


def get_instrumented_libraries() -> list[str]:
    """Return the names of libraries successfully instrumented via auto_instrument().

    Each entry corresponds to a library that was installed and patched with OTel
    (e.g. ``"httpx"``, ``"sqlalchemy"``). Libraries that were skipped because they
    are not installed do not appear in this list. Returns an empty list if
    auto_instrument() has not been called yet.
    """
    return list(_instrumented)
