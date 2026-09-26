"""BDD integration tests for the CBC (Central Business Configuration) module.

Run against a real or mock CBC server::

    CLOUD_SDK_CBC_URL=http://localhost:8001 \\
    CLOUD_SDK_CBC_CBC_TENANT_ID=my-cbc-tenant \\
    CLOUD_SDK_CBC_APP_TENANT_ID=my-app-tenant \\
    pytest tests/cbc/integration

Or against production (with mTLS)::

    CLOUD_SDK_CBC_URL=https://cbc.example.ondemand.com \\
    CLOUD_SDK_CBC_CERT_PATH=/run/secrets/tls.crt \\
    CLOUD_SDK_CBC_KEY_PATH=/run/secrets/tls.key \\
    CLOUD_SDK_CBC_CBC_TENANT_ID=my-cbc-tenant \\
    CLOUD_SDK_CBC_APP_TENANT_ID=my-app-tenant \\
    pytest tests/cbc/integration
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenario, then, when

from sap_cloud_sdk.cbc import ConfigData, ConsumptionVersions, TenantContext
from sap_cloud_sdk.cbc.client import DefaultClient

pytestmark = pytest.mark.integration


# -- Shared step state ---------------------------------------------------------


@pytest.fixture
def ctx() -> dict:
    return {}


# -- Scenarios -----------------------------------------------------------------


@scenario("cbc.feature", "Fetch consumption versions returns at least one version")
def test_consumption_versions_non_empty():
    pass


@scenario("cbc.feature", "Latest consumption version is non-empty")
def test_latest_version_non_empty():
    pass


@scenario("cbc.feature", "Fetch full configuration returns ConfigData")
def test_get_configuration_returns_config_data():
    pass


@scenario("cbc.feature", "Full configuration contains at least one config object")
def test_configuration_has_config_objects():
    pass


@scenario(
    "cbc.feature", "Every entity within each config object has an entity_id and data"
)
def test_every_entity_has_id_and_data():
    pass


# -- Steps ---------------------------------------------------------------------


@given("a configured CBC client and tenant context")
def cbc_context(cbc_client: DefaultClient, cbc_tenant: TenantContext):
    pass


@when("I call get_consumption_versions")
def call_get_consumption_versions(ctx: dict, cbc_client: DefaultClient):
    ctx["versions"] = cbc_client.get_consumption_versions()


@when("I call get_configuration")
def call_get_configuration(ctx: dict, cbc_client: DefaultClient):
    ctx["config"] = cbc_client.get_configuration()


@then("the result should contain at least one version")
def assert_versions_non_empty(ctx: dict):
    versions: ConsumptionVersions = ctx["versions"]
    assert len(versions.items) >= 1


@then("the latest version should have a non-empty version string")
def assert_latest_version_non_empty(ctx: dict):
    versions: ConsumptionVersions = ctx["versions"]
    latest = versions.latest()
    assert latest is not None
    assert latest.version


@then("the result should be a ConfigData with a non-empty consumption_version")
def assert_config_data_type(ctx: dict):
    config: ConfigData = ctx["config"]
    assert isinstance(config, ConfigData)
    assert config.consumption_version


@then("the tenant_context should match the configured tenant")
def assert_tenant_context(ctx: dict, cbc_tenant: TenantContext):
    config: ConfigData = ctx["config"]
    assert config.tenant_context == cbc_tenant


@then("the result should contain at least one config object")
def assert_config_objects_non_empty(ctx: dict):
    config: ConfigData = ctx["config"]
    assert len(config.config_objects) >= 1


@then("every entity should have a non-empty entity_id")
def assert_entity_ids(ctx: dict):
    config: ConfigData = ctx["config"]
    for co in config.config_objects:
        for ed in co.entities:
            assert ed.entity_id, (
                f"entity_id missing in config_object={co.config_object_id!r}"
            )


@then("every entity data should be accessible as a list or object")
def assert_entity_data_accessible(ctx: dict):
    config: ConfigData = ctx["config"]
    for co in config.config_objects:
        for ed in co.entities:
            raw = ed.data
            try:
                result = raw.as_list()
                assert result is not None
            except ValueError:
                result = raw.as_object()
                assert result is not None
