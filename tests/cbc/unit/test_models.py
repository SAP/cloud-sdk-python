"""Unit tests for CBC data models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sap_cloud_sdk.cbc._models import (
    ApiError,
    ConfigData,
    ConfigObject,
    ConsumptionVersion,
    ConsumptionVersions,
    EntityContent,
    EntityData,
    TenantContext,
)


# ---------------------------------------------------------------------------
# TenantContext
# ---------------------------------------------------------------------------


class TestTenantContext:
    def test_accepts_camel_case_aliases(self):
        ctx = TenantContext(cbcTenantId="cbc-1", appTenantId="app-1")
        assert ctx.cbc_tenant_id == "cbc-1"
        assert ctx.app_tenant_id == "app-1"

    def test_accepts_snake_case_names(self):
        ctx = TenantContext(cbc_tenant_id="cbc-1", app_tenant_id="app-1")
        assert ctx.cbc_tenant_id == "cbc-1"

    def test_rejects_empty_cbc_tenant_id(self):
        with pytest.raises(Exception):
            TenantContext(cbcTenantId="", appTenantId="app-1")


# ---------------------------------------------------------------------------
# ConsumptionVersions.latest()
# ---------------------------------------------------------------------------


class TestConsumptionVersionsLatest:
    def _version(
        self,
        version: str,
        modified: datetime | None = None,
        created: datetime | None = None,
    ) -> ConsumptionVersion:
        return ConsumptionVersion(
            version=version,
            modifiedDate=modified,
            createdDate=created,
        )

    def test_returns_none_for_empty_list(self):
        assert ConsumptionVersions(items=[]).latest() is None

    def test_returns_latest_by_modified_date(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        v = ConsumptionVersions(
            items=[
                self._version("v1", modified=t1),
                self._version("v2", modified=t2),
            ]
        )
        assert v.latest().version == "v2"

    def test_returns_latest_by_created_date_when_no_modified(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        v = ConsumptionVersions(
            items=[
                self._version("v1", created=t1),
                self._version("v2", created=t2),
            ]
        )
        assert v.latest().version == "v2"

    def test_returns_last_item_when_no_dates(self):
        v = ConsumptionVersions(
            items=[self._version("v1"), self._version("v2")]
        )
        assert v.latest().version == "v2"


# ---------------------------------------------------------------------------
# EntityContent
# ---------------------------------------------------------------------------


class TestEntityContent:
    def test_as_list_returns_list(self):
        ec = EntityContent([{"k": "v"}])
        assert ec.as_list() == [{"k": "v"}]

    def test_as_list_raises_when_dict(self):
        ec = EntityContent({"k": "v"})
        with pytest.raises(ValueError, match="as_object"):
            ec.as_list()

    def test_as_object_returns_dict(self):
        ec = EntityContent({"k": "v"})
        assert ec.as_object() == {"k": "v"}

    def test_as_object_raises_when_list(self):
        ec = EntityContent([{"k": "v"}])
        with pytest.raises(ValueError, match="as_list"):
            ec.as_object()


# ---------------------------------------------------------------------------
# ConfigData helpers
# ---------------------------------------------------------------------------


class TestConfigData:
    def _entity_data(self, entity_id: str) -> EntityData:
        return EntityData(entity_id=entity_id, data=EntityContent([]))

    def _config_object(self, config_object_id: str, *entity_ids: str) -> ConfigObject:
        return ConfigObject(
            config_object_id=config_object_id,
            entities=[self._entity_data(eid) for eid in entity_ids],
        )

    def _config(self, *config_objects: ConfigObject) -> ConfigData:
        return ConfigData(
            consumption_version="cv1",
            tenant_context=TenantContext(cbcTenantId="t1", appTenantId="app-t1"),
            config_objects=list(config_objects),
        )

    def test_get_config_object_returns_matching(self):
        config = self._config(
            self._config_object("ObjA", "E1"),
            self._config_object("ObjB", "E2"),
        )
        result = config.get_config_object("ObjA")
        assert result is not None
        assert result.config_object_id == "ObjA"

    def test_get_config_object_returns_none_when_missing(self):
        config = self._config(self._config_object("ObjA", "E1"))
        assert config.get_config_object("Missing") is None

    def test_get_entity_data_returns_match(self):
        config = self._config(
            self._config_object("ObjA", "E1", "E2"),
        )
        result = config.get_entity_data("ObjA", "E2")
        assert result is not None
        assert result.entity_id == "E2"

    def test_get_entity_data_returns_none_when_missing(self):
        config = self._config(self._config_object("ObjA", "E1"))
        assert config.get_entity_data("ObjA", "Missing") is None


# ---------------------------------------------------------------------------
# ApiError.from_response
# ---------------------------------------------------------------------------


class TestApiError:
    def test_parses_cbc_error_envelope(self):
        body = b'{"error":{"code":"NOT_FOUND","message":"Resource not found"}}'
        err = ApiError.from_response(body)
        assert err.code == "NOT_FOUND"
        assert err.message == "Resource not found"

    def test_fallback_on_empty_body(self):
        err = ApiError.from_response(None)
        assert err.code == "UNKNOWN_ERROR"

    def test_fallback_on_unparseable_body(self):
        err = ApiError.from_response(b"not json")
        assert err.code == "UNKNOWN_ERROR"
        assert "not json" in err.message
