"""Unit tests for AI Core configuration module."""

import json
import os
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from sap_cloud_sdk.aicore import (
    _get_aicore_base_url,
    _get_secret,
    set_aicore_config,
)


class TestGetSecret:
    """Test suite for _get_secret function."""

    def test_get_secret_from_file_success(self):
        """Test successfully reading secret from file."""
        mock_file_content = "secret-value-from-file"
        instance_name = "test-instance"
        env_var_name = "TEST_SECRET"
        file_name = "test-file"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_secret(env_var_name, file_name, instance_name=instance_name)

            assert result == mock_file_content

    def test_get_secret_from_file_with_whitespace(self):
        """Test reading secret from file strips whitespace."""
        mock_file_content = "  secret-value  \n"
        env_var_name = "TEST_SECRET"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_secret(env_var_name)

            assert result == "secret-value"

    def test_get_secret_from_file_empty_falls_back_to_env(self):
        """Test that empty file content falls back to environment variable."""
        env_var_name = "TEST_SECRET"
        env_value = "env-secret-value"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="   \n")
        ), patch.dict("os.environ", {env_var_name: env_value}, clear=True):
            result = _get_secret(env_var_name)

            assert result == env_value

    def test_get_secret_from_env_when_file_not_exists(self):
        """Test falling back to environment variable when file doesn't exist."""
        env_var_name = "TEST_SECRET"
        env_value = "env-secret-value"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {env_var_name: env_value}, clear=True
        ):
            result = _get_secret(env_var_name)

            assert result == env_value

    def test_get_secret_file_read_exception_falls_back_to_env(self):
        """Test that file read exceptions fall back to environment variable."""
        env_var_name = "TEST_SECRET"
        env_value = "env-secret-value"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=IOError("Permission denied")
        ), patch.dict("os.environ", {env_var_name: env_value}, clear=True):
            result = _get_secret(env_var_name)

            assert result == env_value

    def test_get_secret_uses_default_when_no_source(self):
        """Test using default value when neither file nor env var exists."""
        env_var_name = "TEST_SECRET"
        default_value = "default-secret"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {}, clear=True
        ):
            result = _get_secret(env_var_name, default=default_value)

            assert result == default_value

    def test_get_secret_uses_empty_default_when_not_specified(self):
        """Test empty string default when no default specified."""
        env_var_name = "TEST_SECRET"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {}, clear=True
        ):
            result = _get_secret(env_var_name)

            assert result == ""

    def test_get_secret_uses_env_var_name_as_file_name_when_not_provided(self):
        """Test that env_var_name is used as file_name when file_name is None."""
        env_var_name = "TEST_SECRET"
        mock_file_content = "secret-from-file"

        with patch("os.path.exists", return_value=True) as mock_exists, patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_secret(env_var_name)  # file_name defaults to None

            # Verify the file path uses env_var_name
            expected_path = f"/etc/secrets/appfnd/aicore/aicore-instance/{env_var_name}"
            mock_exists.assert_called_with(expected_path)
            assert result == mock_file_content

    def test_get_secret_custom_instance_name(self):
        """Test using custom instance_name parameter."""
        env_var_name = "TEST_SECRET"
        file_name = "test-file"
        instance_name = "custom-instance"
        mock_file_content = "secret-value"

        with patch("os.path.exists", return_value=True) as mock_exists, patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_secret(
                env_var_name, file_name, instance_name=instance_name
            )

            expected_path = f"/etc/secrets/appfnd/aicore/{instance_name}/{file_name}"
            mock_exists.assert_called_with(expected_path)
            assert result == mock_file_content

    def test_get_secret_logs_info_when_loaded_from_file(self):
        """Test that info is logged when secret is loaded from file."""
        env_var_name = "TEST_SECRET"
        mock_file_content = "secret-value"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True), patch(
            "sap_cloud_sdk.aicore.logger"
        ) as mock_logger:
            _get_secret(env_var_name)

            mock_logger.info.assert_called()
            assert any(
                env_var_name in str(call) for call in mock_logger.info.call_args_list
            )

    def test_get_secret_logs_warning_when_file_read_fails(self):
        """Test that warning is logged when file read fails."""
        env_var_name = "TEST_SECRET"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=IOError("Permission denied")
        ), patch.dict("os.environ", {}, clear=True), patch(
            "sap_cloud_sdk.aicore.logger"
        ) as mock_logger:
            _get_secret(env_var_name)

            mock_logger.warning.assert_called()

    def test_get_secret_logs_info_when_loaded_from_env(self):
        """Test that info is logged when secret is loaded from environment."""
        env_var_name = "TEST_SECRET"
        env_value = "env-value"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {env_var_name: env_value}, clear=True
        ), patch("sap_cloud_sdk.aicore.logger") as mock_logger:
            _get_secret(env_var_name)

            mock_logger.info.assert_called()

    def test_get_secret_logs_warning_when_no_value_found(self):
        """Test that warning is logged when no value is found."""
        env_var_name = "TEST_SECRET"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {}, clear=True
        ), patch("sap_cloud_sdk.aicore.logger") as mock_logger:
            _get_secret(env_var_name)

            mock_logger.warning.assert_called()


