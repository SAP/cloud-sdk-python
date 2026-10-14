"""BDD integration tests for the CBC (Central Business Configuration) module.

Run against a real CBC server via the default provisioning path. Supply the
Destination Service binding and the target tenant (see conftest.py for the full
list), then::

    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI=... \\
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE=... \\
    CLOUD_SDK_CFG_CBC_DEFAULT_APP_TENANT_ID=... \\
    CLOUD_SDK_CFG_CBC_DEFAULT_TENANT_SUBDOMAIN=... \\
    CLOUD_SDK_CFG_CBC_DEFAULT_LANDSCAPE=... \\
    pytest tests/cbc/integration
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenario, then, when

from sap_cloud_sdk.cbc import ConfigurationData, ConsumptionVersions, EntityData
from sap_cloud_sdk.cbc.client import CBCClient

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


@scenario("cbc.feature", "Fetch full configuration returns ConfigurationData")
def test_get_configuration_returns_configuration_data():
    pass


@scenario("cbc.feature", "Full configuration contains at least one config object")
def test_configuration_has_configuration_objects():
    pass


@scenario(
    "cbc.feature", "Every entity within each config object has an entity_id and data"
)
def test_every_entity_has_id_and_data():
    pass


@scenario(
    "cbc.feature",
    "Fetch a single entity directly returns EntityData",
)
def test_get_entity_data_returns_entity_data():
    pass


# -- Steps ---------------------------------------------------------------------


@given("a configured CBC client and tenant context")
def cbc_context(cbc_client: CBCClient, cbc_app_tenant_id: str):
    pass


@when("I call get_consumption_versions")
def call_get_consumption_versions(ctx: dict, cbc_client: CBCClient):
    ctx["versions"] = cbc_client.get_consumption_versions()


@when("I call get_configuration")
def call_get_configuration(ctx: dict, cbc_client: CBCClient):
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


@then("the result should be a ConfigurationData with a non-empty consumption_version")
def assert_configuration_data_type(ctx: dict):
    config: ConfigurationData = ctx["config"]
    assert isinstance(config, ConfigurationData)
    assert config.consumption_version


@then("the app_tenant_id should match the configured tenant")
def assert_app_tenant_id(ctx: dict, cbc_app_tenant_id: str):
    config: ConfigurationData = ctx["config"]
    assert config.app_tenant_id == cbc_app_tenant_id


@then("the result should contain at least one config object")
def assert_configuration_objects_non_empty(ctx: dict):
    config: ConfigurationData = ctx["config"]
    assert len(config.configuration_objects) >= 1


@then("every entity should have a non-empty entity_id")
def assert_entity_ids(ctx: dict):
    config: ConfigurationData = ctx["config"]
    for co in config.configuration_objects:
        for ed in co.entities:
            assert ed.entity_id, (
                f"entity_id missing in configuration_object={co.configuration_object_id!r}"
            )


@then("every entity data should be accessible as a list or object")
def assert_entity_data_accessible(ctx: dict):
    config: ConfigurationData = ctx["config"]
    for co in config.configuration_objects:
        for ed in co.entities:
            raw = ed.data
            try:
                result = raw.as_list()
                assert result is not None
            except ValueError:
                result = raw.as_object()
                assert result is not None


@when("I call get_entity_data for the first entity in the first config object")
def call_get_entity_data(ctx: dict, cbc_client: CBCClient):
    config: ConfigurationData = cbc_client.get_configuration()
    assert config.configuration_objects, (
        "no config objects — cannot test get_entity_data"
    )
    co = config.configuration_objects[0]
    assert co.entities, f"no entities in {co.configuration_object_id!r}"
    entity_id = co.entities[0].entity_id
    ctx["entity_data"] = cbc_client.get_entity_data(
        co.configuration_object_id, entity_id
    )


@then("the result should be EntityData accessible as a list or object")
def assert_single_entity_data(ctx: dict):
    data: EntityData = ctx["entity_data"]
    assert isinstance(data, EntityData)
    try:
        result = data.as_list()
        assert result is not None
    except ValueError:
        result = data.as_object()
        assert result is not None
