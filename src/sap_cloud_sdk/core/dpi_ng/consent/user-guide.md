# Consent User Guide

This module provides a unified API for managing consents, purposes, templates,
retention rules, and configuration reference data exposed by the DPI V2 Consent
Repository OData service. The module contains a factory function, typed request
and result dataclasses, an OData transport abstraction, and operation-level
telemetry so developers can focus on business logic while satisfying data-privacy
requirements. Telemetry is limited to aggregate operation metrics and excludes
request and response payloads.

## Installation

The consent module is part of the SAP Cloud SDK for Python and is available
automatically once the SDK is installed.

```bash
pip install sap-cloud-sdk
```

Requires Python 3.11+.

## Import

Import what you need explicitly:

```python
from sap_cloud_sdk.core.dpi_ng.consent import (
    create_client,
    ConsentSDKConfig,
    ClientCredentialsAuth,
    CreateConsentRequest,
    WithdrawConsentRequest,
    CheckConsentExistsResult,
)
```

Or use a star import for convenience:

```python
from sap_cloud_sdk.core.dpi_ng.consent import *
```

## Quick Start

Pass a `ConsentSDKConfig` with `ClientCredentialsAuth` when OAuth2 client
credentials are available. The auth provider fetches and refreshes bearer tokens
automatically.

```python
from sap_cloud_sdk.core.dpi_ng.consent import (
    create_client,
    ConsentSDKConfig,
    ClientCredentialsAuth,
)

config = ConsentSDKConfig(
    base_url="https://<your-consent-service-host>",
    auth=ClientCredentialsAuth(
        token_url="https://<your-xsuaa-host>/oauth/token",
        client_id="<client-id>",
        client_secret="<client-secret>",
    ),
)

with create_client(config=config) as client:
    consents = client.consents.list_consents(filter="lifecycleStatusCode eq '1'")
    for c in consents:
        print(c.consent_id, c.lifecycle_status_code)
```

**`ConsentSDKConfig` parameters:**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `base_url` | Yes | - | URL of the DPI external service router (e.g. `https://api.service.<region>.ngdpi.dpp.cloud.sap`). Found in the credentials of the `data-privacy-integration` service instance. |
| `auth` | Yes | - | Authentication strategy - one of `BearerTokenAuth`, `ClientCredentialsAuth`, or `ClientCertificateAuth`. |
| `timeout` | No | `30.0` | HTTP request timeout in seconds. |
| `verify_ssl` | No | `True` | Verify TLS certificates. Set `False` only in local dev. Overridden by `ClientCertificateAuth` when a custom `ca_file` is provided. |
| `service_path` | No | `/sap/cp/kernel/dpi/consent/odata/v4` | Base path the DPI external service router uses to forward requests. Do not override unless deploying to a non-standard environment. |
| `tenant_id` | Required for `ClientCertificateAuth`; **must not be set** for others | `None` | Tenant identifier sent as the `x-tenant-id` header. Required for mTLS because the handshake does not carry a tenant claim. Raises `ValueError` if provided with `BearerTokenAuth` or `ClientCredentialsAuth`. |

## Authentication

The SDK supports three authentication strategies. Pass one as the `auth`
argument to `ConsentSDKConfig`.

### BearerTokenAuth

Use when you already have a valid bearer token:

```python
from sap_cloud_sdk.core.dpi_ng.consent import ConsentSDKConfig, BearerTokenAuth

config = ConsentSDKConfig(
    base_url="https://api.service.<region>.ngdpi.dpp.cloud.sap",
    auth=BearerTokenAuth(token="<bearer-token>"),
)
```

| Parameter | Required | Description |
|---|---|---|
| `token` | Yes | Bearer token sent as the `Authorization: Bearer` header on every request. |

The token is sent as-is - no automatic refresh is performed. Use
`ClientCredentialsAuth` for long-running processes where the token may expire.
Passing an empty string raises `ValueError: token must not be empty`.

### ClientCredentialsAuth

Use when you have OAuth2 client credentials. The provider performs the
`client_credentials` grant against the given token URL and refreshes the token
transparently 60 seconds before it expires:

