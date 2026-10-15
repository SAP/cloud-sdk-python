"""Unit tests for argument validators (``object_storage._validation``)."""

import io

import pytest

from sap_cloud_sdk.object_storage._validation import (
    validate_object_name,
    validate_prefix,
    validate_put_from_bytes,
    validate_put_from_file,
    validate_put_object,
)


class TestValidateObjectName:
    def test_non_empty_name_passes(self):
        validate_object_name("key")

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            validate_object_name("")


class TestValidatePrefix:
    def test_empty_string_prefix_is_allowed(self):
        validate_prefix("")

    def test_non_string_prefix_raises(self):
        with pytest.raises(ValueError, match="prefix must be a string"):
            validate_prefix(123)  # ty: ignore[invalid-argument-type]


class TestValidatePutFromBytes:
    def test_valid_arguments_pass(self):
        validate_put_from_bytes("k", b"data", "text/plain")

    def test_non_bytes_data_raises(self):
        with pytest.raises(ValueError, match="data must be bytes"):
            validate_put_from_bytes("k", "not-bytes", "text/plain")  # ty: ignore[invalid-argument-type]

    def test_empty_content_type_raises(self):
        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            validate_put_from_bytes("k", b"data", "")


class TestValidatePutObject:
    def test_valid_arguments_pass(self):
        validate_put_object("k", io.BytesIO(b"x"), 1, "text/plain")

    def test_stream_without_read_raises(self):
        with pytest.raises(ValueError, match="stream must be a readable binary stream"):
            validate_put_object("k", object(), 1, "text/plain")  # ty: ignore[invalid-argument-type]

    def test_negative_size_raises(self):
        with pytest.raises(ValueError, match="size must be non-negative"):
            validate_put_object("k", io.BytesIO(b"x"), -1, "text/plain")

    def test_empty_content_type_raises(self):
        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            validate_put_object("k", io.BytesIO(b"x"), 1, "")


class TestValidatePutFromFile:
    def test_valid_arguments_pass(self):
        validate_put_from_file("k", "/tmp/x.txt", "text/plain")

    def test_empty_file_path_raises(self):
        with pytest.raises(ValueError, match="file_path must be a non-empty string"):
            validate_put_from_file("k", "", "text/plain")

    def test_empty_content_type_raises(self):
        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            validate_put_from_file("k", "/tmp/x.txt", "")
