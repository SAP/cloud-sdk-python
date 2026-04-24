"""Unit tests for the Temporal exceptions module."""

import pytest

from sap_cloud_sdk.temporal.exceptions import (
    ClientCreationError,
    ConfigurationError,
    SpiffeError,
    TemporalError,
    WorkerCreationError,
)


def test_temporal_error_is_base():
    with pytest.raises(TemporalError):
        raise TemporalError("base error")


def test_configuration_error_inherits_temporal_error():
    err = ConfigurationError("missing env var")
    assert isinstance(err, TemporalError)
    assert str(err) == "missing env var"


def test_spiffe_error_with_cause():
    cause = ValueError("socket not found")
    err = SpiffeError("SPIFFE failed", cause=cause)
    assert isinstance(err, TemporalError)
    assert err.__cause__ is cause


def test_spiffe_error_without_cause():
    err = SpiffeError("no cause")
    assert err.__cause__ is None


def test_client_creation_error_with_cause():
    cause = OSError("connection refused")
    err = ClientCreationError("cannot connect", cause=cause)
    assert isinstance(err, TemporalError)
    assert err.__cause__ is cause


def test_worker_creation_error_inherits_temporal_error():
    err = WorkerCreationError("no workflows")
    assert isinstance(err, TemporalError)