class TestGetAICoreBaseUrl:
    """Test suite for _get_aicore_base_url function."""

    def test_get_base_url_from_serviceurls_file_success(self):
        """Test successfully reading base URL from serviceurls JSON file."""
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = json.dumps(serviceurls_data)

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_aicore_base_url()

            assert result == "https://api.example.com"

    def test_get_base_url_from_serviceurls_strips_whitespace(self):
        """Test that base URL from serviceurls strips whitespace."""
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = f"  {json.dumps(serviceurls_data)}  \n"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_aicore_base_url()

            assert result == "https://api.example.com"

    def test_get_base_url_from_serviceurls_missing_key(self):
        """Test handling serviceurls file without AI_API_URL key."""
        serviceurls_data = {"OTHER_KEY": "value"}
        mock_file_content = json.dumps(serviceurls_data)

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {"AICORE_BASE_URL": "https://env.example.com"}):
            result = _get_aicore_base_url()

            assert result == "https://env.example.com"

    def test_get_base_url_from_serviceurls_empty_value(self):
        """Test handling serviceurls file with empty AI_API_URL value."""
        serviceurls_data = {"AI_API_URL": ""}
        mock_file_content = json.dumps(serviceurls_data)

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {"AICORE_BASE_URL": "https://env.example.com"}):
            result = _get_aicore_base_url()

            assert result == "https://env.example.com"

    def test_get_base_url_from_serviceurls_invalid_json(self):
        """Test handling invalid JSON in serviceurls file."""
        mock_file_content = "{ invalid json }"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {"AICORE_BASE_URL": "https://env.example.com"}):
            result = _get_aicore_base_url()

            assert result == "https://env.example.com"

    def test_get_base_url_from_env_when_file_not_exists(self):
        """Test falling back to environment variable when serviceurls file doesn't exist."""
        env_value = "https://env.example.com"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {"AICORE_BASE_URL": env_value}
        ):
            result = _get_aicore_base_url()

            assert result == env_value

    def test_get_base_url_returns_empty_when_no_source(self):
        """Test returning empty string when neither file nor env var exists."""
        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {}, clear=True
        ):
            result = _get_aicore_base_url()

            assert result == ""

    def test_get_base_url_custom_instance_name(self):
        """Test using custom instance_name parameter."""
        instance_name = "custom-instance"
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = json.dumps(serviceurls_data)

        with patch("os.path.exists", return_value=True) as mock_exists, patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True):
            result = _get_aicore_base_url(instance_name=instance_name)

            expected_path = f"/etc/secrets/appfnd/aicore/{instance_name}/serviceurls"
            mock_exists.assert_called_with(expected_path)
            assert result == "https://api.example.com"

    def test_get_base_url_file_read_exception_falls_back_to_env(self):
        """Test that file read exceptions fall back to environment variable."""
        env_value = "https://env.example.com"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=IOError("Permission denied")
        ), patch.dict("os.environ", {"AICORE_BASE_URL": env_value}):
            result = _get_aicore_base_url()

            assert result == env_value

    def test_get_base_url_logs_info_when_loaded_from_file(self):
        """Test that info is logged when base URL is loaded from file."""
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = json.dumps(serviceurls_data)

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=mock_file_content)
        ), patch.dict("os.environ", {}, clear=True), patch(
            "sap_cloud_sdk.aicore.logger"
        ) as mock_logger:
            _get_aicore_base_url()

            mock_logger.info.assert_called()

    def test_get_base_url_logs_warning_when_file_read_fails(self):
        """Test that warning is logged when file read fails."""
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=IOError("Permission denied")
        ), patch.dict("os.environ", {}, clear=True), patch(
            "sap_cloud_sdk.aicore.logger"
        ) as mock_logger:
            _get_aicore_base_url()

            mock_logger.warning.assert_called()

    def test_get_base_url_logs_info_when_loaded_from_env(self):
        """Test that info is logged when base URL is loaded from environment."""
        env_value = "https://env.example.com"

        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {"AICORE_BASE_URL": env_value}
        ), patch("sap_cloud_sdk.aicore.logger") as mock_logger:
            _get_aicore_base_url()

            mock_logger.info.assert_called()

    def test_get_base_url_logs_warning_when_no_value_found(self):
        """Test that warning is logged when no value is found."""
        with patch("os.path.exists", return_value=False), patch.dict(
            "os.environ", {}, clear=True
        ), patch("sap_cloud_sdk.aicore.logger") as mock_logger:
            _get_aicore_base_url()

            mock_logger.warning.assert_called()