```python
from sap_cloud_sdk.core.dpi_ng.consent import (
    ConsentSDKConfig,
    ClientCredentialsAuth,
)

config = ConsentSDKConfig(
    base_url="https://api.service.<region>.ngdpi.dpp.cloud.sap",
    auth=ClientCredentialsAuth(
        token_url="https://<xsuaa-host>/oauth/token",
        client_id="<client-id>",
        client_secret="<client-secret>",
    ),
)
```

| Parameter | Required | Description |
|---|---|---|
| `token_url` | Yes | OAuth2 token endpoint URL. |
| `client_id` | Yes | OAuth2 client identifier. |
| `client_secret` | Yes | OAuth2 client secret. |

Passing an empty string for any field raises
`ValueError: token_url, client_id, and client_secret are all required`.

### ClientCertificateAuth and tenant_id

Use when your environment requires mutual TLS (mTLS):

```python
from sap_cloud_sdk.core.dpi_ng.consent import (
    ConsentSDKConfig,
    ClientCertificateAuth,
)

config = ConsentSDKConfig(
    base_url="https://api.service.<region>.ngdpi.dpp.cloud.sap",
    auth=ClientCertificateAuth(
        cert_file="/path/to/client.crt",
        key_file="/path/to/client.key",
        ca_file="/path/to/ca.crt",
    ),
    tenant_id="<your-tenant-id>",
)
```

| Parameter | Required | Description |
|---|---|---|
| `cert_file` | Yes | Path to the PEM-encoded client certificate file. |
| `key_file` | Yes | Path to the PEM-encoded private key file. |
| `ca_file` | No | Path to a custom CA bundle. Omit to use the system trust store. |

Passing an empty string for `cert_file` or `key_file` raises
`ValueError: cert_file and key_file are required`.

## Client structure

`ConsentClient` exposes five service attributes:

| Attribute | OData service | Purpose |
|---|---|---|
| `client.consents` | `consentServices` | Consent creation, withdrawal, termination, reads |
| `client.purposes` | `consentPurposeExternalServices` | Purpose CRUD, lifecycle, and purpose texts |
| `client.templates` | `consentTemplateExternalServices` | Template CRUD, lifecycle, template texts, third-party data |
| `client.retention` | `consentRetentionExternalServices` | Retention rule CRUD and lifecycle |
| `client.configuration` | `consentConfigurationExternalServices` | Reference data CRUD (controllers, applications, jurisdictions, ...) |

## Operations

All `list_*` methods accept OData query kwargs:

| Kwarg | OData option | Example |
|---|---|---|
| `filter` | `$filter` | `filter="lifecycleStatusCode eq '2'"` |
| `top` | `$top` | `top=10` |
| `skip` | `$skip` | `skip=20` |
| `orderby` | `$orderby` | `orderby="changedAt desc"` |

### Consents (`client.consents`)

#### List consents

```python
consents = client.consents.list_consents(
    filter="lifecycleStatusCode eq '1'",
    top=50,
)
for c in consents:
    print(c.consent_id, c.lifecycle_status_code)
```

#### Get a consent by ID

```python
consent = client.consents.get_consent("<consent-uuid>")
print(consent.consent_id, consent.data_subject_id)
```

#### Delete a consent

```python
client.consents.delete_consent("<consent-uuid>")
```

#### Create a consent from a template

```python
from sap_cloud_sdk.core.dpi_ng.consent import CreateConsentRequest

request = CreateConsentRequest(
    data_subject_id="user@example.com",
    template_name="GDPR_Marketing_2024",
    language_code="en",
    data_subject_type_name="Employee",
)
consents = client.consents.create_consent_from_template(request)
for c in consents:
    print(c.consent_id)
```

**Required fields:**
- `data_subject_id` - The unique identifier for the data subject. This sets the `DataSubjectId` for resulting consent records.
- `template_name` - The name of the consent form that should be used to create the consent record.
- `language_code` - The language in which the consent was granted.
- `data_subject_type_name` - The name of a data subject type.

