"""Exception classes for the object store module."""


class ObjectStoreError(Exception):
    """Base exception for all object store errors."""
    pass


class ClientCreationError(ObjectStoreError):
    """Raised when object store client creation fails."""
    pass


class ObjectOperationError(ObjectStoreError):
    """Raised when an object operation fails."""
    pass


class ObjectNotFoundError(ObjectOperationError):
    """Raised when a requested object is not found."""
    pass


class ListObjectsError(ObjectOperationError):
    """Raised when listing objects fails."""
    pass
