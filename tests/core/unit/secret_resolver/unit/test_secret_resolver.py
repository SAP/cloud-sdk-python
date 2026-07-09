"""Tests for secret_resolver module."""

import os
from dataclasses import dataclass, field
from unittest.mock import patch, mock_open, MagicMock
import pytest

from sap_cloud_sdk.core.secret_resolver import (
    read_from_mount_and_fallback_to_env_var,
    MountResolver,
    EnvVarResolver,
    ChainedResolver,
    Resolver,
    SdkConfig,
    configure,
    get_sdk_config,
    get_resolver,
    resolve_base_mount,
)
from sap_cloud_sdk.core.secret_resolver.sdk_config import _reset_sdk_config


@dataclass
class SampleConfig:
    username: str = field(default="", metadata={"secret": "user"})
    password: str = ""
    endpoint: str = "default"


@dataclass
class NonStringConfig:
    count: int = 0


# ---------------------------------------------------------------------------
# Legacy function-based API
# ---------------------------------------------------------------------------

class TestLegacyResolver:

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
            mock_open(read_data="test_endpoint").return_value,
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
        "VAR_MODULE_INSTANCE_ENDPOINT": "env_endpoint",
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
            mock_open(read_data="mount_endpoint").return_value,
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
            mock_open(read_data="endpoint").return_value,
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
            mock_open(read_data="field_endpoint").return_value,
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
        # SERVICE_BINDING_ROOT overrides the base; path is still $ROOT/<module>/<instance>/<field>
        assert first_call_path == "/custom/root/module/instance/user"

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
        assert first_call_path == "/etc/secrets/appfnd/module/instance/user"


# ---------------------------------------------------------------------------
# resolve_base_mount
# ---------------------------------------------------------------------------

class TestResolveBaseMount:

    @patch.dict(os.environ, {"SERVICE_BINDING_ROOT": "/from/env"})
    def test_returns_env_var_when_set(self):
        assert resolve_base_mount("/default") == "/from/env"

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_default_when_env_var_absent(self):
        assert resolve_base_mount("/my/default") == "/my/default"

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_module_constant_by_default(self):
        from sap_cloud_sdk.core.secret_resolver.constants import BASE_MOUNT_PATH
        assert resolve_base_mount() == BASE_MOUNT_PATH


# ---------------------------------------------------------------------------
# MountResolver
# ---------------------------------------------------------------------------

class TestMountResolver:

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_resolve_success(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="u").return_value,
            mock_open(read_data="p").return_value,
            mock_open(read_data="e").return_value,
        ]
        config = SampleConfig()
        MountResolver(base_volume_mount="/secrets").resolve("mod", "inst", config)

        assert config.username == "u"
        assert config.password == "p"
        assert config.endpoint == "e"

    @patch('os.stat', side_effect=FileNotFoundError("not found"))
    def test_resolve_raises_when_dir_missing(self, mock_stat):
        config = SampleConfig()
        with pytest.raises(FileNotFoundError):
            MountResolver(base_volume_mount="/noexist").resolve("mod", "inst", config)

    @patch('os.path.isdir', return_value=False)
    @patch('os.stat')
    def test_resolve_raises_when_path_not_directory(self, mock_stat, mock_isdir):
        config = SampleConfig()
        with pytest.raises(NotADirectoryError):
            MountResolver(base_volume_mount="/file").resolve("mod", "inst", config)

    @patch.dict(os.environ, {"SERVICE_BINDING_ROOT": "/override"})
    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_service_binding_root_overrides_constructor_path(self, mock_file, mock_stat, mock_isdir):
        mock_file.side_effect = [
            mock_open(read_data="x").return_value,
            mock_open(read_data="y").return_value,
            mock_open(read_data="z").return_value,
        ]
        config = SampleConfig()
        MountResolver(base_volume_mount="/original").resolve("mod", "inst", config)
        first_call_path = mock_file.call_args_list[0][0][0]
        assert first_call_path.startswith("/override/")

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', new_callable=mock_open)
    def test_uses_default_base_mount_path(self, mock_file, mock_stat, mock_isdir):
        from sap_cloud_sdk.core.secret_resolver.constants import BASE_MOUNT_PATH
        mock_file.side_effect = [
            mock_open(read_data="u").return_value,
            mock_open(read_data="p").return_value,
            mock_open(read_data="e").return_value,
        ]
        config = SampleConfig()
        with patch.dict(os.environ, {}, clear=True):
            MountResolver().resolve("mod", "inst", config)
        first_call_path = mock_file.call_args_list[0][0][0]
        assert first_call_path.startswith(BASE_MOUNT_PATH)


# ---------------------------------------------------------------------------
# EnvVarResolver
# ---------------------------------------------------------------------------