**Optional fields:**
- `data_subject_description` - The full name of the data subject.
- `outbound_channel_type_name` - The name of an outbound channel type. If you include an outbound channel type, you must also include an outbound channel.
- `outbound_channel` - Outbound channel identifier.
- `valid_from` - The date when the consent record starts being valid. If no value is provided, the current timestamp is used.
- `jurisdiction_code` - The legal space in which the consent is valid. Overrides the `JurisdictionCode` from the consent form.
- `application_template_id` - Freely used by the integrating application (e.g. a context string identifying the business process). Overrides the `applicationTemplateId` from the consent form.
- `controller_name` - The name of a data controller. Overrides the `ControllerName` from the consent form.
- `granted_by` - The natural person who granted the consent — either the data subject or another person acting on their behalf (e.g. a customer service representative or legal guardian).
- `granted_at` - When the consent was granted.
- `submission_site` - Where the consent was granted. This could be a physical place (e.g. a hospital name) or a website.

#### Withdraw a consent

```python
from sap_cloud_sdk.core.dpi_ng.consent import WithdrawConsentRequest

client.consents.withdraw_consent(
    WithdrawConsentRequest(
        consent_id="<consent-uuid>",
        withdrawn_by="user@example.com",
    )
)
```

#### Terminate a consent

```python
client.consents.terminate_consent(
    WithdrawConsentRequest(
        consent_id="<consent-uuid>",
        withdrawn_by="contract-end-process",
    )
)
```

`WithdrawConsentRequest.withdrawn_by` and `withdrawn_at` are both optional — omit them to let the service
record the current timestamp.

#### Check whether a consent exists

```python
result = client.consents.check_consent_exists(
    data_subject_id="user@example.com",
    template_id="<template-uuid>",
)
if result.consent_exists:
    print("Consent found:", result.consent_id)
```

`check_consent_exists` returns a `CheckConsentExistsResult` with two fields:
`consent_exists` (`bool | None`) and `consent_id` (`str | None`).

---

### Purposes (`client.purposes`)

#### List purposes

```python
purposes = client.purposes.list_purposes(
    filter="lifecycleStatusCode eq '2'",
    top=25,
)
for p in purposes:
    print(p.purpose_id, p.purpose_name)
```

#### Get a purpose by ID

```python
purpose = client.purposes.get_purpose("<purpose-uuid>")
print(purpose.purpose_name, purpose.sensitive_data_flag)
```

#### Create a purpose

```python
purpose = client.purposes.create_purpose({
    "purpose_name": "Marketing_Emails",
    "sensitive_data_flag": False,
})
print(purpose.purpose_id)
```

#### Update a purpose

```python
purpose = client.purposes.update_purpose(
    "<purpose-uuid>",
    {"purpose_name": "Marketing_Emails_Updated", "sensitive_data_flag": True},
)
```

#### Delete a purpose

```python
client.purposes.delete_purpose("<purpose-uuid>")
```

#### Set a purpose active / inactive

```python
client.purposes.set_purpose_active("<purpose-uuid>")
client.purposes.set_purpose_inactive("<purpose-uuid>")
```

Both methods return the refreshed entity after invoking the lifecycle action.

#### List purpose texts

```python
texts = client.purposes.list_purpose_texts(
    filter="purposeId eq '<purpose-uuid>'"
)
```

#### Get a purpose text

```python
text = client.purposes.get_purpose_text("<purpose-text-uuid>")
print(text.text)
```

#### Create a purpose text

```python
text = client.purposes.create_purpose_text({
    "purpose_id": "<purpose-uuid>",
    "type_code": "01",
    "language_code": "en",
    "text": "We use your email to send marketing updates.",
})
```

#### Update a purpose text

```python
text = client.purposes.update_purpose_text(
    "<purpose-text-uuid>",
    body={"purpose_id": "<purpose-uuid>", "type_code": "01", "language_code": "de", "text": "Updated marketing email description."},
)
```

#### Delete a purpose text

```python
client.purposes.delete_purpose_text("<purpose-text-uuid>")
```

---

### Templates (`client.templates`)

#### List templates

```python
templates = client.templates.list_templates(
    filter="lifecycleStatusCode eq '2'"
)
```

#### Get a template by ID

```python
template = client.templates.get_template("<template-uuid>")
print(template.template_name)
```

