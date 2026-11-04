"""Tests for secret_resolver module."""

import os
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import patch, mock_open
import pytest

from sap_cloud_sdk.core.secret_resolver import read_from_mount_and_fallback_to_env_var
from sap_cloud_sdk.core.secret_resolver.resolver import _get_field_map


@dataclass
class SampleConfig:
    username: str = field(default="", metadata={"secret": "user"})
    password: str = ""
    endpoint: str = "default"


@dataclass
class OptionalFieldConfig:
    required_field: str = ""
    optional_field: Optional[str] = None


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


class TestOptionalFields:
    """Tests for Optional[str] field support — optionality declared via type annotation."""

    @patch.dict(os.environ, {"VAR_MODULE_INSTANCE_REQUIRED_FIELD": "req_value"})
    def test_optional_env_var_absent_keeps_default(self):
        """Optional env var missing is silently skipped; field keeps its default (None)."""
        config = OptionalFieldConfig()
        with (
            patch("os.path.isdir", return_value=False),
            patch("os.stat", side_effect=FileNotFoundError()),
        ):
            read_from_mount_and_fallback_to_env_var(
                "/nonexistent", "VAR", "module", "instance", config
            )

        assert config.required_field == "req_value"
        assert config.optional_field is None  # default preserved

    @patch.dict(os.environ, {
        "VAR_MODULE_INSTANCE_REQUIRED_FIELD": "req_value",
        "VAR_MODULE_INSTANCE_OPTIONAL_FIELD": "opt_value",
    })
    def test_optional_env_var_present_is_loaded(self):
        """Optional env var that IS present is loaded normally."""
        config = OptionalFieldConfig()
        with (
            patch("os.path.isdir", return_value=False),
            patch("os.stat", side_effect=FileNotFoundError()),
        ):
            read_from_mount_and_fallback_to_env_var(
                "/nonexistent", "VAR", "module", "instance", config
            )

        assert config.required_field == "req_value"
        assert config.optional_field == "opt_value"

    @patch.dict(os.environ, {}, clear=True)
    def test_required_env_var_absent_still_raises(self):
        """Missing required field still raises RuntimeError even when optional field is absent."""
        config = OptionalFieldConfig()
        with (
            patch("os.path.isdir", return_value=False),
            patch("os.stat", side_effect=FileNotFoundError()),
        ):
            with pytest.raises(RuntimeError, match="env var failed"):
                read_from_mount_and_fallback_to_env_var(
                    "/nonexistent", "VAR", "module", "instance", config
                )

    @patch("os.path.isdir", return_value=True)
    @patch("os.stat")
    def test_optional_mount_file_absent_keeps_default(self, mock_stat, mock_isdir):
        """Optional secret file missing from mount is silently skipped."""
        file_side_effects = [
            mock_open(read_data="req_value").return_value,  # required_field file found
            FileNotFoundError("optional file not found"),    # optional_field file missing
        ]
        config = OptionalFieldConfig()
        with patch("builtins.open", side_effect=file_side_effects):
            read_from_mount_and_fallback_to_env_var(
                "/secrets", "VAR", "module", "instance", config
            )

        assert config.required_field == "req_value"
        assert config.optional_field is None  # default preserved

    @patch("os.path.isdir", return_value=True)
    @patch("os.stat")
    def test_required_mount_file_absent_raises(self, mock_stat, mock_isdir):
        """Missing required secret file still raises FileNotFoundError."""
        config = OptionalFieldConfig()
        with patch("builtins.open", side_effect=FileNotFoundError("file not found")):
            with pytest.raises(
                RuntimeError,
                match="failed to read secrets.*failed to read secret file",
            ):
                read_from_mount_and_fallback_to_env_var(
                    "/secrets", "VAR", "module", "instance", config
                )


# ── TestGetFieldMap ───────────────────────────────────────────────────────────


class TestGetFieldMap:
    """Direct unit tests for _get_field_map() — the internal that drives optionality detection.

    These pin down the exact contract so a refactor can't silently change behaviour:
      - ``str`` fields are required (is_optional=False)
      - ``Optional[str]`` fields are optional (is_optional=True)
      - Non-string fields raise TypeError
      - Optionality comes from the type annotation, NOT from field.metadata
    """

    def test_str_field_is_required(self):
        @dataclass
        class Config:
            host: str = ""

        result = _get_field_map(Config())
        assert result["host"][2] is False  # (name, type, is_optional)

    def test_optional_str_field_is_optional(self):
        @dataclass
        class Config:
            token: Optional[str] = None

        result = _get_field_map(Config())
        assert result["token"][2] is True

    def test_mixed_fields_correct_flags(self):
        @dataclass
        class Config:
            required: str = ""
            optional: Optional[str] = None

        result = _get_field_map(Config())
        assert result["required"][2] is False
        assert result["optional"][2] is True

    def test_non_string_field_raises_type_error(self):
        @dataclass
        class Config:
            count: int = 0

        with pytest.raises(TypeError, match="is not a string"):
            _get_field_map(Config())

    def test_metadata_secret_key_still_respected(self):
        """field(metadata={"secret": "..."}) renames the lookup key; Optional still works."""
        @dataclass
        class Config:
            api_token: Optional[str] = field(default=None, metadata={"secret": "token"})

        result = _get_field_map(Config())
        # Key is the metadata "secret" value, not the field name
        assert "token" in result
        assert result["token"][0] == "api_token"   # attribute name
        assert result["token"][2] is True           # is_optional

    def test_non_dataclass_raises_type_error(self):
        with pytest.raises(TypeError, match="target must be a dataclass instance"):
            _get_field_map("not_a_dataclass")

    def test_dataclass_class_not_instance_raises(self):
        with pytest.raises(TypeError, match="target must be a dataclass instance"):
            _get_field_map(OptionalFieldConfig)  # class, not instance

    def test_metadata_optional_true_without_optional_type_is_required(self):
        """Confirms the old metadata={"optional": True} pattern is no longer honoured.

        After the migration to Optional[str], a plain ``str`` field annotated with
        ``field(metadata={"optional": True})`` is treated as REQUIRED — the type
        annotation is the source of truth, not the metadata.  Any pre-migration
        usage of the metadata pattern must be updated to ``Optional[str]``.
        """
        @dataclass
        class OldStyleConfig:
            legacy: str = field(default="", metadata={"optional": True})

        result = _get_field_map(OldStyleConfig())
        # is_optional is False because the annotation is str, not Optional[str]
        assert result["legacy"][2] is False

    def test_pep563_annotations_resolved_correctly(self):
        """_get_field_map() works when the dataclass module uses PEP 563 (from __future__ import annotations).

        Under PEP 563, class __annotations__ stores raw strings like "Optional[str]"
        instead of type objects.  f.type would return a string, making ``f.type is str``
        and ``get_origin(f.type)`` both return wrong results.  Using get_type_hints()
        resolves the strings to real objects so Optional[str] detection stays correct.
        """
        from tests.core.unit.secret_resolver.unit._future_annotations_fixture import PEP563Config

        # Confirm PEP 563 effect: annotations are strings in the class dict.
        raw = PEP563Config.__annotations__
        assert isinstance(raw["required"], str), "PEP 563 not active — test invalid"
        assert isinstance(raw["optional"], str), "PEP 563 not active — test invalid"

        result = _get_field_map(PEP563Config())
        assert result["required"][2] is False, "required str field should be required"
        assert result["optional"][2] is True,  "Optional[str] field should be optional"
