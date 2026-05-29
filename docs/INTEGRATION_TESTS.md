# Integration Tests

This document describes how to run integration tests for the Cloud SDK for Python.

## Overview

Integration tests verify that the SDK modules work correctly with real external services. They use actual dependencies to validate end-to-end functionality.

## Prerequisites

### Required Tools

- **Python 3.11+**: Required for running the tests
- **uv**: Package manager for dependency management

### Install Dependencies

```bash
# Install all dependencies including test dependencies
uv sync --all-extras
```

## Configuration

### Environment Variables

Integration tests require specific environment variables to be configured. These are managed through the `.env_integration_tests` file in the project root.

### ObjectStore Integration Tests

For ObjectStore integration tests, configure the following variables in `.env_integration_tests`:

```bash
# ObjectStore Configuration
CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST=your-host-here
CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID=your-access-key-id-here
CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY=your-secret-access-key-kere
CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_BUCKET=your-bucket-here
CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED=false
```

### AuditLog Integration Tests

For AuditLog integration tests, configure the following variables in `.env_integration_tests`:

```bash
# AuditLog Configuration
CLOUD_SDK_CFG_AUDITLOG_DEFAULT_URL=https://your-auditlog-api-url-here
CLOUD_SDK_CFG_AUDITLOG_DEFAULT_UAA='{"url":"https://your-auth-url","clientid":"your-client-id","clientsecret":"your-client-secret"}'
```

**Note**: AuditLog integration tests are cloud-only and require real SAP Audit Log Service credentials. The secret resolver automatically loads configuration from `/etc/secrets/appfnd` or environment variables - no manual configuration parsing needed in test code.

### Destination Integration Tests

For Destination integration tests, configure the following variables in `.env_integration_tests`:

```bash
# Destination Configuration
CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID=your-destination-client-id-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET=your-destination-client-secret-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL=https://your-destination-auth-url-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI=https://your-destination-configuration-uri-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE=your-identity-zone-here
```

### Agent Memory Integration Tests

For Agent Memory integration tests, configure the following variables in `.env_integration_tests`:

```bash
# Agent Memory Configuration
CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL=https://your-agent-memory-api-url
CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA='{"url":"https://your-auth-url","clientid":"your-client-id","clientsecret":"your-client-secret"}'
```

### Data Anonymization Integration Tests

For Data Anonymization integration tests, configure the following variables in `.env_integration_tests`:

```bash
# Data Anonymization Configuration
CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_URL=https://your-data-anonymization-api-url-here
CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_CERT=your-base64-encoded-client-certificate-pem
CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_KEY=your-base64-encoded-client-private-key-pem
```

`CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_CERT` and `CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_KEY` must contain the base64-encoded PEM content, not filesystem paths.

If the certificate is managed through BTP Destination service, you can use a destination instead of inline certificate values:

```bash
CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_URL=https://your-data-anonymization-api-url-here
CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_DESTINATION_NAME=your-client-certificate-destination-name
```

The destination must be configured with `ClientCertificateAuthentication` and reference a certificate bundle containing the client certificate and private key.

### ADMS Integration Tests

For ADMS (Advanced Document Management Service) integration tests, configure the following variables in `.env_integration_tests`:

```bash
# ADMS Configuration
CLOUD_SDK_CFG_ADMS_DEFAULT_URL=https://your-tenant.accounts.ondemand.com
CLOUD_SDK_CFG_ADMS_DEFAULT_URI=https://your-adm-instance.cfapps.eu20.hana.ondemand.com
CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTID=your-ias-client-id
CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTSECRET=your-ias-client-secret
CLOUD_SDK_CFG_ADMS_DEFAULT_RESOURCE=urn:sap:identity:application:provider:name:your-app
```

`CLOUD_SDK_CFG_ADMS_DEFAULT_URI` points the tests at the target ADM service. The other `CLOUD_SDK_CFG_ADMS_DEFAULT_*` variables hold the IAS service-binding credentials used by the SDK to fetch Bearer tokens. Tests are skipped automatically when any of these are missing.

### Agent Gateway Integration Tests

Agent Gateway integration tests use the LoB agent flow via the Destination Service. Configure the following variables in `.env_integration_tests`:

```bash
# Destination Service (required by the LoB agent flow)
CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID=your-destination-client-id-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET=your-destination-client-secret-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL=https://your-destination-auth-url-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI=https://your-destination-configuration-uri-here
CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE=your-identity-zone-here

# Landscape suffix used to resolve the IAS destination name
APPFND_CONHOS_LANDSCAPE=your-landscape-here

# Tenant subdomain for multi-tenant lookup
TENANT_SUBDOMAIN=your-tenant-subdomain-here

# User JWT for token exchange scenarios (get_user_auth)
# If not set, user auth scenarios are automatically skipped
AGW_USER_TOKEN=your-user-jwt-here
```

## Running Integration Tests

```bash
# Run all integration tests
uv run pytest tests/ -m integration -v

# Run specific module integration tests
uv run pytest tests/core/integration/auditlog -v
uv run pytest tests/core/integration/data_anonymization -v
uv run pytest tests/objectstore/integration/ -v
uv run pytest tests/destination/integration/ -v
uv run pytest tests/agent_memory/integration/ -v
uv run pytest tests/adms/integration/ -v
uv run pytest tests/agentgateway/integration/ -v
```

### BDD Scenarios

Tests are written in Gherkin format for readability:

```gherkin
Scenario: Upload object from bytes
  Given I have test content as bytes "Hello, Object Store!"
  And I have an object named "test-file.txt"
  When I upload the object from bytes with content type "text/plain"
  Then the upload should be successful
  And the object should exist in the store
```