#### Create a template

```python
template = client.templates.create_template({
    "template_name": "GDPR_Marketing_2024",
    "jurisdiction_code": "EU",
    "consent_model_code": "1",
    "validity_period": 365,
    "expiring_period": 30,
    "purpose_name": "Marketing_Emails",
    "controller_name": "AB_Corp",
    "application_name": "HR_Portal",
})
print(template.template_id)
```

#### Update a template

```python
template = client.templates.update_template(
    "<template-uuid>",
    {
        "template_name": "GDPR_Marketing_2025",
        "jurisdiction_code": "DE",
        "consent_model_code": "2",
        "validity_period": 180,
        "expiring_period": 15,
        "purpose_name": "Marketing_Emails_Updated",
        "controller_name": "AB_Corp_Updated",
        "application_name": "HR_Portal_v2",
    },
)
```

#### Delete a template

```python
client.templates.delete_template("<template-uuid>")
```

#### Set a template active / inactive

```python
client.templates.set_template_active("<template-uuid>")
client.templates.set_template_inactive("<template-uuid>")
```

#### List template texts

```python
texts = client.templates.list_template_texts(
    filter="templateId eq '<template-uuid>'"
)
```

#### Get a template text

```python
text = client.templates.get_template_text("<template-text-uuid>")
print(text.text)
```

#### Create a template text

```python
text = client.templates.create_template_text({
    "template_id": "<template-uuid>",
    "language_code": "en",
    "type_code": "51",
    "text": "Full consent statement in English...",
})
```

#### Update a template text

```python
text = client.templates.update_template_text(
    "<template-text-uuid>",
    body={"template_id": "<template-uuid>", "language_code": "de", "type_code": "52", "text": "Revised consent statement."},
)
```

#### Delete a template text

```python
client.templates.delete_template_text("<template-text-uuid>")
```

#### List third-party personal data assignments

```python
records = client.templates.list_third_party_pers_data(
    filter="templateId eq '<template-uuid>'"
)
```

#### Get a third-party personal data record

```python
record = client.templates.get_third_party_pers_data(
    third_party_assignment_id="<third-party-assignment-uuid>",
    template_id="<template-uuid>",
)
```

#### Create a third-party personal data record

```python
record = client.templates.create_third_party_pers_data({
    "template_id": "<template-uuid>",
    "third_party_id": "<third-party-uuid>",
    "third_party_function_code": "01",
    "sensitive_data_flag": False,
})
```

#### Update a third-party personal data record

```python
record = client.templates.update_third_party_pers_data(
    third_party_assignment_id="<third-party-assignment-uuid>",
    template_id="<template-uuid>",
    body={"third_party_id": "<third-party-uuid>", "third_party_function_code": "02", "sensitive_data_flag": True},
)
```

#### Delete a third-party personal data record

```python
client.templates.delete_third_party_pers_data(
    third_party_assignment_id="<third-party-assignment-uuid>",
    template_id="<template-uuid>",
)
```

---

### Retention rules (`client.retention`)

#### List retention rules

```python
rules = client.retention.list_rules(
    filter="lifecycleStatusCode eq '2'"
)
```

#### Get a retention rule by ID

```python
rule = client.retention.get_rule("<rule-uuid>")
print(rule.rule_name, rule.retention_period)
```

#### Create a retention rule

```python
rule = client.retention.create_rule({
    "rule_name": "7_year_financial",
    "purpose_name": "Marketing_Emails",
    "retention_period": 7,
    "jurisdiction_code": "EU",
    "controller_name": "AB_Corp",
    "consent_model_code": "1",
})
print(rule.rule_id)
```

#### Update a retention rule

```python
rule = client.retention.update_rule(
    "<rule-uuid>",
    {
        "rule_name": "7_year_financial",
        "purpose_name": "Marketing_Emails_Updated",
        "retention_period": 8,
        "jurisdiction_code": "DE",
        "controller_name": "AB_Corp_Updated",
        "consent_model_code": "2",
    },
)
```

#### Delete a retention rule

```python
client.retention.delete_rule("<rule-uuid>")
```

#### Set a retention rule active / inactive