class TestSetAICoreConfig:
    """Test suite for set_aicore_config function."""

    def test_set_config_loads_all_secrets_successfully(self):
        """Test successfully loading and setting all AI Core configuration."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            # Setup mock returns
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-client-secret",
                "AICORE_AUTH_URL": "https://auth.example.com",
                "AICORE_RESOURCE_GROUP": "test-group",
            }.get(name, default)
            mock_get_base_url.return_value = "https://api.example.com"

            set_aicore_config()

            # Verify all environment variables are set
            assert os.environ["AICORE_CLIENT_ID"] == "test-client-id"
            assert os.environ["AICORE_CLIENT_SECRET"] == "test-client-secret"
            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )
            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"
            assert os.environ["AICORE_RESOURCE_GROUP"] == "test-group"

    def test_set_config_appends_oauth_token_suffix(self):
        """Test that /oauth/token suffix is appended to auth URL."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com",
                "AICORE_RESOURCE_GROUP": "default",
            }.get(name, default)
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )

    def test_set_config_does_not_duplicate_oauth_token_suffix(self):
        """Test that /oauth/token suffix is not duplicated if already present."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com/oauth/token",
                "AICORE_RESOURCE_GROUP": "default",
            }.get(name, default)
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )

    def test_set_config_strips_trailing_slash_before_adding_oauth_token(self):
        """Test that trailing slash is removed before appending /oauth/token."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com/",
                "AICORE_RESOURCE_GROUP": "default",
            }.get(name, default)
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )

    def test_set_config_appends_v2_suffix_to_base_url(self):
        """Test that /v2 suffix is appended to base URL."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com",
                "AICORE_RESOURCE_GROUP": "default",
            }.get(name, default)
            mock_get_base_url.return_value = "https://api.example.com"

            set_aicore_config()

            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_set_config_does_not_duplicate_v2_suffix(self):
        """Test that /v2 suffix is not duplicated if already present."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com",
                "AICORE_RESOURCE_GROUP": "default",
            }.get(name, default)
            mock_get_base_url.return_value = "https://api.example.com/v2"

            set_aicore_config()

            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_set_config_strips_trailing_slash_before_adding_v2(self):
        """Test that trailing slash is removed before appending /v2."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com",
                "AICORE_RESOURCE_GROUP": "default",
            }.get(name, default)
            mock_get_base_url.return_value = "https://api.example.com/"

            set_aicore_config()

            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_set_config_does_not_set_empty_values(self):
        """Test that empty values are not set as environment variables."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "",
                "AICORE_CLIENT_SECRET": "",
                "AICORE_AUTH_URL": "",
                "AICORE_RESOURCE_GROUP": "test-group",
            }.get(name, default)
            mock_get_base_url.return_value = ""

            set_aicore_config()

            # Only non-empty value should be set
            assert "AICORE_CLIENT_ID" not in os.environ
            assert "AICORE_CLIENT_SECRET" not in os.environ
            assert "AICORE_AUTH_URL" not in os.environ
            assert "AICORE_BASE_URL" not in os.environ
            assert os.environ["AICORE_RESOURCE_GROUP"] == "test-group"

    def test_set_config_uses_default_resource_group(self):
        """Test that default resource group is used when not provided."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": (
                default if name == "AICORE_RESOURCE_GROUP" else ""
            )
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert os.environ["AICORE_RESOURCE_GROUP"] == "default"

    def test_set_config_custom_instance_name(self):
        """Test using custom instance_name parameter."""
        instance_name = "custom-instance"

        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.return_value = ""
            mock_get_base_url.return_value = ""

            set_aicore_config(instance_name=instance_name)

            # Verify instance_name was passed to _get_aicore_base_url
            mock_get_base_url.assert_called_with(instance_name)

            # Verify instance_name was passed to all _get_secret calls
            for call in mock_get_secret.call_args_list:
                assert call[1].get("instance_name") == instance_name, (
                    f"_get_secret call for {call[0][0]} missing instance_name={instance_name}"
                )

    def test_set_config_calls_get_secret_with_correct_parameters(self):
        """Test that _get_secret is called with correct parameters for each secret."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True):
            mock_get_secret.return_value = ""
            mock_get_base_url.return_value = ""

            set_aicore_config()

            default_instance = "aicore-instance"
            # Verify _get_secret was called with correct parameters including instance_name
            calls = mock_get_secret.call_args_list
            assert any(
                call[0][0] == "AICORE_CLIENT_ID"
                and call[0][1] == "clientid"
                and call[1].get("instance_name") == default_instance
                for call in calls
            )
            assert any(
                call[0][0] == "AICORE_CLIENT_SECRET"
                and call[0][1] == "clientsecret"
                and call[1].get("instance_name") == default_instance
                for call in calls
            )
            assert any(
                call[0][0] == "AICORE_AUTH_URL"
                and call[0][1] == "url"
                and call[1].get("instance_name") == default_instance
                for call in calls
            )
            assert any(
                call[0][0] == "AICORE_RESOURCE_GROUP"
                and call[1].get("default") == "default"
                and call[1].get("instance_name") == default_instance
                for call in calls
            )

    def test_set_config_logs_configuration(self):
        """Test that configuration completion is logged (excluding sensitive information)."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True), patch(
            "sap_cloud_sdk.aicore.logger"
        ) as mock_logger:
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": {
                "AICORE_CLIENT_ID": "test-client-id",
                "AICORE_CLIENT_SECRET": "test-secret",
                "AICORE_AUTH_URL": "https://auth.example.com",
                "AICORE_RESOURCE_GROUP": "test-group",
            }.get(name, default)
            mock_get_base_url.return_value = "https://api.example.com"

            set_aicore_config()

            # Verify info logging was called with success message
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("AI Core configuration has been set successfully" in call for call in info_calls)

            # Verify sensitive info is not logged
            all_log_calls = str(mock_logger.mock_calls)
            assert "test-client-id" not in all_log_calls
            assert "test-secret" not in all_log_calls

    def test_set_config_decorated_with_record_metrics(self):
        """Test that set_aicore_config is decorated with @record_metrics."""
        with patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret, patch(
            "sap_cloud_sdk.aicore._get_aicore_base_url"
        ) as mock_get_base_url, patch.dict("os.environ", {}, clear=True), patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_metrics",
            wraps=lambda module, operation: lambda func: func,
        ):
            mock_get_secret.return_value = ""
            mock_get_base_url.return_value = ""

            set_aicore_config()

            # Function should complete without errors even with decorator
            # The actual telemetry recording is tested in telemetry tests
