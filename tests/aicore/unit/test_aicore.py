"""Unit tests for AI Core configuration module."""

import json
import os
from unittest.mock import mock_open, patch

import pytest

from sap_cloud_sdk.aicore import (
    _get_aicore_base_url,
    _get_secret,
    _is_transparent_tls,
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

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_secret(env_var_name, file_name, instance_name=instance_name)

            assert result == mock_file_content

    def test_get_secret_from_file_with_whitespace(self):
        """Test reading secret from file strips whitespace."""
        mock_file_content = "  secret-value  \n"
        env_var_name = "TEST_SECRET"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_secret(env_var_name)

            assert result == "secret-value"

    def test_get_secret_from_file_empty_falls_back_to_env(self):
        """Test that empty file content falls back to environment variable."""
        env_var_name = "TEST_SECRET"
        env_value = "env-secret-value"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="   \n")),
            patch.dict("os.environ", {env_var_name: env_value}, clear=True),
        ):
            result = _get_secret(env_var_name)

            assert result == env_value

    def test_get_secret_from_env_when_file_not_exists(self):
        """Test falling back to environment variable when file doesn't exist."""
        env_var_name = "TEST_SECRET"
        env_value = "env-secret-value"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {env_var_name: env_value}, clear=True),
        ):
            result = _get_secret(env_var_name)

            assert result == env_value

    def test_get_secret_file_read_exception_falls_back_to_env(self):
        """Test that file read exceptions fall back to environment variable."""
        env_var_name = "TEST_SECRET"
        env_value = "env-secret-value"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("Permission denied")),
            patch.dict("os.environ", {env_var_name: env_value}, clear=True),
        ):
            result = _get_secret(env_var_name)

            assert result == env_value

    def test_get_secret_uses_default_when_no_source(self):
        """Test using default value when neither file nor env var exists."""
        env_var_name = "TEST_SECRET"
        default_value = "default-secret"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_secret(env_var_name, default=default_value)

            assert result == default_value

    def test_get_secret_uses_empty_default_when_not_specified(self):
        """Test empty string default when no default specified."""
        env_var_name = "TEST_SECRET"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_secret(env_var_name)

            assert result == ""

    def test_get_secret_uses_env_var_name_as_file_name_when_not_provided(self):
        """Test that env_var_name is used as file_name when file_name is None."""
        env_var_name = "TEST_SECRET"
        mock_file_content = "secret-from-file"

        with (
            patch("os.path.exists", return_value=True) as mock_exists,
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
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

        with (
            patch("os.path.exists", return_value=True) as mock_exists,
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_secret(env_var_name, file_name, instance_name=instance_name)

            expected_path = f"/etc/secrets/appfnd/aicore/{instance_name}/{file_name}"
            mock_exists.assert_called_with(expected_path)
            assert result == mock_file_content

    def test_get_secret_logs_info_when_loaded_from_file(self):
        """Test that info is logged when secret is loaded from file."""
        env_var_name = "TEST_SECRET"
        mock_file_content = "secret-value"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_secret(env_var_name)

            mock_logger.info.assert_called()
            assert any(
                env_var_name in str(call) for call in mock_logger.info.call_args_list
            )

    def test_get_secret_logs_warning_when_file_read_fails(self):
        """Test that warning is logged when file read fails."""
        env_var_name = "TEST_SECRET"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("Permission denied")),
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_secret(env_var_name)

            mock_logger.warning.assert_called()

    def test_get_secret_logs_info_when_loaded_from_env(self):
        """Test that info is logged when secret is loaded from environment."""
        env_var_name = "TEST_SECRET"
        env_value = "env-value"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {env_var_name: env_value}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_secret(env_var_name)

            mock_logger.info.assert_called()

    def test_get_secret_logs_warning_when_no_value_found(self):
        """Test that warning is logged when no value is found."""
        env_var_name = "TEST_SECRET"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_secret(env_var_name)

            mock_logger.warning.assert_called()


class TestGetAICoreBaseUrl:
    """Test suite for _get_aicore_base_url function."""

    def test_get_base_url_from_serviceurls_file_success(self):
        """Test successfully reading base URL from serviceurls JSON file."""
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = json.dumps(serviceurls_data)

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_aicore_base_url()

            assert result == "https://api.example.com"

    def test_get_base_url_from_serviceurls_strips_whitespace(self):
        """Test that base URL from serviceurls strips whitespace."""
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = f"  {json.dumps(serviceurls_data)}  \n"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_aicore_base_url()

            assert result == "https://api.example.com"

    def test_get_base_url_from_serviceurls_missing_key(self):
        """Test handling serviceurls file without AI_API_URL key."""
        serviceurls_data = {"OTHER_KEY": "value"}
        mock_file_content = json.dumps(serviceurls_data)

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {"AICORE_BASE_URL": "https://env.example.com"}),
        ):
            result = _get_aicore_base_url()

            assert result == "https://env.example.com"

    def test_get_base_url_from_serviceurls_empty_value(self):
        """Test handling serviceurls file with empty AI_API_URL value."""
        serviceurls_data = {"AI_API_URL": ""}
        mock_file_content = json.dumps(serviceurls_data)

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {"AICORE_BASE_URL": "https://env.example.com"}),
        ):
            result = _get_aicore_base_url()

            assert result == "https://env.example.com"

    def test_get_base_url_from_serviceurls_invalid_json(self):
        """Test handling invalid JSON in serviceurls file."""
        mock_file_content = "{ invalid json }"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {"AICORE_BASE_URL": "https://env.example.com"}),
        ):
            result = _get_aicore_base_url()

            assert result == "https://env.example.com"

    def test_get_base_url_from_env_when_file_not_exists(self):
        """Test falling back to environment variable when serviceurls file doesn't exist."""
        env_value = "https://env.example.com"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {"AICORE_BASE_URL": env_value}),
        ):
            result = _get_aicore_base_url()

            assert result == env_value

    def test_get_base_url_returns_empty_when_no_source(self):
        """Test returning empty string when neither file nor env var exists."""
        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_aicore_base_url()

            assert result == ""

    def test_get_base_url_custom_instance_name(self):
        """Test using custom instance_name parameter."""
        instance_name = "custom-instance"
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = json.dumps(serviceurls_data)

        with (
            patch("os.path.exists", return_value=True) as mock_exists,
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = _get_aicore_base_url(instance_name=instance_name)

            expected_path = f"/etc/secrets/appfnd/aicore/{instance_name}/serviceurls"
            mock_exists.assert_called_with(expected_path)
            assert result == "https://api.example.com"

    def test_get_base_url_file_read_exception_falls_back_to_env(self):
        """Test that file read exceptions fall back to environment variable."""
        env_value = "https://env.example.com"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("Permission denied")),
            patch.dict("os.environ", {"AICORE_BASE_URL": env_value}),
        ):
            result = _get_aicore_base_url()

            assert result == env_value

    def test_get_base_url_logs_info_when_loaded_from_file(self):
        """Test that info is logged when base URL is loaded from file."""
        serviceurls_data = {"AI_API_URL": "https://api.example.com"}
        mock_file_content = json.dumps(serviceurls_data)

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_file_content)),
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_aicore_base_url()

            mock_logger.info.assert_called()

    def test_get_base_url_logs_warning_when_file_read_fails(self):
        """Test that warning is logged when file read fails."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("Permission denied")),
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_aicore_base_url()

            mock_logger.warning.assert_called()

    def test_get_base_url_logs_info_when_loaded_from_env(self):
        """Test that info is logged when base URL is loaded from environment."""
        env_value = "https://env.example.com"

        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {"AICORE_BASE_URL": env_value}),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_aicore_base_url()

            mock_logger.info.assert_called()

    def test_get_base_url_logs_warning_when_no_value_found(self):
        """Test that warning is logged when no value is found."""
        with (
            patch("os.path.exists", return_value=False),
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            _get_aicore_base_url()

            mock_logger.warning.assert_called()


class TestSetAICoreConfig:
    """Test suite for set_aicore_config function."""

    def test_set_config_loads_all_secrets_successfully(self):
        """Test successfully loading and setting all AI Core configuration."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            # Setup mock returns
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-client-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com",
                        "AICORE_RESOURCE_GROUP": "test-group",
                    }.get(name, default)
                )
            )
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
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com",
                        "AICORE_RESOURCE_GROUP": "default",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )

    def test_set_config_does_not_duplicate_oauth_token_suffix(self):
        """Test that /oauth/token suffix is not duplicated if already present."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com/oauth/token",
                        "AICORE_RESOURCE_GROUP": "default",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )

    def test_set_config_strips_trailing_slash_before_adding_oauth_token(self):
        """Test that trailing slash is removed before appending /oauth/token."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com/",
                        "AICORE_RESOURCE_GROUP": "default",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert (
                os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            )

    def test_set_config_appends_v2_suffix_to_base_url(self):
        """Test that /v2 suffix is appended to base URL."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com",
                        "AICORE_RESOURCE_GROUP": "default",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = "https://api.example.com"

            set_aicore_config()

            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_set_config_does_not_duplicate_v2_suffix(self):
        """Test that /v2 suffix is not duplicated if already present."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com",
                        "AICORE_RESOURCE_GROUP": "default",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = "https://api.example.com/v2"

            set_aicore_config()

            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_set_config_strips_trailing_slash_before_adding_v2(self):
        """Test that trailing slash is removed before appending /v2."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com",
                        "AICORE_RESOURCE_GROUP": "default",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = "https://api.example.com/"

            set_aicore_config()

            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_set_config_does_not_set_empty_values(self):
        """Test that empty values are not set as environment variables."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "",
                        "AICORE_CLIENT_SECRET": "",
                        "AICORE_AUTH_URL": "",
                        "AICORE_RESOURCE_GROUP": "test-group",
                    }.get(name, default)
                )
            )
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
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    default if name == "AICORE_RESOURCE_GROUP" else ""
                )
            )
            mock_get_base_url.return_value = ""

            set_aicore_config()

            assert os.environ["AICORE_RESOURCE_GROUP"] == "default"

    def test_set_config_custom_instance_name(self):
        """Test using custom instance_name parameter."""
        instance_name = "custom-instance"

        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.return_value = ""
            mock_get_base_url.return_value = ""

            set_aicore_config(instance_name=instance_name)

            # Verify instance_name was passed to _get_aicore_base_url
            mock_get_base_url.assert_called_with(instance_name)

            # Verify instance_name was passed to all _get_secret calls
            for c in mock_get_secret.call_args_list:
                assert c.kwargs.get("instance_name") == instance_name, (
                    f"_get_secret call for {c.args[0]} missing instance_name={instance_name}"
                )

    def test_set_config_calls_get_secret_with_correct_parameters(self):
        """Test that _get_secret is called with correct parameters for each secret."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.return_value = ""
            mock_get_base_url.return_value = ""

            set_aicore_config()

            default_instance = "aicore-instance"
            # Verify _get_secret was called with correct parameters including instance_name
            mock_get_secret.assert_any_call(
                "AICORE_CLIENT_ID", "clientid", instance_name=default_instance
            )
            mock_get_secret.assert_any_call(
                "AICORE_CLIENT_SECRET", "clientsecret", instance_name=default_instance
            )
            mock_get_secret.assert_any_call(
                "AICORE_AUTH_URL", "url", instance_name=default_instance
            )
            mock_get_secret.assert_any_call(
                "AICORE_RESOURCE_GROUP",
                default="default",
                instance_name=default_instance,
            )

    def test_set_config_logs_configuration(self):
        """Test that configuration completion is logged (excluding sensitive information)."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
            patch("sap_cloud_sdk.aicore.logger") as mock_logger,
        ):
            mock_get_secret.side_effect = (
                lambda name, file_name=None, default="", instance_name="aicore-instance": (
                    {
                        "AICORE_CLIENT_ID": "test-client-id",
                        "AICORE_CLIENT_SECRET": "test-secret",
                        "AICORE_AUTH_URL": "https://auth.example.com",
                        "AICORE_RESOURCE_GROUP": "test-group",
                    }.get(name, default)
                )
            )
            mock_get_base_url.return_value = "https://api.example.com"

            set_aicore_config()

            # Verify info logging was called with success message
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any(
                "AI Core configuration has been set successfully" in call
                for call in info_calls
            )

            # Verify sensitive info is not logged
            all_log_calls = str(mock_logger.mock_calls)
            assert "test-client-id" not in all_log_calls
            assert "test-secret" not in all_log_calls

    def test_set_config_decorated_with_record_metrics(self):
        """Test that set_aicore_config is decorated with @record_metrics."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url") as mock_get_base_url,
            patch.dict("os.environ", {}, clear=True),
            patch(
                "sap_cloud_sdk.core.telemetry.metrics_decorator.record_metrics",
                wraps=lambda module, operation: lambda func: func,
            ),
        ):
            mock_get_secret.return_value = ""
            mock_get_base_url.return_value = ""

            set_aicore_config()

            # Function should complete without errors even with decorator
            # The actual telemetry recording is tested in telemetry tests


class TestIsTransparentTls:
    """Test suite for _is_transparent_tls helper."""

    def test_returns_true_for_value_true(self):
        with patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "true"}):
            assert _is_transparent_tls() is True

    def test_returns_true_for_value_1(self):
        with patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "1"}):
            assert _is_transparent_tls() is True

    def test_returns_true_for_value_yes(self):
        with patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "yes"}):
            assert _is_transparent_tls() is True

    def test_returns_true_case_insensitive(self):
        with patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "TRUE"}):
            assert _is_transparent_tls() is True

    def test_returns_false_when_absent(self):
        with patch.dict("os.environ", {}, clear=True):
            assert _is_transparent_tls() is False

    def test_returns_false_for_value_false(self):
        with patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "false"}):
            assert _is_transparent_tls() is False


class TestSetAICoreConfigTransparentTls:
    """Test suite for set_aicore_config in transparent TLS mode."""

    def _base_secrets(self):
        return {
            "AICORE_CLIENT_ID": "test-client-id",
            "AICORE_AUTH_URL": "https://auth.example.com",
            "AICORE_RESOURCE_GROUP": "default",
        }

    def test_transparent_tls_does_not_set_client_secret(self):
        """In transparent TLS mode, AICORE_CLIENT_SECRET must not be written to env."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url", return_value="https://api.example.com"),
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "true"}, clear=True),
        ):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": (
                self._base_secrets().get(name, default)
            )

            set_aicore_config()

            assert "AICORE_CLIENT_SECRET" not in os.environ

    def test_transparent_tls_removes_stale_client_secret(self):
        """Any pre-existing AICORE_CLIENT_SECRET is cleared in transparent TLS mode."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url", return_value=""),
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict(
                "os.environ",
                {"AICORE_TRANSPARENT_TLS": "true", "AICORE_CLIENT_SECRET": "stale-secret"},
                clear=True,
            ),
        ):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": (
                self._base_secrets().get(name, default)
            )

            set_aicore_config()

            assert "AICORE_CLIENT_SECRET" not in os.environ

    def test_transparent_tls_sets_other_credentials(self):
        """Non-secret credentials are still set in transparent TLS mode."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url", return_value="https://api.example.com"),
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "true"}, clear=True),
        ):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": (
                self._base_secrets().get(name, default)
            )

            set_aicore_config()

            assert os.environ["AICORE_CLIENT_ID"] == "test-client-id"
            assert os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"
            assert os.environ["AICORE_BASE_URL"] == "https://api.example.com/v2"

    def test_standard_mode_still_sets_client_secret(self):
        """Regression: without transparent TLS, client_secret is still written."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url", return_value=""),
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_get_secret.side_effect = lambda name, file_name=None, default="", instance_name="aicore-instance": (
                {**self._base_secrets(), "AICORE_CLIENT_SECRET": "my-secret"}.get(name, default)
            )

            set_aicore_config()

            assert os.environ["AICORE_CLIENT_SECRET"] == "my-secret"

    def test_transparent_tls_does_not_call_get_secret_for_client_secret(self):
        """_get_secret should not be called for clientsecret in transparent TLS mode."""
        with (
            patch("sap_cloud_sdk.aicore._get_secret") as mock_get_secret,
            patch("sap_cloud_sdk.aicore._get_aicore_base_url", return_value=""),
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict("os.environ", {"AICORE_TRANSPARENT_TLS": "true"}, clear=True),
        ):
            mock_get_secret.return_value = ""

            set_aicore_config()

            called_names = [c.args[0] for c in mock_get_secret.call_args_list]
            assert "AICORE_CLIENT_SECRET" not in called_names


# ---------------------------------------------------------------------------
# Proxy mode — set_aicore_config() with AICORE_PROXY_URL
# ---------------------------------------------------------------------------


class TestSetAICoreConfigProxyMode:
    """set_aicore_config() routes via proxy when AICORE_PROXY_URL is present."""

    def _base_proxy_env(self, **extra):
        return {"AICORE_PROXY_URL": "https://proxy.example.com", **extra}

    def test_proxy_mode_sets_litellm_api_base(self):
        import litellm
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict("os.environ", self._base_proxy_env(), clear=True),
        ):
            set_aicore_config()
        assert litellm.api_base == "https://proxy.example.com"
        litellm.api_base = None  # cleanup

    def test_proxy_mode_sets_litellm_api_key_when_virtual_key_present(self):
        import litellm
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict(
                "os.environ",
                self._base_proxy_env(AICORE_PROXY_API_KEY="sk-virt-123"),
                clear=True,
            ),
        ):
            set_aicore_config()
        assert litellm.api_key == "sk-virt-123"
        litellm.api_key = None  # cleanup

    def test_proxy_mode_does_not_write_aicore_credentials(self):
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch.dict("os.environ", self._base_proxy_env(), clear=True),
        ):
            set_aicore_config()
            for var in ("AICORE_CLIENT_ID", "AICORE_CLIENT_SECRET", "AICORE_AUTH_URL"):
                assert var not in os.environ, f"{var} must not be written in proxy mode"

    def test_proxy_mode_takes_precedence_over_destination(self):
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.aicore._configure_destination_mode") as mock_dest,
            patch.dict(
                "os.environ",
                self._base_proxy_env(AICORE_DESTINATION_NAME="aicore"),
                clear=True,
            ),
        ):
            set_aicore_config()
        mock_dest.assert_not_called()

    def test_proxy_mode_still_calls_set_filtering(self):
        with (
            patch("sap_cloud_sdk.aicore.set_filtering") as mock_filter,
            patch.dict("os.environ", self._base_proxy_env(), clear=True),
        ):
            set_aicore_config()
        mock_filter.assert_called_once()

    def test_direct_mode_used_when_neither_proxy_nor_destination_set(self):
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.aicore._configure_direct_mode") as mock_direct,
            patch.dict("os.environ", {}, clear=True),
        ):
            set_aicore_config()
        mock_direct.assert_called_once()


# ---------------------------------------------------------------------------
# Destination mode — set_aicore_config() with AICORE_DESTINATION_NAME
# ---------------------------------------------------------------------------


class TestSetAICoreConfigDestinationMode:
    """set_aicore_config() loads credentials from BTP Destination Service."""

    def _mock_destination(
        self,
        url="https://api.ai.prod.example.com",
        properties=None,
        auth_tokens=None,
    ):
        from unittest.mock import MagicMock
        dest = MagicMock()
        dest.url = url
        dest.properties = properties or {
            "clientId": "sb-client-id",
            "clientSecret": "client-secret-value",
            "tokenServiceURL": "https://auth.example.com/oauth/token",
        }
        dest.auth_tokens = auth_tokens or []
        return dest

    def test_destination_mode_sets_base_url_with_v2_suffix(self):
        dest = self._mock_destination(url="https://api.ai.prod.example.com")
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch(
                "sap_cloud_sdk.destination.create_client"
            ) as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
            assert os.environ["AICORE_BASE_URL"] == "https://api.ai.prod.example.com/v2"

    def test_destination_mode_does_not_double_v2(self):
        dest = self._mock_destination(url="https://api.ai.prod.example.com/v2")
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
            assert os.environ["AICORE_BASE_URL"] == "https://api.ai.prod.example.com/v2"

    def test_destination_mode_sets_resource_group_from_properties(self):
        dest = self._mock_destination(
            properties={
                "clientId": "id",
                "clientSecret": "sec",
                "tokenServiceURL": "https://auth.example.com/oauth/token",
                "resource_group": "production",
            }
        )
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
            assert os.environ["AICORE_RESOURCE_GROUP"] == "production"

    def test_destination_mode_defaults_resource_group_to_default(self):
        dest = self._mock_destination()  # no resource_group in properties
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
            assert os.environ["AICORE_RESOURCE_GROUP"] == "default"

    def test_destination_mode_sets_client_credentials(self):
        dest = self._mock_destination()
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
            assert os.environ["AICORE_CLIENT_ID"] == "sb-client-id"
            assert os.environ["AICORE_CLIENT_SECRET"] == "client-secret-value"

    def test_destination_mode_appends_oauth_token_suffix(self):
        dest = self._mock_destination(
            properties={
                "clientId": "id",
                "clientSecret": "sec",
                "tokenServiceURL": "https://auth.example.com",  # no /oauth/token
            }
        )
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
            assert os.environ["AICORE_AUTH_URL"] == "https://auth.example.com/oauth/token"

    def test_destination_mode_raises_when_destination_not_found(self):
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "missing"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = None
            with pytest.raises(RuntimeError, match="not found"):
                set_aicore_config()

    def test_destination_mode_raises_when_no_client_credentials(self):
        dest = self._mock_destination(properties={"resource_group": "default"})
        with (
            patch("sap_cloud_sdk.aicore.set_filtering"),
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            with pytest.raises(RuntimeError, match="clientId/clientSecret"):
                set_aicore_config()

    def test_destination_mode_still_calls_set_filtering(self):
        dest = self._mock_destination()
        with (
            patch("sap_cloud_sdk.aicore.set_filtering") as mock_filter,
            patch("sap_cloud_sdk.destination.create_client") as mock_create,
            patch.dict("os.environ", {"AICORE_DESTINATION_NAME": "aicore"}, clear=True),
        ):
            mock_create.return_value.get_destination.return_value = dest
            set_aicore_config()
        mock_filter.assert_called_once()
