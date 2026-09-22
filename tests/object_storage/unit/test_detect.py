"""Unit tests for provider auto-detection (``object_storage._detect``)."""

import os

import pytest

from sap_cloud_sdk.object_storage import _detect
from sap_cloud_sdk.object_storage._detect import detect_provider, read_binding_keys
from sap_cloud_sdk.object_storage._models import ObjectStoreProvider

S3_KEYS = {"access_key_id", "secret_access_key", "bucket", "host"}
AZURE_KEYS = {"container_uri", "sas_token", "container_name"}
GCS_KEYS = {"base64EncodedPrivateKeyData", "projectId", "bucket"}


def _write_binding(directory, keys):
    directory.mkdir(parents=True, exist_ok=True)
    for key in keys:
        (directory / key).write_text("x")


@pytest.fixture
def base_mount(tmp_path, monkeypatch):
    """Point detection at an isolated mount and clear objectstore env vars."""
    monkeypatch.setattr(_detect, "resolve_base_mount", lambda _default: str(tmp_path))
    for var in list(os.environ):
        if var.upper().startswith("CLOUD_SDK_CFG_OBJECTSTORE_"):
            monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("SERVICE_BINDING_ROOT", raising=False)
    return tmp_path


class TestReadBindingKeys:
    def test_legacy_mount_complete_signature_returns_its_keys(self, base_mount):
        _write_binding(base_mount / "objectstore" / "default", S3_KEYS)
        assert read_binding_keys("default") == S3_KEYS

    def test_flat_mount_scanned_only_when_service_binding_root_set(
        self, base_mount, monkeypatch
    ):
        _write_binding(base_mount / "objectstore", AZURE_KEYS)
        assert read_binding_keys("default") == set()

        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(base_mount))
        assert read_binding_keys("default") == AZURE_KEYS

    def test_env_vars_uppercase_and_hyphen_instance_normalised(
        self, base_mount, monkeypatch
    ):
        prefix = "CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_"
        for key in S3_KEYS:
            monkeypatch.setenv(f"{prefix}{key.upper()}", "v")
        assert read_binding_keys("my-instance") == {k.upper() for k in S3_KEYS}

    def test_env_var_with_empty_suffix_excluded(self, base_mount, monkeypatch):
        monkeypatch.setenv("CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_", "v")
        assert read_binding_keys("default") == set()

    def test_first_source_with_complete_signature_wins(self, base_mount, monkeypatch):
        _write_binding(base_mount / "objectstore" / "default", S3_KEYS)
        for key in AZURE_KEYS:
            monkeypatch.setenv(f"CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_{key.upper()}", "v")
        assert read_binding_keys("default") == S3_KEYS

    def test_no_complete_signature_falls_back_to_first_non_empty(self, base_mount):
        _write_binding(base_mount / "objectstore" / "default", {"host", "bucket"})
        assert read_binding_keys("default") == {"host", "bucket"}

    def test_directories_are_ignored_only_files_counted(self, base_mount):
        instance_dir = base_mount / "objectstore" / "default"
        instance_dir.mkdir(parents=True)
        (instance_dir / "nested").mkdir()
        (instance_dir / "host").write_text("x")
        assert read_binding_keys("default") == {"host"}

    def test_all_sources_empty_returns_empty_set(self, base_mount):
        assert read_binding_keys("default") == set()


class TestDetectProvider:
    def test_exact_s3_signature_returns_s3(self):
        assert detect_provider(S3_KEYS) is ObjectStoreProvider.S3

    def test_exact_azure_signature_returns_azure(self):
        assert detect_provider(AZURE_KEYS) is ObjectStoreProvider.AZURE

    def test_exact_gcs_signature_returns_gcs(self):
        assert detect_provider(GCS_KEYS) is ObjectStoreProvider.GCS

    def test_detection_is_case_insensitive(self):
        assert detect_provider({k.upper() for k in AZURE_KEYS}) is (
            ObjectStoreProvider.AZURE
        )

    def test_extra_unrelated_keys_are_ignored(self):
        assert detect_provider(S3_KEYS | {"region", "tags"}) is ObjectStoreProvider.S3

    def test_no_matching_signature_raises_valueerror(self):
        with pytest.raises(ValueError, match="Cannot detect objectstore provider"):
            detect_provider({"host", "bucket"})

    def test_multiple_matching_signatures_raise_valueerror(self):
        with pytest.raises(ValueError, match="match multiple providers"):
            detect_provider(S3_KEYS | GCS_KEYS)
