"""
Pytest fixtures for ADMS end-to-end integration tests.

Two modes are supported — controlled by environment variables:

  MODE 1 — External (BTP / remote) server
  ----------------------------------------
  Set CLOUD_SDK_ADMS_INTEGRATION_URL to point to a running ADM instance.
  The SDK uses real IAS credentials read from the standard secret-mount or
  env-var pattern (CLOUD_SDK_CFG_ADMS_DEFAULT_*).

    export CLOUD_SDK_ADMS_INTEGRATION_URL=https://your-adm.cfapps.eu20.hana.ondemand.com
    export CLOUD_SDK_CFG_ADMS_DEFAULT_URL=https://your-tenant.accounts.ondemand.com
    export CLOUD_SDK_CFG_ADMS_DEFAULT_URI=https://your-adm.cfapps.eu20.hana.ondemand.com
    export CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTID=...
    export CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTSECRET=...
    export CLOUD_SDK_CFG_ADMS_DEFAULT_RESOURCE=urn:sap:identity:application:provider:name:your-app

  MODE 2 — Local HDM server (auto-started)
  -----------------------------------------
  Leave CLOUD_SDK_ADMS_INTEGRATION_URL unset.  This fixture starts the HDM
  Spring Boot server (srv/) locally on port 18080 via Maven, using the
  default/H2 profile with Spring Security disabled.

  Requires:
    - mvn 3.9+ on PATH
    - Java 21 on PATH
    - HDM source at HDM_DIR (default: ../hdm relative to this repo, or
      override with CLOUD_SDK_HDM_DIR env var)

  To skip if HDM cannot start, set:
    export CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE=true
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from typing import Generator, Optional
from unittest.mock import MagicMock

import pytest
import requests as _requests

from sap_cloud_sdk.adms._auth import IasTokenFetcher
from sap_cloud_sdk.adms._http import AdmsHttp
from sap_cloud_sdk.adms.client import AsyncAdmsClient, create_async_client
from sap_cloud_sdk.adms.client import AdmsClient
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms import create_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_HDM_PORT = int(os.getenv("CLOUD_SDK_HDM_PORT", "18080"))
_HDM_HEALTH = f"http://localhost:{_HDM_PORT}/actuator/health"

# Path to the HDM repo root — default: sibling directory next to cloud-sdk-python
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SDK_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))
_DEFAULT_HDM_DIR = os.path.abspath(os.path.join(_SDK_ROOT, "..", "hdm"))
_HDM_DIR = os.getenv("CLOUD_SDK_HDM_DIR", _DEFAULT_HDM_DIR)

_STARTUP_TIMEOUT_S = 120  # seconds to wait for HDM to be ready
_STARTUP_POLL_INTERVAL_S = 3

# Static dummy token accepted by CAP in default/H2 mode (security disabled)
_DUMMY_BEARER = "integration-test-dummy-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("localhost", port)) == 0


def _wait_for_hdm(base_url: str, timeout: int, skip_if_unavailable: bool) -> bool:
    """Poll the health endpoint until it responds 200 or timeout elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = _requests.get(f"{base_url}/actuator/health", timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(_STARTUP_POLL_INTERVAL_S)

    if skip_if_unavailable:
        return False
    pytest.fail(
        f"HDM server did not become healthy at {base_url} within {timeout}s. "
        "Set CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE=true to skip instead of fail.",
        pytrace=False,
    )
    return False  # unreachable


# ---------------------------------------------------------------------------
# Session-scoped server fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def hdm_base_url() -> Generator[str, None, None]:
    """Yield the base URL of a running HDM server.

    Starts HDM locally if CLOUD_SDK_ADMS_INTEGRATION_URL is not set.
    Skips all integration tests if the server cannot be reached and
    CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE=true.
    """
    skip_if_unavailable = os.getenv("CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE", "").lower() == "true"

    # --- Mode 1: external server ---
    external = os.getenv("CLOUD_SDK_ADMS_INTEGRATION_URL", "").rstrip("/")
    if external:
        if not _wait_for_hdm(external, timeout=10, skip_if_unavailable=skip_if_unavailable):
            pytest.skip(f"External HDM server not reachable at {external}")
        yield external
        return

    # --- Mode 2: local auto-start ---
    local_base = f"http://localhost:{_HDM_PORT}"

    # Re-use if already running
    if _is_port_open(_HDM_PORT):
        if _wait_for_hdm(local_base, timeout=10, skip_if_unavailable=skip_if_unavailable):
            yield local_base
            return

    # Verify HDM source is present
    if not os.path.isdir(_HDM_DIR):
        if skip_if_unavailable:
            pytest.skip(f"HDM source directory not found at {_HDM_DIR}")
        pytest.fail(
            f"HDM source not found at {_HDM_DIR}. "
            "Set CLOUD_SDK_HDM_DIR to the HDM repo root or "
            "CLOUD_SDK_ADMS_SKIP_IF_UNAVAILABLE=true.",
            pytrace=False,
        )

    # Start HDM with Spring Security disabled so the Python SDK can call it
    # without real IAS credentials.  H2 in-memory DB is used automatically
    # in the 'default' profile.
    cmd = [
        "mvn",
        "-pl", "srv",
        "spring-boot:run",
        "-q",
        f"-Dspring-boot.run.jvmArguments="
        f"-Dserver.port={_HDM_PORT} "
        f"-Dspring.security.enabled=false "
        f"-Dadm.redis.enabled=false "
        f"-Dmanagement.endpoints.web.exposure.include=health",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=_HDM_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # create process group for clean teardown
    )

    ready = _wait_for_hdm(local_base, timeout=_STARTUP_TIMEOUT_S, skip_if_unavailable=skip_if_unavailable)
    if not ready:
        proc.terminate()
        pytest.skip("HDM server did not start in time")

    yield local_base

    # Teardown: kill the whole process group
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=15)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# AdmsConfig fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def adms_config(hdm_base_url: str) -> AdmsConfig:
    """AdmsConfig pointing at the integration server.

    IAS fields are set to dummy values — real IAS is bypassed by the
    patched token fetcher below.  When CLOUD_SDK_ADMS_INTEGRATION_URL is
    set, real IAS credentials should be supplied via CLOUD_SDK_CFG_ADMS_*
    env vars and the real token fetcher is used.
    """
    if os.getenv("CLOUD_SDK_ADMS_INTEGRATION_URL"):
        # External mode — resolve config from env/mount as normal
        from sap_cloud_sdk.adms.config import load_from_env_or_mount
        return load_from_env_or_mount("default")

    return AdmsConfig(
        service_url=hdm_base_url,
        ias_url="http://dummy-ias.localhost",
        client_id="integration-test-client",
        client_secret="integration-test-secret",
    )


