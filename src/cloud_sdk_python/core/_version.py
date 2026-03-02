"""Utility to get SDK version from package metadata."""

from importlib.metadata import version, PackageNotFoundError


def get_version() -> str:
    """Get the SDK version from package metadata.
    
    This function retrieves the version from the installed package metadata
    as defined in pyproject.toml.
    
    Returns:
        Version string (e.g., "1.2.1") from the installed package,
        or "unknown" if the package is not installed or metadata is unavailable.
    """
    try:
        return version("cloud-sdk-python")
    except PackageNotFoundError:
        # Package not installed (e.g., during development without installation)
        return "unknown"
    except Exception:
        # Any other error retrieving version
        return "unknown"
