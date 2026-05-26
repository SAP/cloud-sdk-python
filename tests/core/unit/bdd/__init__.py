"""Shared conftest for core BDD unit tests."""
import pytest


@pytest.fixture
def context():
    """Generic mutable context bag for BDD step state sharing."""
    return {}