# ---------------------------------------------------------------------------
# AdmsClient fixture (sync)
# ---------------------------------------------------------------------------

def _make_mock_fetcher(config: AdmsConfig) -> IasTokenFetcher:
    """Return an IasTokenFetcher whose get_token / exchange_token are stubbed.

    In local H2 mode HDM runs with spring.security.enabled=false so any Bearer
    value is accepted.  In external mode real tokens are used instead.
    """
    fetcher = IasTokenFetcher(config=config)
    fetcher.get_token = MagicMock(return_value=_DUMMY_BEARER)  # type: ignore[assignment]
    fetcher.exchange_token = MagicMock(return_value=_DUMMY_BEARER)  # type: ignore[assignment]
    return fetcher


@pytest.fixture(scope="session")
def adms_client(adms_config: AdmsConfig) -> AdmsClient:
    """Return a AdmsClient wired to the integration server.

    Uses a real IasTokenFetcher in external mode; stubs it in local H2 mode.
    """
    if os.getenv("CLOUD_SDK_ADMS_INTEGRATION_URL"):
        # Real IAS — credentials must be in env/mount
        return create_client(config=adms_config)

    client = create_client(config=adms_config)
    fetcher = _make_mock_fetcher(adms_config)
    client._http._token_fetcher = fetcher
    return client


# ---------------------------------------------------------------------------
# AsyncAdmsClient fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def async_adms_client(adms_config: AdmsConfig) -> AsyncAdmsClient:
    """Return an AsyncAdmsClient wired to the integration server."""
    if os.getenv("CLOUD_SDK_ADMS_INTEGRATION_URL"):
        return create_async_client(config=adms_config)

    client = create_async_client(config=adms_config)
    fetcher = _make_mock_fetcher(adms_config)
    client._http._token_fetcher = fetcher
    return client


# ---------------------------------------------------------------------------
# Pre-requisite: business object type ID
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def bo_type_id(adms_client: AdmsClient) -> str:
    """Return a BusinessObjectNodeType unique ID for use in tests.

    Reads the first available type from the ConfigurationService.
    Creates a test type if none exist.
    """
    import requests as req

    # Call ConfigurationService directly (not in SDK scope) to get/create a BO type
    base = adms_client._http._config.service_url.rstrip("/")
    bearer = adms_client._http._token_fetcher.get_token()

    resp = req.get(
        f"{base}/odata/v4/ConfigurationService/BusinessObjectNodeType",
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("value", [])
    if data:
        return data[0]["BusinessObjectNodeTypeUniqueID"]

    # Create one
    csrf_resp = req.get(
        f"{base}/odata/v4/ConfigurationService/",
        headers={
            "Authorization": f"Bearer {bearer}",
            "X-CSRF-Token": "Fetch",
        },
        timeout=15,
    )
    csrf = csrf_resp.headers.get("X-CSRF-Token", "")

    create_resp = req.post(
        f"{base}/odata/v4/ConfigurationService/BusinessObjectNodeType",
        json={
            "BusinessObjectNodeTypeUniqueID": "PY_SDK_TEST_BO",
            "Description": "Created by Python SDK integration test",
        },
        headers={
            "Authorization": f"Bearer {bearer}",
            "X-CSRF-Token": csrf,
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    create_resp.raise_for_status()
    return "PY_SDK_TEST_BO"
