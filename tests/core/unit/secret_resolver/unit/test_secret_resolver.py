"""Tests for secret_resolver module."""

import os
from dataclasses import dataclass, field
from unittest.mock import patch, mock_open
import pytest

from sap_cloud_sdk.core.secret_resolver import read_from_mount_and_fallback_to_env_var


@dataclass
class SampleConfig:
    username: str = field(default="", metadata={"secret": "user"})
    password: str = ""
    endpoint: str = "default"


@dataclass
class NonStringConfig:
    count: int = 0


class TestSecretResolver:

    def test_validate_inputs_empty_module(self):
        config = SampleConfig()
        with pytest.raises(ValueError, match="module name cannot be empty"):
            read_from_mount_and_fallback_to_env_var("/path", "VAR", "", "instance", config)

    def test_validate_inputs_empty_instance(self):
        config = SampleConfig()
        with pytest.raises(ValueError, match="instance name cannot be empty"):
            read_from_mount_and_fallback_to_env_var("/path", "VAR", "module", "", config)

    def test_non_dataclass_target(self):
        with pytest.raises(RuntimeError, match="failed to read secrets.*target must be a dataclass instance"):
            read_from_mount_and_fallback_to_env_var("/path", "VAR", "module", "instance", "not_dataclass")

    def test_non_string_field_error(self):
        config = NonStringConfig()
        with pytest.raises(RuntimeError, match="failed to read secrets.*is not a string"):
            read_from_mount_and_fallback_to_env_var("/path", "VAR", "module", "instance", config)

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_from_mount_success(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="test_user").return_value,
            mock_open(read_data="test_pass").return_value,
            mock_open(read_data="test_endpoint").return_value
        ]

        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)

        assert config.username == "test_user"
        assert config.password == "test_pass"
        assert config.endpoint == "test_endpoint"

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_load_from_mount_file_not_found(self, mock_file, mock_stat, mock_isdir):
        config = SampleConfig()
        with pytest.raises(RuntimeError, match="failed to read secrets.*failed to read secret file"):
            read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)

    @patch('os.stat', side_effect=FileNotFoundError("Path not found"))
    def test_validate_path_not_exists(self, mock_stat):
        config = SampleConfig()
        with pytest.raises(RuntimeError, match="mount failed"):
            read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)

    @patch('os.path.isdir', return_value=False)
    @patch('os.stat')
    def test_validate_path_not_directory(self, mock_stat, mock_isdir):
        config = SampleConfig()
        with pytest.raises(RuntimeError, match="mount failed"):
            read_from_mount_and_fallback_to_env_var("/file", "VAR", "module", "instance", config)

    @patch.dict(os.environ, {
        "VAR_MODULE_INSTANCE_USER": "env_user",
        "VAR_MODULE_INSTANCE_PASSWORD": "env_pass",
        "VAR_MODULE_INSTANCE_ENDPOINT": "env_endpoint"
    })
    def test_load_from_env_success(self):
        config = SampleConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)

        assert config.username == "env_user"
        assert config.password == "env_pass"
        assert config.endpoint == "env_endpoint"

    @patch.dict(os.environ, {"VAR_MODULE_INSTANCE_PASSWORD": "env_pass"})
    def test_load_from_env_missing_var(self):
        config = SampleConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError, match="env var failed"):
                read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_mount_success_no_env_fallback(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="mount_user").return_value,
            mock_open(read_data="mount_pass").return_value,
            mock_open(read_data="mount_endpoint").return_value
        ]

        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)

        assert config.username == "mount_user"

    @patch.dict(os.environ, {}, clear=True)
    def test_both_fail_aggregated_error(self):
        config = SampleConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError, match="mount failed.*env var failed"):
                read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_preserves_newlines(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="user\nwith\nnewlines").return_value,
            mock_open(read_data="pass").return_value,
            mock_open(read_data="endpoint").return_value
        ]

        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)

        assert config.username == "user\nwith\nnewlines"

    @patch.dict(os.environ, {"VAR_MODULE_INSTANCE_TESTFIELD": "test_value"})
    def test_case_conversion(self):
        @dataclass
        class CaseConfig:
            testfield: str = ""

        config = CaseConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)

        assert config.testfield == "test_value"

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_metadata_secret_priority(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="metadata_user").return_value,
            mock_open(read_data="field_pass").return_value,
            mock_open(read_data="field_endpoint").return_value
        ]

        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)

        assert config.username == "metadata_user"

    @patch.dict(os.environ, {
        "VAR_MODULE_MY_INSTANCE_USER": "env_user_hyphen",
        "VAR_MODULE_MY_INSTANCE_PASSWORD": "env_pass_hyphen",
        "VAR_MODULE_MY_INSTANCE_ENDPOINT": "env_endpoint_hyphen",
    })
    def test_env_instance_name_hyphen_normalization(self):
        # Given instance name with hyphen, the resolver should replace '-' with '_'
        config = SampleConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            read_from_mount_and_fallback_to_env_var(
                "/nonexistent", "VAR", "module", "my-instance", config
            )

        assert config.username == "env_user_hyphen"
        assert config.password == "env_pass_hyphen"
        assert config.endpoint == "env_endpoint_hyphen"

    @patch.dict(os.environ, {"SERVICE_BINDING_ROOT": "/custom/root"})
    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_service_binding_root_overrides_base_mount(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="u").return_value,
            mock_open(read_data="p").return_value,
            mock_open(read_data="e").return_value,
        ]
        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/etc/secrets/appfnd", "VAR", "module", "instance", config)
        first_call_path = mock_file.call_args_list[0][0][0]
        # With SERVICE_BINDING_ROOT set, flat path is tried first: $ROOT/<module>/<field>
        assert first_call_path == "/custom/root/module/user"

    @patch.dict(os.environ, {}, clear=True)
    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_default_base_mount_used_when_no_service_binding_root(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="u").return_value,
            mock_open(read_data="p").return_value,
            mock_open(read_data="e").return_value,
        ]
        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/etc/secrets/appfnd", "VAR", "module", "instance", config)
        first_call_path = mock_file.call_args_list[0][0][0]
        # Without SERVICE_BINDING_ROOT, only the legacy $ROOT/<module>/<instance>/<field> path is tried
        assert first_call_path == "/etc/secrets/appfnd/module/instance/user"

    @patch.dict(os.environ, {"SERVICE_BINDING_ROOT": "/bindings"})
    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_service_binding_root_flat_path_success(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="flat_user").return_value,
            mock_open(read_data="flat_pass").return_value,
            mock_open(read_data="flat_endpoint").return_value,
        ]
        config = SampleConfig()
        read_from_mount_and_fallback_to_env_var("/etc/secrets/appfnd", "VAR", "module", "instance", config)
        first_call_path = mock_file.call_args_list[0][0][0]
        # Flat path $ROOT/<module>/<field> is tried first
        assert first_call_path == "/bindings/module/user"
        assert config.username == "flat_user"

    @patch.dict(os.environ, {"SERVICE_BINDING_ROOT": "/bindings"})
    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    def test_service_binding_root_flat_fails_falls_back_to_module_instance(self, mock_stat, mock_isdir):
        # Flat path: directory exists but field files are not there (old AppFND structure)
        # Full path: files are present under <module>/<instance>/
        flat_not_found = FileNotFoundError("flat file missing")
        mock_file_calls = [
            flat_not_found,                                   # flat: <module>/user → not found
            mock_open(read_data="legacy_user").return_value,  # full: <module>/<instance>/user
            mock_open(read_data="legacy_pass").return_value,  # full: <module>/<instance>/password
            mock_open(read_data="legacy_ep").return_value,    # full: <module>/<instance>/endpoint
        ]
        with patch('builtins.open', side_effect=mock_file_calls):
            config = SampleConfig()
            read_from_mount_and_fallback_to_env_var("/bindings", "VAR", "module", "instance", config)

        assert config.username == "legacy_user"
        assert config.password == "legacy_pass"
        assert config.endpoint == "legacy_ep"


