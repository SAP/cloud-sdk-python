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
    ConfigEntity,
    EntityData,
)


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

    def test_latest_with_empty_list_returns_none(self):
        assert ConsumptionVersions(items=[]).latest() is None

    def test_latest_with_modified_dates_returns_most_recently_modified(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        v = ConsumptionVersions(
            items=[
                self._version("v1", modified=t1),
                self._version("v2", modified=t2),
            ]
        )
        result = v.latest()
        assert result is not None
        assert result.version == "v2"

    def test_latest_without_modified_dates_returns_most_recently_created(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        v = ConsumptionVersions(
            items=[
                self._version("v1", created=t1),
                self._version("v2", created=t2),
            ]
        )
        result = v.latest()
        assert result is not None
        assert result.version == "v2"

    def test_latest_without_any_dates_returns_last_item(self):
        v = ConsumptionVersions(items=[self._version("v1"), self._version("v2")])
        result = v.latest()
        assert result is not None
        assert result.version == "v2"


# ---------------------------------------------------------------------------
# EntityData
# ---------------------------------------------------------------------------


class TestEntityData:
    def test_as_list_with_list_content_returns_list(self):
        ec = EntityData([{"k": "v"}])
        assert ec.as_list() == [{"k": "v"}]

    def test_as_list_with_dict_content_raises_value_error(self):
        ec = EntityData({"k": "v"})
        with pytest.raises(ValueError, match="as_object"):
            ec.as_list()

    def test_as_object_with_dict_content_returns_dict(self):
        ec = EntityData({"k": "v"})
        assert ec.as_object() == {"k": "v"}

    def test_as_object_with_list_content_raises_value_error(self):
        ec = EntityData([{"k": "v"}])
        with pytest.raises(ValueError, match="as_list"):
            ec.as_object()

    def test_is_list_with_list_content_returns_true_and_is_object_returns_false(self):
        ec = EntityData([{"k": "v"}])
        assert ec.is_list() is True
        assert ec.is_object() is False

    def test_is_object_with_dict_content_returns_true_and_is_list_returns_false(self):
        ec = EntityData({"k": "v"})
        assert ec.is_object() is True
        assert ec.is_list() is False

    def test_value_with_any_content_returns_raw_without_shape_assertion(self):
        assert EntityData([{"k": "v"}]).value() == [{"k": "v"}]
        assert EntityData({"k": "v"}).value() == {"k": "v"}


# ---------------------------------------------------------------------------
# ConfigData helpers
# ---------------------------------------------------------------------------


class TestConfigData:
    def _entity_data(self, entity_id: str) -> ConfigEntity:
        return ConfigEntity(entity_id=entity_id, data=EntityData([{"id": entity_id}]))

    def _config_object(self, config_object_id: str, *entity_ids: str) -> ConfigObject:
        return ConfigObject(
            config_object_id=config_object_id,
            entities=[self._entity_data(eid) for eid in entity_ids],
        )

    def _config(self, *config_objects: ConfigObject) -> ConfigData:
        return ConfigData(
            consumption_version="cv1",
            app_tenant_id="app-t1",
            config_objects=list(config_objects),
        )

    def test_get_config_object_with_matching_id_returns_config_object(self):
        config = self._config(
            self._config_object("ObjA", "E1"),
            self._config_object("ObjB", "E2"),
        )
        result = config.get_config_object("ObjA")
        assert result is not None
        assert result.config_object_id == "ObjA"

    def test_get_config_object_with_missing_id_returns_none(self):
        config = self._config(self._config_object("ObjA", "E1"))
        assert config.get_config_object("Missing") is None

    def test_get_entity_data_with_matching_ids_returns_correct_entity_data(self):
        config = self._config(
            self._config_object("ObjA", "E1", "E2"),
        )
        result = config.get_entity_data("ObjA", "E2")
        assert result is not None
        assert isinstance(result, EntityData)
        assert result.as_list() == [{"id": "E2"}]

    def test_get_entity_data_with_missing_entity_id_returns_none(self):
        config = self._config(self._config_object("ObjA", "E1"))
        assert config.get_entity_data("ObjA", "Missing") is None


# ---------------------------------------------------------------------------
# ApiError.from_response
# ---------------------------------------------------------------------------


class TestApiError:
    def test_from_response_with_cbc_error_envelope_parses_code_and_message(self):
        body = b'{"error":{"code":"NOT_FOUND","message":"Resource not found"}}'
        err = ApiError.from_response(body)
        assert err.code == "NOT_FOUND"
        assert err.message == "Resource not found"

    def test_from_response_with_empty_body_falls_back_to_unknown_error(self):
        err = ApiError.from_response(None)
        assert err.code == "UNKNOWN_ERROR"

    def test_from_response_with_unparseable_body_falls_back_to_unknown_error(self):
        err = ApiError.from_response(b"not json")
        assert err.code == "UNKNOWN_ERROR"
        assert "not json" in err.message
