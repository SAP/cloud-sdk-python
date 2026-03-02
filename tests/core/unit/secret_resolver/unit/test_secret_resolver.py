"""Tests for secret_resolver module."""

import os
from dataclasses import dataclass, field
from unittest.mock import patch, mock_open
import pytest

from cloud_sdk_python.core.secret_resolver import read_from_mount_and_fallback_to_env_var


@dataclass
class TestConfig:
    username: str = field(default="", metadata={"secret": "user"})
    password: str = ""
    endpoint: str = "default"


@dataclass 
class NonStringConfig:
    count: int = 0


class TestSecretResolver:

    def test_validate_inputs_empty_module(self):
        config = TestConfig()
        with pytest.raises(ValueError, match="module name cannot be empty"):
            read_from_mount_and_fallback_to_env_var("/path", "VAR", "", "instance", config)

    def test_validate_inputs_empty_instance(self):
        config = TestConfig()
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
        
        config = TestConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)
        
        assert config.username == "test_user"
        assert config.password == "test_pass"
        assert config.endpoint == "test_endpoint"

    @patch('os.path.isdir', return_value=True)
    @patch('os.stat')
    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_load_from_mount_file_not_found(self, mock_file, mock_stat, mock_isdir):
        config = TestConfig()
        with pytest.raises(RuntimeError, match="failed to read secrets.*failed to read secret file"):
            read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)

    @patch('os.stat', side_effect=FileNotFoundError("Path not found"))
    def test_validate_path_not_exists(self, mock_stat):
        config = TestConfig()
        with pytest.raises(RuntimeError, match="mount failed"):
            read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)

    @patch('os.path.isdir', return_value=False)
    @patch('os.stat')
    def test_validate_path_not_directory(self, mock_stat, mock_isdir):
        config = TestConfig()
        with pytest.raises(RuntimeError, match="mount failed"):
            read_from_mount_and_fallback_to_env_var("/file", "VAR", "module", "instance", config)

    @patch.dict(os.environ, {
        "VAR_MODULE_INSTANCE_USER": "env_user",
        "VAR_MODULE_INSTANCE_PASSWORD": "env_pass", 
        "VAR_MODULE_INSTANCE_ENDPOINT": "env_endpoint"
    })
    def test_load_from_env_success(self):
        config = TestConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            read_from_mount_and_fallback_to_env_var("/nonexistent", "VAR", "module", "instance", config)
        
        assert config.username == "env_user"
        assert config.password == "env_pass"
        assert config.endpoint == "env_endpoint"

    @patch.dict(os.environ, {"VAR_MODULE_INSTANCE_PASSWORD": "env_pass"})
    def test_load_from_env_missing_var(self):
        config = TestConfig()
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
        
        config = TestConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)
        
        assert config.username == "mount_user"

    @patch.dict(os.environ, {}, clear=True)
    def test_both_fail_aggregated_error(self):
        config = TestConfig()
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
        
        config = TestConfig()
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
        
        config = TestConfig()
        read_from_mount_and_fallback_to_env_var("/secrets", "VAR", "module", "instance", config)
        
        assert config.username == "metadata_user"

    @patch.dict(os.environ, {
        "VAR_MODULE_MY_INSTANCE_USER": "env_user_hyphen",
        "VAR_MODULE_MY_INSTANCE_PASSWORD": "env_pass_hyphen",
        "VAR_MODULE_MY_INSTANCE_ENDPOINT": "env_endpoint_hyphen",
    })
    def test_env_instance_name_hyphen_normalization(self):
        # Given instance name with hyphen, the resolver should replace '-' with '_'
        config = TestConfig()
        with patch('os.path.isdir', return_value=False), \
             patch('os.stat', side_effect=FileNotFoundError()):
            read_from_mount_and_fallback_to_env_var(
                "/nonexistent", "VAR", "module", "my-instance", config
            )

        assert config.username == "env_user_hyphen"
        assert config.password == "env_pass_hyphen"
        assert config.endpoint == "env_endpoint_hyphen"
