"""Tests for ConfigFactory."""

import os
from dataclasses import dataclass
from unittest.mock import MagicMock, call, patch

import pytest

from sap_cloud_sdk.core.secret_resolver._config_factory import ConfigFactory

_RESOLVER_PATH = "sap_cloud_sdk.core.secret_resolver.read_from_mount_and_fallback_to_env_var"


@dataclass
class _Binding:
    value: str = ""

    def validate(self) -> None:
        pass


def _make_factory(
    module: str = "test-module",
    instance: str = "default",
    base_volume_mount: str = "/fake",
    base_var_name: str = "CLOUD_SDK_CFG",
) -> ConfigFactory[str]:
    return ConfigFactory(
        module=module,
        instance=instance,
        binding_cls=_Binding,
        extract=lambda b: b.value,
        base_volume_mount=base_volume_mount,
        base_var_name=base_var_name,
    )


class TestConfigFactoryCall:
    def test_returns_extracted_value(self):
        factory = _make_factory()
        with patch(_RESOLVER_PATH) as mock_resolve:
            def _fill(*, target, **_kw):
                target.value = "hello"

            mock_resolve.side_effect = _fill
            assert factory() == "hello"

    def test_passes_correct_args_to_resolver(self):
        factory = _make_factory(
            module="my-svc",
            instance="tenant-a",
            base_volume_mount="/mnt/secrets",
            base_var_name="MY_PREFIX",
        )
        with patch(_RESOLVER_PATH) as mock_resolve:
            factory()
        mock_resolve.assert_called_once_with(
            base_volume_mount="/mnt/secrets",
            base_var_name="MY_PREFIX",
            module="my-svc",
            instance="tenant-a",
            target=mock_resolve.call_args.kwargs["target"],
        )

    def test_calls_validate_on_binding(self, monkeypatch):
        validate_mock = MagicMock()
        monkeypatch.setattr(_Binding, "validate", validate_mock)
        factory = _make_factory()
        with patch(_RESOLVER_PATH):
            factory()
        validate_mock.assert_called_once()

    def test_validate_error_propagates(self):
        @dataclass
        class _BadBinding:
            def validate(self) -> None:
                raise ValueError("invalid binding")

        factory = ConfigFactory(
            module="m",
            instance="i",
            binding_cls=_BadBinding,
            extract=lambda b: "ok",
            base_volume_mount="/fake",
        )
        with patch(_RESOLVER_PATH), pytest.raises(ValueError, match="invalid binding"):
            factory()

    def test_extract_error_propagates(self):
        factory = ConfigFactory(
            module="m",
            instance="i",
            binding_cls=_Binding,
            extract=lambda b: (_ for _ in ()).throw(RuntimeError("bad extract")),
            base_volume_mount="/fake",
        )
        with patch(_RESOLVER_PATH), pytest.raises(RuntimeError, match="bad extract"):
            factory()


class TestConfigFactoryWatchPath:
    def test_watch_path_constructed_from_parts(self):
        factory = _make_factory(
            module="hana-agent-memory",
            instance="acme-corp",
            base_volume_mount="/etc/secrets/appfnd",
        )
        expected = os.path.join("/etc/secrets/appfnd", "hana-agent-memory", "acme-corp")
        assert factory._watch_path == expected

    def test_custom_base_volume_mount_used_in_watch_path(self):
        factory = _make_factory(module="svc", instance="inst", base_volume_mount="/custom/mount")
        assert factory._watch_path == "/custom/mount/svc/inst"


class TestConfigFactoryHasChanged:
    def test_first_call_records_baseline_and_returns_false(self):
        factory = _make_factory()
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            assert factory.has_changed() is False
            assert factory._last_mtime == 1000.0

    def test_unchanged_mtime_returns_false(self):
        factory = _make_factory()
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            factory.has_changed()  # baseline
            assert factory.has_changed() is False

    def test_changed_mtime_returns_true(self):
        factory = _make_factory()
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            factory.has_changed()  # baseline
            mock_stat.return_value.st_mtime = 2000.0
            assert factory.has_changed() is True

    def test_mtime_reverting_still_returns_true(self):
        """A lower mtime (e.g. remount) is also a change — != not >."""
        factory = _make_factory()
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 2000.0
            factory.has_changed()  # baseline
            mock_stat.return_value.st_mtime = 1000.0
            assert factory.has_changed() is True

    def test_after_change_next_unchanged_call_returns_false(self):
        """After detecting a change _last_mtime is updated; stable call returns False."""
        factory = _make_factory()
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            factory.has_changed()  # baseline
            mock_stat.return_value.st_mtime = 2000.0
            assert factory.has_changed() is True   # change detected, _last_mtime → 2000
            assert factory.has_changed() is False  # still 2000, no change

    def test_oserror_returns_false(self):
        factory = _make_factory()
        with patch("os.stat", side_effect=OSError("no such file")):
            assert factory.has_changed() is False

    def test_oserror_after_baseline_returns_false(self):
        factory = _make_factory()
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            factory.has_changed()  # baseline
        with patch("os.stat", side_effect=OSError("mount gone")):
            assert factory.has_changed() is False

    def test_stat_called_with_watch_path(self):
        factory = _make_factory(module="svc", instance="inst", base_volume_mount="/mnt")
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1.0
            factory.has_changed()
        mock_stat.assert_called_once_with("/mnt/svc/inst")
