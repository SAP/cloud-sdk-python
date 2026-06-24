# Consent SDK  -  User Guide

## Installation

```bash
pip install sap-cloud-sdk
```

Requires Python 3.11+. The SDK depends on [python-odata](https://pypi.org/project/python-odata/) for entity modelling and OData query building.

---

## Quick start

```python
from sap_cloud_sdk.core.dpi_ng.consent import create_client, BearerTokenAuth

with create_client(
    base_url="https://<your-consent-service-host>",
    auth=BearerTokenAuth("<token>"),
) as client:
    # List consents with an OData filter
    consents = client.consents.list_consents(filter="lifecycle_status_code eq '1'")
    for c in consents:
        print(c.consent_id, c.lifecycle_status_code)
```

---

## Authentication

Pass one of the built-in `AuthProvider` implementations to `create_client`:

| Class | When to use |
|---|---|
| `BearerTokenAuth(token)` | You hold a pre-fetched token and manage refresh yourself |
| `ClientCredentialsAuth(token_url, client_id, client_secret)` | OAuth2 client credentials; token is fetched and refreshed automatically |
| `ClientCertificateAuth(cert_file, key_file, ca_file=None)` | Mutual TLS with a client certificate and key |

Custom auth providers implement `AuthProvider.apply(session: requests.Session)`.

---

## Client structure

`ConsentClient` exposes five service attributes:

| Attribute | OData service | Purpose |
|---|---|---|
| `client.consents` | `consentServices` | Consent creation, withdrawal, termination, reads |
| `client.purposes` | `consentPurposeExternalServices` | Purpose CRUD and lifecycle |
| `client.templates` | `consentTemplateExternalServices` | Template CRUD, lifecycle, third-party assignment |
| `client.retention` | `consentRetentionExternalServices` | Retention rule CRUD and lifecycle |
| `client.configuration` | `consentConfigurationExternalServices` | Reference data (controllers, applications, jurisdictions, ...) |

---

## Entity model (python-odata)

Entity classes are defined using [python-odata](https://pypi.org/project/python-odata/) descriptors and live under `entities/`. Each `make_entities(Service)` factory binds the classes to a specific `ODataService` instance so that query and save operations go to the right endpoint.

### Property types

| Descriptor | OData type | Python type |
|---|---|---|
| `StringProperty` | `Edm.String` | `str` |
| `UUIDProperty` | `Edm.Guid` | `uuid.UUID` / `str` |
| `BooleanProperty` | `Edm.Boolean` | `bool` |
| `DatetimeProperty` | `Edm.DateTimeOffset` | `datetime` |
| `IntegerProperty` | `Edm.Int32` | `int` |

Properties declared with `primary_key=True` form the entity key used by `GET` and `DELETE` requests.

### Reading a field

```python
purpose = client.purposes.list_purposes()[0]
print(purpose.purpose_id)          # uuid.UUID
print(purpose.purpose_name)        # str
print(purpose.sensitive_data_flag) # bool
```

---

## Querying

All `list_*` methods accept OData query kwargs:

| Kwarg | OData option | Example |
|---|---|---|
| `filter` | `$filter` | `filter="lifecycle_status_code eq '2'"` |
| `top` | `$top` | `top=10` |
| `skip` | `$skip` | `skip=20` |
| `orderby` | `$orderby` | `orderby="changed_at desc"` |

```python
# First page of active purposes
active = client.purposes.list_purposes(filter="lifecycle_status_code eq '2'", top=50)

# A single consent by UUID
consent = client.consents.get_consent("3fa85f64-5717-4562-b3fc-2c963f66afa6")
```

---

## Creating and saving entities

Entities are created by instantiating the class, setting attributes, and calling `save` (which issues a `POST` for new entities and a `PATCH` for dirty existing entities).

```python
# Create a new controller via configuration service
ctrl = client.configuration.create_controller({
    "controller_name": "AB Corp",
    "description": "Main data controller",
})
print(ctrl.controller_id)  # UUID assigned by the service
```

Internally the service calls `ODataClient.save(entity)`, which delegates to `entity.__odata_service__.save(entity)`.

---

## OData actions

Actions that are not standard CRUD are called via `ODataClient.call_action` and are exposed as named methods.

### Consent creation from a template

```python
from sap_cloud_sdk.core.dpi_ng.consent import CreateConsentRequest

request = CreateConsentRequest(
    data_subject_id="user@example.com",
    template_name="<template-name>",
    language_code="EN",
    data_subject_type_name="<type-name>",
    jurisdiction_code="<jurisdiction-code>",
)
consents = client.consents.create_consent_from_template(request)
```

### Async consent creation

```python
result = client.consents.create_consent_from_template_async(request)
# result.request_id, result.status

# Poll until done
status = client.consents.get_async_consent_status(result.request_id)
```

### Withdraw / terminate

```python
from sap_cloud_sdk.core.dpi_ng.consent import WithdrawConsentRequest

client.consents.withdraw_consent(
    WithdrawConsentRequest(consent_id="<uuid>", withdrawn_by="User request")
)
client.consents.terminate_consent(
    WithdrawConsentRequest(consent_id="<uuid>", withdrawn_by="Contract end")
)
```

### Lifecycle transitions (purposes, templates, retention)

```python
client.purposes.set_purpose_active(purpose_id)
client.purposes.set_purpose_inactive(purpose_id)

client.templates.set_template_active(template_id)
client.templates.set_template_inactive(template_id)

client.retention.set_rule_active(rule_id)
client.retention.set_rule_inactive(rule_id)
```

---

## Error handling

All SDK errors inherit from `ConsentSDKError`.

| Exception | HTTP status |
|---|---|
| `AuthenticationError` | 401 |
| `AuthorizationError` | 403 |
| `ValidationError` | 400 / 422 |
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ODataError` | other 4xx / 5xx |

```python
from sap_cloud_sdk.core.dpi_ng.consent import NotFoundError, ValidationError

try:
    consent = client.consents.get_consent(some_id)
except NotFoundError:
    print("Consent not found")
except ValidationError as exc:
    print("Bad request:", exc)
```

---

## Context manager

Always use the client as a context manager so the underlying `requests.Session` is closed properly:

```python
with create_client(base_url=..., auth=...) as client:
    ...
# session is closed here
```

Or call `client.close()` explicitly when not using `with`.
