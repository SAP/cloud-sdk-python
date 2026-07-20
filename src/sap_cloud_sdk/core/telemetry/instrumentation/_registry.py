from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor

_registry: list[LibraryInstrumentor] = []


def register(instrumentor: LibraryInstrumentor) -> None:
    """Add an instrumentor to the registry.

    Call this at module level in each concrete instrumentor file, or from
    third-party code that wants to plug in additional library coverage.
    """
    _registry.append(instrumentor)


def get_registry() -> list[LibraryInstrumentor]:
    return list(_registry)
