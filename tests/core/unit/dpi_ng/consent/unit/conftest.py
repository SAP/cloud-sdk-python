"""Unit-test fixtures — auto-marks every test in tests/unit/ with `unit`."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        item.add_marker(pytest.mark.unit)