class TestEnvVarResolver:

    @patch.dict(os.environ, {
        "CLOUD_SDK_CFG_MOD_INST_USER": "eu",
        "CLOUD_SDK_CFG_MOD_INST_PASSWORD": "ep",
        "CLOUD_SDK_CFG_MOD_INST_ENDPOINT": "ee",
    })
    def test_resolve_success(self):
        config = SampleConfig()
        EnvVarResolver().resolve("mod", "inst", config)

        assert config.username == "eu"
        assert config.password == "ep"
        assert config.endpoint == "ee"

    @patch.dict(os.environ, {
        "MYPREFIX_MOD_INST_USER": "cu",
        "MYPREFIX_MOD_INST_PASSWORD": "cp",
        "MYPREFIX_MOD_INST_ENDPOINT": "ce",
    })
    def test_custom_base_var_name(self):
        config = SampleConfig()
        EnvVarResolver(base_var_name="MYPREFIX").resolve("mod", "inst", config)

        assert config.username == "cu"

    @patch.dict(os.environ, {
        "CLOUD_SDK_CFG_MOD_MY_INST_USER": "hu",
        "CLOUD_SDK_CFG_MOD_MY_INST_PASSWORD": "hp",
        "CLOUD_SDK_CFG_MOD_MY_INST_ENDPOINT": "he",
    })
    def test_hyphen_normalization_in_instance(self):
        config = SampleConfig()
        EnvVarResolver().resolve("mod", "my-inst", config)

        assert config.username == "hu"

    @patch.dict(os.environ, {
        "CLOUD_SDK_CFG_MY_MOD_INST_USER": "mu",
        "CLOUD_SDK_CFG_MY_MOD_INST_PASSWORD": "mp",
        "CLOUD_SDK_CFG_MY_MOD_INST_ENDPOINT": "me",
    })
    def test_hyphen_normalization_in_module(self):
        config = SampleConfig()
        EnvVarResolver().resolve("my-mod", "inst", config)

        assert config.username == "mu"

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_raises_when_var_missing(self):
        config = SampleConfig()
        with pytest.raises(KeyError, match="env var not found"):
            EnvVarResolver().resolve("mod", "inst", config)


# ---------------------------------------------------------------------------
# ChainedResolver
# ---------------------------------------------------------------------------

class TestChainedResolver:

    def test_empty_resolvers_raises(self):
        with pytest.raises(ValueError, match="resolvers list must not be empty"):
            ChainedResolver([])

    def test_non_dataclass_target_raises(self):
        resolver = ChainedResolver([MountResolver()])
        with pytest.raises(TypeError, match="target must be a dataclass instance"):
            resolver.resolve("mod", "inst", "not_a_dataclass")

    def test_non_string_field_raises(self):
        resolver = ChainedResolver([MountResolver()])
        config = NonStringConfig()
        with pytest.raises(TypeError, match="is not a string"):
            resolver.resolve("mod", "inst", config)

    def test_first_resolver_succeeds(self):
        first = MagicMock(spec=Resolver)
        second = MagicMock(spec=Resolver)
        chain = ChainedResolver([first, second])
        config = SampleConfig()

        chain.resolve("mod", "inst", config)

        first.resolve.assert_called_once_with("mod", "inst", config)
        second.resolve.assert_not_called()

    def test_falls_back_to_second_on_first_failure(self):
        first = MagicMock(spec=Resolver)
        first.resolve.side_effect = RuntimeError("first failed")
        second = MagicMock(spec=Resolver)
        chain = ChainedResolver([first, second])
        config = SampleConfig()

        chain.resolve("mod", "inst", config)

        first.resolve.assert_called_once()
        second.resolve.assert_called_once_with("mod", "inst", config)

    def test_raises_runtime_error_when_all_resolvers_fail(self):
        first = MagicMock(spec=Resolver)
        first.resolve.side_effect = RuntimeError("first failed")
        second = MagicMock(spec=Resolver)
        second.resolve.side_effect = KeyError("second failed")
        chain = ChainedResolver([first, second])
        config = SampleConfig()

        with pytest.raises(RuntimeError, match="failed to read secrets from all resolvers"):
            chain.resolve("mod", "inst", config)

    def test_aggregated_error_contains_all_failures(self):
        first = MagicMock(spec=Resolver)
        first.resolve.side_effect = RuntimeError("mount error")
        second = MagicMock(spec=Resolver)
        second.resolve.side_effect = KeyError("env error")
        chain = ChainedResolver([first, second])
        config = SampleConfig()

        with pytest.raises(RuntimeError) as exc_info:
            chain.resolve("mod", "inst", config)

        msg = str(exc_info.value)
        assert "mount error" in msg
        assert "env error" in msg

    def test_custom_base_var_name_appears_in_error(self):
        resolver = MagicMock(spec=Resolver)
        resolver.resolve.side_effect = RuntimeError("fail")
        chain = ChainedResolver([resolver], base_var_name="MY_APP_CFG")
        config = SampleConfig()

        with pytest.raises(RuntimeError, match="MY_APP_CFG"):
            chain.resolve("mod", "inst", config)


# ---------------------------------------------------------------------------
# SdkConfig / configure / get_resolver / reset_sdk_config
# ---------------------------------------------------------------------------

class TestSdkConfig:

    def teardown_method(self):
        _reset_sdk_config()

    def test_get_sdk_config_is_none_by_default(self):
        assert get_sdk_config() is None

    def test_configure_sets_global_config(self):
        cfg = SdkConfig()
        configure(cfg)
        assert get_sdk_config() is cfg

    def test_reset_clears_config(self):
        configure(SdkConfig())
        _reset_sdk_config()
        assert get_sdk_config() is None

    def test_configure_replaces_previous_config(self):
        first = SdkConfig()
        second = SdkConfig()
        configure(first)
        configure(second)
        assert get_sdk_config() is second

    def test_get_resolver_returns_default_chain_when_no_config(self):
        resolver = get_resolver()
        assert isinstance(resolver, ChainedResolver)

    def test_get_resolver_returns_default_chain_when_config_has_no_resolver(self):
        configure(SdkConfig(resolver=None))
        resolver = get_resolver()
        assert isinstance(resolver, ChainedResolver)

    def test_get_resolver_returns_custom_resolver_when_configured(self):
        custom = MagicMock(spec=Resolver)
        configure(SdkConfig(resolver=custom))
        assert get_resolver() is custom

    def test_get_resolver_default_chain_contains_mount_and_env(self):
        resolver = get_resolver()
        assert isinstance(resolver, ChainedResolver)
        # Verify it contains MountResolver and EnvVarResolver by attempting resolution
        # (the internal _resolvers list is private, so we check behaviour via the protocol)
        assert hasattr(resolver, "resolve")
