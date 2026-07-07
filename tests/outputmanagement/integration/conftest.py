# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company and Cloud SDK contributors
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for Output Management integration tests."""

import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.outputmanagement import create_client

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def output_management_client():
    """Create an Output Management client for cloud testing using secret resolver."""
    _setup_cloud_mode()

    try:
        # Secret resolver handles configuration automatically from /etc/secrets/appfnd or CLOUD_SDK_CFG
        client = create_client(instance="default")
        return client
    except Exception as e:
        pytest.skip(f"Output Management integration tests require credentials: {e}")


def _setup_cloud_mode():
    """Common setup for cloud mode integration tests."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)
