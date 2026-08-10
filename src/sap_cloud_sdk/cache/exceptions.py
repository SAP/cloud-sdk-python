"""Exception classes for the cache module."""


class CacheError(Exception):
    """Base exception for all cache module errors."""


class BackendError(CacheError):
    """Raised when a custom cache backend raises an unexpected exception."""
