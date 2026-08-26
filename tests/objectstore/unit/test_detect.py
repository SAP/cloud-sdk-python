"""Tests for provider auto-detection logic."""

import os
from itertools import combinations
from unittest.mock import patch

import pytest

from sap_cloud_sdk.objectstore._detect import (
    _DISCRIMINATORS,
    detect_provider,
    read_binding_keys,
)


class TestDetectProvider:

    def test_s3_keys_detected_as_s3(self):
        keys = {"access_key_id", "secret_access_key", "host", "bucket", "region"}
        assert detect_provider(keys) == "s3"

    def test_azure_keys_detected_as_azure(self):
        keys = {"container_uri", "sas_token", "container_name", "account_name"}
        assert detect_provider(keys) == "azure"

    def test_gcs_keys_detected_as_gcs(self):
        # Real binding key names are camelCase (as they appear in the mount).
        keys = {"base64EncodedPrivateKeyData", "projectId", "bucket", "region"}
        assert detect_provider(keys) == "gcs"

    def test_gcs_wins_over_s3_when_gcs_discriminators_present(self):
        # GCS and S3 share 'bucket'/'region'; if GCS discriminators are present
        # it must be detected as GCS, not S3.
        keys = {
            "base64EncodedPrivateKeyData",
            "projectId",
            "bucket",
            "region",
        }
        assert detect_provider(keys) == "gcs"

    def test_empty_keys_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot detect objectstore provider"):
            detect_provider(set())

    def test_unrecognised_keys_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot detect objectstore provider"):
            detect_provider({"garbage", "unknown_key"})

    def test_mixed_non_matching_keys_raises_value_error(self):
        # Partial overlap with S3 but missing 'host'
        with pytest.raises(ValueError):
            detect_provider({"access_key_id", "secret_access_key"})

    def test_uppercase_keys_still_detected_as_s3(self):
        """detect_provider must lowercase before matching."""
        keys = {"ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "HOST"}
        assert detect_provider(keys) == "s3"

    def test_uppercase_azure_keys_still_detected(self):
        keys = {"CONTAINER_URI", "SAS_TOKEN", "CONTAINER_NAME"}
        assert detect_provider(keys) == "azure"

    def test_uppercase_gcs_keys_still_detected(self):
        # Env-var form: keys arrive fully uppercased.
        keys = {"BASE64ENCODEDPRIVATEKEYDATA", "PROJECTID"}
        assert detect_provider(keys) == "gcs"

    def test_camelcase_gcs_keys_detected(self):
        # Mount form: keys arrive verbatim in their binding camelCase.
        keys = {"base64EncodedPrivateKeyData", "projectId"}
        assert detect_provider(keys) == "gcs"

    def test_azure_wins_before_gcs_and_s3(self):
        """The azure discriminator set must be checked first."""
        # Artificially include both azure + gcs discriminators to verify ordering.
        keys = {
            "container_uri",
            "sas_token",
            "container_name",
            "base64EncodedPrivateKeyData",
            "projectId",
        }
        assert detect_provider(keys) == "azure"

    def test_discriminator_sets_are_pairwise_disjoint(self):
        """Each provider must own at least one key no other provider shares.

        Detection is first-match-wins; it is only unambiguous while the
        discriminator sets don't overlap. If a new provider is added with a
        discriminator that intersects an existing one, first-match ordering
        would silently pick the wrong provider — this test fails loudly instead.
        """
        lowered = {
            provider: {d.lower() for d in discriminators}
            for provider, discriminators in _DISCRIMINATORS.items()
        }
        for (p_a, set_a), (p_b, set_b) in combinations(lowered.items(), 2):
            overlap = set_a & set_b
            assert not overlap, (
                f"discriminators for {p_a} and {p_b} overlap on {sorted(overlap)}; "
                "detection can no longer distinguish these providers"
            )


class TestReadBindingKeysLegacyLayout:

    def test_legacy_layout_returns_verbatim_file_names(self, tmp_path, monkeypatch):
        """Files under {base}/objectstore/{instance}/ are returned verbatim (no case-folding)."""
        instance = "default"
        legacy_dir = tmp_path / "objectstore" / instance
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "access_key_id").touch()
        (legacy_dir / "SECRET_ACCESS_KEY").touch()
        (legacy_dir / "HOST").touch()

        # Patch resolve_base_mount to return our tmp dir as the base.
        monkeypatch.delenv("SERVICE_BINDING_ROOT", raising=False)
        monkeypatch.setattr(
            "sap_cloud_sdk.objectstore._detect.resolve_base_mount",
            lambda *a, **kw: str(tmp_path),
        )

        keys = read_binding_keys(instance)

        # Keys are returned as-is (verbatim filenames); no lowercasing here.
        assert "access_key_id" in keys
        assert "SECRET_ACCESS_KEY" in keys
        assert "HOST" in keys

    def test_legacy_layout_missing_dir_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SERVICE_BINDING_ROOT", raising=False)
        monkeypatch.setattr(
            "sap_cloud_sdk.objectstore._detect.resolve_base_mount",
            lambda *a, **kw: str(tmp_path),
        )
        keys = read_binding_keys("nonexistent-instance")
        assert keys == set()


