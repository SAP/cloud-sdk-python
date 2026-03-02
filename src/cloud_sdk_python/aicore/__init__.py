"""AI Core configuration module.

This module provides utilities to load AI Core credentials from mounted secrets or environment
variables and configure them for use with LiteLLM.
"""

import json
import logging
import os

from cloud_sdk_python.core.telemetry.metrics_decorator import record_metrics
from cloud_sdk_python.core.telemetry.module import Module
from cloud_sdk_python.core.telemetry.operation import Operation

logger = logging.getLogger(__name__)

def _get_secret(env_var_name: str, file_name: str = None, default: str = "",
               instance_name: str = "aicore-instance") -> str:
    """
    Get a secret value with the following priority:
    1. Try to read from /etc/secrets/appfnd/aicore/{instance_name}/{file_name}
    2. Fall back to environment variable {env_var_name}
    3. Return default value if neither exists

    Args:
        env_var_name: Name of the environment variable
        file_name: Name of the secret file (if None, uses env_var_name)
        default: Default value if neither source has the secret
        instance_name: Name of the aicore instance defined in app.yaml. Defaults to aicore-instance

    """
    secrets_base_path = f"/etc/secrets/appfnd/aicore/{instance_name}"
    secret_file_name = file_name if file_name else env_var_name
    secret_file_path = os.path.join(secrets_base_path, secret_file_name)

    # Try reading from file first
    if os.path.exists(secret_file_path):
        try:
            with open(secret_file_path, 'r') as f:
                value = f.read().strip()
                if value:
                    logger.info(f"Loaded {env_var_name} from file: {secret_file_path}")
                    return value
        except Exception as e:
            logger.warning(f"Failed to read {env_var_name} from {secret_file_path}: {e}")

    # Fall back to environment variable
    value = os.environ.get(env_var_name, default)
    if value:
        logger.info(f"Loaded {env_var_name} from environment variable")
    else:
        logger.warning(f"No value found for {env_var_name}, using default")

    return value

def _get_aicore_base_url(instance_name: str = "aicore-instance") -> str:
    """
    Get AICORE_BASE_URL with special handling for serviceurls JSON structure.
    The serviceurls file contains a JSON object with AI_API_URL field.

    Returns:
        Base URL for AI Core service
    """
    secrets_base_path = f"/etc/secrets/appfnd/aicore/{instance_name}"
    serviceurls_file = os.path.join(secrets_base_path, "serviceurls")

    # Try reading from serviceurls file
    if os.path.exists(serviceurls_file):
        try:
            with open(serviceurls_file, 'r') as f:
                serviceurls_data = json.loads(f.read().strip())
                ai_api_url = serviceurls_data.get("AI_API_URL", "")
                if ai_api_url:
                    logger.info(f"Loaded AICORE_BASE_URL from file: {serviceurls_file}")
                    return ai_api_url
        except Exception as e:
            logger.warning(f"Failed to read AICORE_BASE_URL from {serviceurls_file}: {e}")

    # Fall back to environment variable
    value = os.environ.get("AICORE_BASE_URL", "")
    if value:
        logger.info("Loaded AICORE_BASE_URL from environment variable")
    else:
        logger.warning("No value found for AICORE_BASE_URL")

    return value

@record_metrics(Module.AICORE, Operation.AICORE_SET_CONFIG)
def set_aicore_config(instance_name: str = "aicore-instance") -> None:
    """
    Load secrets from files or environment variables and set them as environment variables.
    This ensures they are available to the LiteLLM library.

    File mappings based on Kubernetes secret structure:
    - clientid -> AICORE_CLIENT_ID
    - clientsecret -> AICORE_CLIENT_SECRET
    - url -> AICORE_AUTH_URL
    - serviceurls (JSON with AI_API_URL) -> AICORE_BASE_URL
    """
    # Load secrets
    client_id = _get_secret("AICORE_CLIENT_ID", "clientid")
    client_secret = _get_secret("AICORE_CLIENT_SECRET", "clientsecret")
    auth_url = _get_secret("AICORE_AUTH_URL", "url")
    base_url = _get_aicore_base_url(instance_name)
    resource_group = _get_secret("AICORE_RESOURCE_GROUP", default="default")

    # Ensure AICORE_AUTH_URL has /oauth/token suffix
    if auth_url and not auth_url.endswith("/oauth/token"):
        auth_url = auth_url.rstrip("/") + "/oauth/token"
    
    if base_url and not base_url.endswith("/v2"):
        base_url = base_url.rstrip("/") + "/v2"
    
    # Set environment variables for LiteLLM
    if client_id:
        os.environ["AICORE_CLIENT_ID"] = client_id
    if client_secret:
        os.environ["AICORE_CLIENT_SECRET"] = client_secret
    if auth_url:
        os.environ["AICORE_AUTH_URL"] = auth_url
    if base_url:
        os.environ["AICORE_BASE_URL"] = base_url
    if resource_group:
        os.environ["AICORE_RESOURCE_GROUP"] = resource_group

    # Log configuration (excluding sensitive information)
    logger.info(f"AICORE_AUTH_URL: {auth_url}")
    logger.info(f"AICORE_BASE_URL: {base_url}")
    logger.info(f"AICORE_RESOURCE_GROUP: {resource_group}")


__all__ = ["set_aicore_config"]