# ---------------------------------------------------------------------------
# Path-traversal security regression tests (HASI2026203-281)
# ---------------------------------------------------------------------------

BAD_INSTANCE_VALUES = [
    "../default",           # relative traversal (the primary attack)
    "../../etc",            # multi-hop traversal
    "/etc/passwd",          # absolute POSIX path
    "C:\\Windows",          # Windows-style absolute (backslash)
    "C:/Windows",           # Windows-style absolute (forward slash)
    "\\\\server\\share",    # UNC path
    "foo/bar",              # embedded forward separator
    "foo\\bar",             # embedded backslash
    "foo\x00bar",           # NUL byte
    "foo\x01bar",           # control character
    ".",                    # dot component
    "..",                   # parent component
    "a" * 256,              # exceeds maximum length
]

BAD_MODULE_VALUES = ["../sibling", "/abs/path", "foo/bar", ".."]

GOOD_VALUES = [
    "default",
    "hana-agent-memory",
    "aicore-instance",
    "my-tenant-us10",
    "foo.bar",
    "hr-advisor-destination-instance",
]


class TestPathComponentValidation:

    @pytest.mark.parametrize("bad", BAD_INSTANCE_VALUES)
    def test_bad_instance_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            read_from_mount_and_fallback_to_env_var(
                "/path", "VAR", "module", bad, SampleConfig()
            )

    @pytest.mark.parametrize("bad", BAD_MODULE_VALUES)
    def test_bad_module_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            read_from_mount_and_fallback_to_env_var(
                "/path", "VAR", bad, "instance", SampleConfig()
            )

    @pytest.mark.parametrize("good", GOOD_VALUES)
    def test_valid_identifier_passes_validation(self, good):
        # Validation passes; RuntimeError expected because /nonexistent doesn't exist.
        with pytest.raises(RuntimeError):
            read_from_mount_and_fallback_to_env_var(
                "/nonexistent", "VAR", "module", good, SampleConfig()
            )

    def test_rejected_value_reads_no_files_and_no_env_fallback(self, monkeypatch):
        """A traversal value must never reach the filesystem or env-var strategy."""
        opened = []
        monkeypatch.setattr("builtins.open", lambda *a, **kw: opened.append(a))
        monkeypatch.setenv("VAR_MODULE_X_USER", "leak")
        with pytest.raises(ValueError):
            read_from_mount_and_fallback_to_env_var(
                "/path", "VAR", "module", "../x", SampleConfig()
            )
        assert opened == [], "bad instance must not open any file"

    def test_symlink_escaping_base_is_rejected(self, tmp_path):
        """A symlink pointing outside the trusted root must be rejected."""
        base = tmp_path / "appfnd"
        (base / "mod").mkdir(parents=True)
        outside = tmp_path / "outside"
        outside.mkdir()
        (base / "mod" / "inst").symlink_to(outside, target_is_directory=True)
        # "inst" is a valid single-component name, passes _validate_path_component,
        # but _assert_within_base detects the symlink escapes and raises ValueError
        # which is aggregated into RuntimeError by read_from_mount_and_fallback_to_env_var.
        with pytest.raises(RuntimeError, match="escapes trusted root"):
            read_from_mount_and_fallback_to_env_var(
                str(base), "VAR", "mod", "inst", SampleConfig()
            )