class TestReadBindingKeysFlatLayout:

    def test_flat_layout_returns_file_names(self, tmp_path, monkeypatch):
        """Files under $SERVICE_BINDING_ROOT/objectstore/ are returned as keys."""
        flat_dir = tmp_path / "objectstore"
        flat_dir.mkdir(parents=True)
        (flat_dir / "container_uri").touch()
        (flat_dir / "sas_token").touch()
        (flat_dir / "container_name").touch()

        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.setattr(
            "sap_cloud_sdk.objectstore._detect.resolve_base_mount",
            lambda *a, **kw: str(tmp_path),
        )

        keys = read_binding_keys("any-instance")

        assert "container_uri" in keys
        assert "sas_token" in keys
        assert "container_name" in keys


class TestReadBindingKeysEnvLayout:

    def test_env_vars_stripped_verbatim(self, monkeypatch, tmp_path):
        """CLOUD_SDK_CFG_OBJECTSTORE_{INSTANCE}_* env vars are picked up; suffix is returned as-is (uppercase)."""
        monkeypatch.delenv("SERVICE_BINDING_ROOT", raising=False)
        monkeypatch.setattr(
            "sap_cloud_sdk.objectstore._detect.resolve_base_mount",
            lambda *a, **kw: str(tmp_path),
        )
        monkeypatch.setenv("CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID", "k")
        monkeypatch.setenv("CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY", "s")
        monkeypatch.setenv("CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST", "h")

        keys = read_binding_keys("default")

        # The prefix is stripped; the remaining suffix is returned as-is (uppercase).
        assert "ACCESS_KEY_ID" in keys
        assert "SECRET_ACCESS_KEY" in keys
        assert "HOST" in keys

    def test_env_vars_with_hyphens_in_instance_name(self, monkeypatch, tmp_path):
        """Hyphens in instance names become underscores in the env prefix."""
        monkeypatch.delenv("SERVICE_BINDING_ROOT", raising=False)
        monkeypatch.setattr(
            "sap_cloud_sdk.objectstore._detect.resolve_base_mount",
            lambda *a, **kw: str(tmp_path),
        )
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_ACCESS_KEY_ID", "val"
        )

        keys = read_binding_keys("my-instance")

        # The suffix after the prefix is returned verbatim (uppercase).
        assert "ACCESS_KEY_ID" in keys

    def test_env_vars_different_instance_not_picked_up(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SERVICE_BINDING_ROOT", raising=False)
        monkeypatch.setattr(
            "sap_cloud_sdk.objectstore._detect.resolve_base_mount",
            lambda *a, **kw: str(tmp_path),
        )
        monkeypatch.setenv("CLOUD_SDK_CFG_OBJECTSTORE_OTHER_HOST", "h")

        keys = read_binding_keys("default")

        assert "host" not in keys
