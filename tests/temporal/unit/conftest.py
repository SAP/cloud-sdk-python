"""Pytest configuration for Temporal unit tests."""

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "temporal/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