```python
client.retention.set_rule_active("<rule-uuid>")
client.retention.set_rule_inactive("<rule-uuid>")
```

---

### Configuration reference data (`client.configuration`)

The configuration service manages all reference data that other entities reference
by ID or code.

#### Third parties

```python
# List
third_parties = client.configuration.list_third_parties()

# Get
tp = client.configuration.get_third_party("<third-party-uuid>")

# Create
tp = client.configuration.create_third_party({
    "third_party_name": "Analytics_Corp",
    "formatted_description": "Third-party analytics provider",
})
print(tp.third_party_id)

# Update
tp = client.configuration.update_third_party(
    "<third-party-uuid>",
    {"third_party_name": "Analytics_Corp", "formatted_description": "Updated analytics provider description"},
)

# Delete
client.configuration.delete_third_party("<third-party-uuid>")
```

#### Jurisdictions

```python
# List
jurisdictions = client.configuration.list_jurisdictions()

# Get
jurisdiction = client.configuration.get_jurisdiction("<jurisdiction-uuid>")

# Create
jurisdiction = client.configuration.create_jurisdiction({
    "jurisdiction_code": "EU",
})

# Update
jurisdiction = client.configuration.update_jurisdiction(
    "<jurisdiction-uuid>",
    {"jurisdiction_code": "DE"},
)

# Delete
client.configuration.delete_jurisdiction("<jurisdiction-uuid>")
```

#### Jurisdiction texts

```python
# List
texts = client.configuration.list_jurisdiction_texts()

# Create
text = client.configuration.create_jurisdiction_text({
    "jurisdiction_code": "<jurisdiction-code>",
    "language_code": "en",
    "description": "European Union General Data Protection Regulation",
})

# Update
text = client.configuration.update_jurisdiction_text(
    "<jurisdiction-text-uuid>",
    body={"language_code": "en", "description": "EU GDPR - Revised"},
)

# Delete
client.configuration.delete_jurisdiction_text("<jurisdiction-text-uuid>")
```

#### Languages

```python
# List
languages = client.configuration.list_languages()

# Get
language = client.configuration.get_language("en")
print(language.language_code)
```

Languages are read-only reference data - create and delete are not exposed.

#### Language descriptions

```python
# List
descriptions = client.configuration.list_language_descriptions()

# Create
desc = client.configuration.create_language_description({
    "language_code": "ar",
    "description_language_code": "en",
    "description": "Arabic",
})

# Update
desc = client.configuration.update_language_description(
    "<language-desc-uuid>",
    body={"language_code": "ar", "description_language_code": "en", "description": "Arabic (Updated)"},
)

# Delete
client.configuration.delete_language_description("<language-desc-uuid>")
```

#### Source infos

```python
# List
sources = client.configuration.list_source_infos()

# Get
source = client.configuration.get_source_info("<source-uuid>")

# Create
source = client.configuration.create_source_info({
    "source_name": "CRM_System",
    "description": "Customer relationship management platform",
})

# Update
source = client.configuration.update_source_info(
    "<source-uuid>",
    {"source_name": "CRM_System", "description": "CRM - Updated"},
)

# Delete
client.configuration.delete_source_info("<source-uuid>")
```

#### Controllers

```python
# List
controllers = client.configuration.list_controllers()

# Get
controller = client.configuration.get_controller("<controller-uuid>")

# Create
controller = client.configuration.create_controller({
    "controller_name": "AB_Corp",
    "source_name": "CRM_System",
    "description": "Main data controller",
})
print(controller.controller_id)

# Update
controller = client.configuration.update_controller(
    "<controller-uuid>",
    {"controller_name": "AB_Corp", "source_name": "CRM_System", "description": "AB Corp - Primary data controller"},
)

# Delete
client.configuration.delete_controller("<controller-uuid>")
```

#### Data subject types

```python
# List
types = client.configuration.list_data_subject_types()

# Get
dst = client.configuration.get_data_subject_type("<data-subject-type-uuid>")

# Create
dst = client.configuration.create_data_subject_type({
    "data_subject_type_name": "Employee",
    "master_data_source_name": "SAP_HR",
})

# Update
dst = client.configuration.update_data_subject_type(
    "<data-subject-type-uuid>",
    {"data_subject_type_name": "Internal_Employee", "master_data_source_name": "SAP_SuccessFactors"},
)

# Delete
client.configuration.delete_data_subject_type("<data-subject-type-uuid>")
```

