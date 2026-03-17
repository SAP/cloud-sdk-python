![Build status](https://github.com/SAP/cloud-sdk-python/workflows/Build/badge.svg) [![REUSE status](https://api.reuse.software/badge/github.com/SAP/cloud-sdk-python)](https://api.reuse.software/info/github.com/SAP/cloud-sdk-python)

# SAP Cloud SDK for Python

## About this project

This SDK provides consistent interfaces for interacting with foundational services such as object storage, destination management, audit logging, telemetry, and secure credential handling.

The Python SDK offers a clean, type-safe API following Python best practices while maintaining compatibility with the SAP Application Foundation ecosystem.

### Key Features

- **AI Core Integration**
- **Audit Log Service**
- **Destination Service**
- **ObjectStore Service**
- **Secret Resolver**
- **Telemetry & Observability**

## Requirements and Setup

- **Python**: 3.11 or higher

### Installation

```python
# uv
uv add sap-cloud-sdk

# Poetry
poetry add sap-cloud-sdk

# Pip
pip install sap-cloud-sdk
````

### Environment Configuration

The SDK automatically resolves configuration from multiple sources with the following priority:

1. **Kubernetes-mounted secrets**: `/etc/secrets/appfnd/<module>/<instance>/<field>`
2. **Environment variables**: `CLOUD_SDK_CFG_<MODULE>_<INSTANCE>_<FIELD>`
   - For instance names, hyphens (`"-"`) are replaced with underscores (`"_"`) for compatibility with system environment variables.
   - You can see examples in our [env_integration_tests.example](.env_integration_tests.example)

### Usage Guides

Each module has comprehensive usage guides:

- [AuditLog](src/sap_cloud_sdk/core/auditlog/user-guide.md)
- [Destination](src/sap_cloud_sdk/destination/user-guide.md)
- [ObjectStore](src/sap_cloud_sdk/objectstore/user-guide.md)
- [Secret Resolver](src/sap_cloud_sdk/core/secret_resolver/user-guide.md)
- [Telemetry](src/sap_cloud_sdk/core/telemetry/user-guide.md)

## Support, Feedback, Contributing

This project is open to feature requests/suggestions, bug reports etc. via [GitHub issues](https://github.com/SAP/cloud-sdk-python/issues). Contribution and feedback are encouraged and always welcome. For more information about how to contribute, the project structure, as well as additional contribution information, see our [Contribution Guidelines](CONTRIBUTING.md).

## Security / Disclosure

If you find any bug that may be a security problem, please follow our instructions at [in our security policy](https://github.com/SAP/cloud-sdk-python/security/policy) on how to report it. Please do not create GitHub issues for security-related doubts or problems.

## Code of Conduct

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone. By participating in this project, you agree to abide by its [Code of Conduct](https://github.com/SAP/.github/blob/main/CODE_OF_CONDUCT.md) at all times.

## Licensing

Copyright 2026 SAP SE or an SAP affiliate company and Cloud SDK Python contributors. Please see our [LICENSE](LICENSE) for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available [via the REUSE tool](https://api.reuse.software/info/github.com/SAP/cloud-sdk-python)
