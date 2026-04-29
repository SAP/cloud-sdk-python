"""Telemetry constants and types.

This module contains all constants, attribute keys, and type definitions
used across the telemetry module.
"""

# Metric names
REQUEST_COUNTER_NAME = "sap.cloud_sdk.capability.requests"
ERROR_COUNTER_NAME = "sap.cloud_sdk.capability.errors"
LLM_TOKEN_HISTOGRAM_NAME = "gen_ai.client.token.usage"

# Attribute keys - OTel standard
ATTR_SERVICE_INSTANCE_ID = "service.instance.id"
ATTR_SERVICE_NAME = "service.name"
ATTR_DEPLOYMENT_ENVIRONMENT = "deployment.environment.name"
ATTR_CLOUD_REGION = "cloud.region"
ATTR_USER_ID = "user.id"

# Attribute keys - SAP standard
ATTR_SAP_SUBACCOUNT_ID = "sap.cld.subaccount_id"
ATTR_SAP_TENANT_ID = "sap.tenancy.tenant_id"
ATTR_SAP_SYSTEM_ROLE = "sap.cld.system_role"
ATTR_SAP_ORIGIN = "sap.ai.agent.trigger.type"
ATTR_SAP_SDK_NAME = "sap.cloud_sdk.name"
ATTR_SAP_SDK_LANGUAGE = "sap.cloud_sdk.language"
ATTR_SAP_SDK_VERSION = "sap.cloud_sdk.version"
ATTR_SAP_SOLUTION_AREA = "sap.solution_area"

# Attribute keys - MLflow
ATTR_MLFLOW_EXPERIMENT_ID = "mlflow.experiment_id"

# Attribute keys - ORD
ATTR_SAP_ORD_ID = "sap.ord.id"

# Attribute keys - SAP App Foundation specific
ATTR_CAPABILITY = "sap.cloud_sdk.capability"
ATTR_FUNCTIONALITY = "sap.cloud_sdk.functionality"
ATTR_SOURCE = "sap.cloud_sdk.source"
ATTR_DEPRECATED = "sap.cloud_sdk.deprecated"

# GenAI-specific attribute keys
ATTR_GENAI_REQUEST_MODEL = "gen_ai.request.model"
ATTR_GENAI_OPERATION_NAME = "gen_ai.operation.name"
ATTR_GENAI_TOKEN_TYPE = "gen_ai.token.type"
ATTR_GENAI_PROVIDER = "gen_ai.provider.name"

# SDK Constants
SDK_NAME = "SAP Cloud SDK for Python"
SDK_PACKAGE_NAME = "sap_cloud_sdk"