#### Applications

```python
# List
apps = client.configuration.list_applications()

# Get
app = client.configuration.get_application("<application-uuid>")

# Create
app = client.configuration.create_application({
    "application_name": "HR_Portal",
    "source_name": "CRM_System",
    "description": "HR self-service portal",
})

# Update
app = client.configuration.update_application(
    "<application-uuid>",
    {"application_name": "HR_Portal_v2", "source_name": "CRM_System", "description": "HR portal version 2"},
)

# Delete
client.configuration.delete_application("<application-uuid>")
```

#### Master data sources

```python
# List
sources = client.configuration.list_master_data_sources()

# Get
source = client.configuration.get_master_data_source("<master-data-source-uuid>")

# Create
source = client.configuration.create_master_data_source({
    "master_data_source_name": "SAP_S4HANA",
    "description": "SAP S/4HANA master data source",
})

# Update
source = client.configuration.update_master_data_source(
    "<master-data-source-uuid>",
    {"master_data_source_name": "SAP_S4HANA_Cloud", "description": "SAP S/4HANA Cloud master data source"},
)

# Delete
client.configuration.delete_master_data_source("<master-data-source-uuid>")
```

#### Outbound channel types

```python
# List
channel_types = client.configuration.list_outbound_channel_types()

# Get
channel_type = client.configuration.get_outbound_channel_type("<outbound-channel-type-uuid>")

# Create
channel_type = client.configuration.create_outbound_channel_type({
    "outbound_channel_type_name": "Email",
    "description": "Email notification channel",
})

# Update
channel_type = client.configuration.update_outbound_channel_type(
    "<outbound-channel-type-uuid>",
    {"outbound_channel_type_name": "Email_Newsletter", "description": "Email newsletter channel"},
)

# Delete
client.configuration.delete_outbound_channel_type("<outbound-channel-type-uuid>")
```

## Error Handling

All SDK errors inherit from `ConsentSDKError`.

| Exception | HTTP status |
|---|---|
| `AuthenticationError` | 401 |
| `AuthorizationError` | 403 |
| `ValidationError` | 400 / 422 |
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ODataError` | other 4xx / 5xx |

Always catch `ConsentSDKError` or its subclasses around calls:

```python
from sap_cloud_sdk.core.dpi_ng.consent import (
    create_client,
    ConsentSDKConfig,
    ClientCredentialsAuth,
    ConsentSDKError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
)

config = ConsentSDKConfig(
    base_url="https://<your-consent-service-host>",
    auth=ClientCredentialsAuth(
        token_url="https://<your-xsuaa-host>/oauth/token",
        client_id="<client-id>",
        client_secret="<client-secret>",
    ),
)

try:
    with create_client(config=config) as client:
        consent = client.consents.get_consent("<consent-uuid>")
except AuthenticationError as e:
    # Token fetch failed or token was rejected - check credentials
    handle_error(e)
except NotFoundError as e:
    # Consent does not exist
    handle_error(e)
except ValidationError as e:
    # Bad request - check the request fields
    handle_error(e)
except ConsentSDKError as e:
    # Catch-all for any other SDK error
    handle_error(e)
```

## Context Manager

`ConsentClient` supports the context-manager protocol, which ensures the
underlying `requests.Session` is closed when the block exits:

```python
from sap_cloud_sdk.core.dpi_ng.consent import (
    create_client,
    ConsentSDKConfig,
    ClientCredentialsAuth,
)

config = ConsentSDKConfig(
    base_url="https://<your-consent-service-host>",
    auth=ClientCredentialsAuth(
        token_url="https://<your-xsuaa-host>/oauth/token",
        client_id="<client-id>",
        client_secret="<client-secret>",
    ),
)

with create_client(config=config) as client:
    consents = client.consents.list_consents(top=10)
# session is closed here
```

Or call `client.close()` explicitly when not using `with`.
