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

from sap_cloud_sdk.cbc import (
    ConfigurationData,
    ConsumptionVersions,
    EntityData,
    FeatureStatus,
    FeatureStatuses,
)
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


@scenario("cbc.feature", "Fetch feature statuses returns FeatureStatuses")
def test_get_feature_statuses_returns_feature_statuses():
    pass


@scenario("cbc.feature", "Look up a single feature status by id")
def test_get_feature_status_matches_full_list():
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


@when("I call get_feature_statuses")
def call_get_feature_statuses(ctx: dict, cbc_client: CBCClient):
    ctx["feature_statuses"] = cbc_client.get_feature_statuses()


@then("the result should be FeatureStatuses")
def assert_feature_statuses_type(ctx: dict):
    assert isinstance(ctx["feature_statuses"], FeatureStatuses)


@then("every feature should have a non-empty feature_id")
def assert_feature_ids_non_empty(ctx: dict):
    statuses: FeatureStatuses = ctx["feature_statuses"]
    for f in statuses.features:
        assert f.feature_id, "feature_id missing on a FeatureStatus"


@when("I call get_feature_status for the first feature id")
def call_get_feature_status(ctx: dict, cbc_client: CBCClient):
    statuses: FeatureStatuses = ctx["feature_statuses"]
    if not statuses.features:
        pytest.skip("tenant has no features — cannot test get_feature_status")
    ctx["first_feature_id"] = statuses.features[0].feature_id
    ctx["single_feature"] = cbc_client.get_feature_status(ctx["first_feature_id"])


@then("the result should be a FeatureStatus for the requested feature id")
def assert_single_feature_matches(ctx: dict):
    single: FeatureStatus | None = ctx["single_feature"]
    assert single is not None
    assert single.feature_id == ctx["first_feature_id"]
