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
CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_URL=https://your-agent-memory-api-url
CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_AUTH_URL=https://your-auth-url
CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTID=your-client-id
CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTSECRET=your-client-secret
```

## Running Integration Tests

```bash
# Run all integration tests
uv run pytest tests/ -m integration -v

# Run specific module integration tests
uv run pytest tests/core/integration/auditlog -v
uv run pytest tests/objectstore/integration/ -v
uv run pytest tests/destination/integration/ -v
uv run pytest tests/agent_memory/integration/ -v
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
