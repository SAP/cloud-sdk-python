"""Argument-validation helpers shared by object store backends."""

from typing import BinaryIO


def validate_object_name(name: str) -> None:
    """Require a non-empty object name/key."""
    if not name:
        raise ValueError("name must be a non-empty string")


def validate_prefix(prefix: str) -> None:
    """Require the list prefix to be a string (empty is allowed)."""
    if not isinstance(prefix, str):
        raise ValueError("prefix must be a string")


def validate_put_from_bytes(name: str, data: bytes, content_type: str) -> None:
    """Validate arguments for an upload from an in-memory byte string."""
    validate_object_name(name)
    if not isinstance(data, bytes):
        raise ValueError("data must be bytes")
    if not content_type:
        raise ValueError("content_type must be a non-empty string")


def validate_put_object(
    name: str, stream: BinaryIO, size: int, content_type: str
) -> None:
    """Validate arguments for an upload from a binary stream."""
    validate_object_name(name)
    if not hasattr(stream, "read"):
        raise ValueError("stream must be a readable binary stream")
    if size < 0:
        raise ValueError("size must be non-negative")
    if not content_type:
        raise ValueError("content_type must be a non-empty string")


def validate_put_from_file(name: str, file_path: str, content_type: str) -> None:
    """Validate arguments for an upload from a local file path."""
    validate_object_name(name)
    if not file_path:
        raise ValueError("file_path must be a non-empty string")
    if not content_type:
        raise ValueError("content_type must be a non-empty string")
