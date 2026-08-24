"""Shared validation error message constants for object store backends."""

EMPTY_NAME_ERROR = "name must be a non-empty string"
EMPTY_CONTENT_TYPE_ERROR = "content_type must be a non-empty string"
EMPTY_FILE_PATH_ERROR = "file_path must be a non-empty string"
INVALID_DATA_TYPE_ERROR = "data must be bytes"
INVALID_STREAM_ERROR = "stream must be a readable binary stream"
NEGATIVE_SIZE_ERROR = "size must be non-negative"
INVALID_PREFIX_TYPE_ERROR = "prefix must be a string"
