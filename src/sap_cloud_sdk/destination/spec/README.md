# Destination Service SDK Module

This module from the Cloud SDK manages the SAP BTP Destination Service, which aims to offer an easy way to centralize connection details and create HTTP clients from it.

## API Spec

[BTP Destination Service API Spec](api_spec.yaml)

[API Hub](https://api.sap.com/api/SAP_CP_CF_Connectivity_Destination/resource/Find_a_Destination)

API Spec is the authoritative API contract for endpoints, parameters, schemas, and responses.

Endpoint categories overview:
- Destinations: /v1/subaccountDestinations, /v1/instanceDestinations
- Fragments: /v1/subaccountDestinationFragments, /v1/instanceDestinationFragments
- Certificates: /v1/subaccountCertificates, /v1/instanceCertificates

## Environment Details

Destination Service uses OAuth 2.0 with client credentials grant type. The credentials can be found on binding. When getting destinations from provider level, token URL can be used from `url` property on binding; from subscriber, the domain needs to be replaced by the tenant subdomain. The credentials will be available from a volume mount with the following path `/etc/secrets/appfnd/destination/{instance-name}/`.

### Service Binding

```json
{
  "clientid": "{clientid}",
  "credential-type": "binding-secret",
  "clientsecret": "{clientsecret}",
  "uri": "https://destination-configuration.cfapps.{region}.hana.ondemand.com",
  "url": "https://{provider}.authentication.{region}.hana.ondemand.com",
  "uaadomain": "authentication.{region}.hana.ondemand.com",
  "instanceid": "instanceid",
  "verificationkey": "-----BEGIN PUBLIC KEY-----\n{verificationkey}\n-----END PUBLIC KEY-----",
  "identityzone": "{provider}",
  "tenantid": "{tenantid}"
}
```

## Integration Details

Destination objects can be declared at the service instance level or the sub-account level. They can originate from either the provider or the subscriber/consumer sub-account.

To manage this, we use `Level` and `AccessStrategy` parameters.

### Level

Determines the level at which the destination is declared. Possible values are:
- `SERVICE_INSTANCE`: Service instance level.
- `SUB_ACCOUNT`: Sub-account level.

It defines which API path is called:
- `level = SUB_ACCOUNT` -> `/v1/subaccountDestinations`
- `level = SERVICE_INSTANCE` -> `/v1/instanceDestinations`

### AccessStrategy

Determines the order of preference when resolving destinations. Possible values are:
- `SUBSCRIBER_ONLY`: Use only destinations from the subscriber sub-account.
- `PROVIDER_ONLY`: Use only destinations from the provider sub-account.
- `SUBSCRIBER_FIRST`: Prefer destinations from the subscriber sub-account, but fall back to the provider sub-account if none are found. (default)
- `PROVIDER_FIRST`: Prefer destinations from the provider sub-account, but fall back to the subscriber sub-account if none are found.

It defines how token is generated, if it should use provider or tenant sub-domain:
- `strategy = SUBSCRIBER_ONLY` -> `https://{tenant-subdomain}.authentication.{region}.hana.ondemand.com/oauth/token`
- `strategy = PROVIDER_ONLY` -> `https://{provider}.authentication.{region}.hana.ondemand.com/oauth/token`
- `strategy = SUBSCRIBER_FIRST | PROVIDER_FIRST` -> Both tokens should be generated with a specific order

## Types

**Destination:**
```json
{
    "name": "name",
    "type": "HTTP",
    "description": "description",
    "url": "https://url",
    "proxyType": "Internet",
    "authentication": "authentication_type",
    "properties": [
        {
            "key": "String",
            "value": "String"
        }
    ]
}
```

**Fragment:**
```json
{
    "name": "fragment-name",
    "properties": {
        "URL": "https://override-url",
        "Authentication": "OAuth2ClientCredentials",
        "tokenServiceURL": "https://auth.example.com/oauth/token"
    }
}
```

**Certificate:**

```json
{
    "name": "certificate-name.pem",
    "content": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
    "type": "PEM",
    "properties": [
      {
        "key": "String",
        "value": "String"
      }
    ]
}
```

**Note:** Certificate `Content` should be base64-encoded. Supported types include PEM, JKS, P12, and other certificate formats supported by the Destination Service.

### Properties

List of destination properties depends on destination type and authentication type. We could have an interface for DestinationProperties with multiple implementations for each type. We should also consider custom properties. So anyway it can include unmapped attributes.

## Pagination and Filtering

The SDK supports pagination and filtering for list operations on destinations and certificates.

### Pagination

Pagination is controlled through the `ListOptions` filter parameter:

```python
from sap_cloud_sdk.destination._models import ListOptions

# Create filter with pagination
filter_opts = ListOptions(
    page=1,              # Page number (1-based)
    page_size=10,        # Number of items per page
    page_count=True,     # Request total page count in response headers
    entity_count=True    # Request total entity count in response headers
)

# List destinations with pagination
result = client.list_instance_destinations(filter=filter_opts)

# Access pagination info
if result.pagination:
    print(f"Total items: {result.pagination.total_count}")
    print(f"Current page: {result.pagination.page}")
    print(f"Page size: {result.pagination.page_size}")
    print(f"Has next: {result.pagination.has_next}")
```

The response includes a `PagedResult` object with:
- `items`: List of destinations/certificates
- `pagination`: Pagination metadata (only present if pagination parameters were provided)
  - `total_count`: Total number of items available
  - `page`: Current page number
  - `page_size`: Number of items per page
  - `has_next`: Boolean indicating if more pages are available

### Filtering

List operations support filtering by name:

```python
from sap_cloud_sdk.destination._models import ListOptions

# Filter by specific names
filter_opts = ListOptions(filter_names=["dest1", "dest2", "dest3"])
destinations = client.list_instance_destinations(filter=filter_opts)

# Combine filter with pagination
filter_opts = ListOptions(
    filter_names=["dest1", "dest2"],
    page=1,
    page_size=10
)
destinations = client.list_instance_destinations(filter=filter_opts)
```

Available filter parameters:
- `filter_names`: List of destination/certificate names to filter by (uses API `$filter` parameter with Name in-list operator)
- `page`: Page number for pagination
- `page_size`: Number of items per page
- `page_count`: Whether to include total page count in response headers
- `entity_count`: Whether to include total entity count in response headers

## Error Handling

The SDK defines specific exception types for error scenarios:

### Exception Types

**`HttpError`**: Raised for HTTP-level errors (4xx, 5xx responses)
- Attributes:
  - `status_code`: HTTP status code (e.g., 404, 500)
  - `message`: Error message from the response

**`DestinationOperationError`**: Raised for operation-level errors
- Wraps HTTP errors with additional context
- Raised for validation errors (e.g., missing tenant for subscriber access)
- Raised for response parsing failures

### Common Error Scenarios

```python
from sap_cloud_sdk.destination import create_client, AccessStrategy
from sap_cloud_sdk.destination.exceptions import HttpError, DestinationOperationError

client = create_client()

# Scenario 1: Destination not found (returns None, no exception)
dest = client.get_instance_destination("non-existent")
if dest is None:
    print("Destination not found")

# Scenario 2: Missing tenant for subscriber access
try:
    dest = client.get_subaccount_destination(
        "my-dest",
        access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
        tenant=None  # Error: tenant required for subscriber access
    )
except DestinationOperationError as e:
    print(f"Operation error: {e}")

# Scenario 3: HTTP error (propagated from API)
try:
    client.create_destination(invalid_dest, level=Level.SUB_ACCOUNT)
except HttpError as e:
    print(f"HTTP error {e.status_code}: {e.message}")
except DestinationOperationError as e:
    print(f"Operation error: {e}")
```

### Error Response Handling

- **404 Not Found**: For get operations, returns `None` instead of raising an exception
- **Other HTTP errors**: Propagated as `HttpError` exceptions
- **Validation errors**: Raised as `DestinationOperationError` before making API calls
- **Parsing errors**: Raised as `DestinationOperationError` when response cannot be parsed

## Module Functionalities

### Destination

**List Destinations**: `dest.list_instance_destinations(filter)`, `dest.list_subaccount_destinations(access_strategy, tenant, filter)`

Returns a list of destinations based on a few options and filters (by name, by tenant, etc).

Consumed APIs:
- `GET /v1/subaccountDestinations`
- `GET /v1/instanceDestinations`

**Consume Destination**: `dest.get_instance_destination(name)`, `dest.get_subaccount_destination(name, access_strategy, tenant)`

Returns a specific destination by name.

Consumed APIs:
- `GET /v1/subaccountDestinations/{name}`
- `GET /v1/instanceDestinations/{name}`

**Create Destination**: `dest.create_destination(destination, level)`

Allows consumer to create a destination on `provider`, `subscriber` and `sub-account` or `instance` levels.

Consumed APIs:
- `POST /v1/subaccountDestinations`
- `POST /v1/instanceDestinations`

**Update Destination**: `dest.update_destination(destination, level)`

Allows consumer to update a specific destination.

Consumed APIs:
- `PUT /v1/subaccountDestinations`
- `PUT /v1/instanceDestinations`

**Delete Destination**: `dest.delete_destination(name, level)`

Allows consumer to delete a specific destination.

Consumed APIs:
- `DELETE /v1/subaccountDestinations/{name}`
- `DELETE /v1/instanceDestinations/{name}`

### Fragments

**List Fragments**: `fragment.list_instance_fragments()`, `fragment.list_subaccount_fragments(access_strategy, tenant)`

Returns a list of fragments based on a few options and filters (by name, by tenant, etc).

Consumed APIs:
- `GET /v1/subaccountDestinationFragments`
- `GET /v1/instanceDestinationFragments`

**Consume Fragment**: `fragment.get_instance_fragment(name)`, `fragment.get_subaccount_fragment(name, access_strategy, tenant)`

Returns a specific fragment by name.

Consumed APIs:
- `GET /v1/subaccountDestinationFragments/{name}`
- `GET /v1/instanceDestinationFragments/{name}`

**Create Fragment**: `fragment.create_fragment(fragment, level)`

Allows consumer to create a fragment on `provider`, `subscriber` and `sub-account` or `instance` levels.

Consumed APIs:
- `POST /v1/subaccountDestinationFragments`
- `POST /v1/instanceDestinationFragments`

**Update Fragment**: `fragment.update_fragment(fragment, level)`

Allows consumer to update a specific fragment.

Consumed APIs:
- `PUT /v1/subaccountDestinationFragments`
- `PUT /v1/instanceDestinationFragments`

**Delete Fragment**: `fragment.delete_fragment(name, level)`

Allows consumer to delete a specific fragment.

Consumed APIs:
- `DELETE /v1/subaccountDestinationFragments/{name}`
- `DELETE /v1/instanceDestinationFragments/{name}`

### Certificate

**List Certificates**: `certificate.list_instance_certificates(filter)`, `certificate.list_subaccount_certificates(access_strategy, tenant, filter)`

Returns a list of certificates based on options and filters. Supports pagination through the `filter` parameter.

Consumed APIs:
- `GET /v1/subaccountCertificates`
- `GET /v1/instanceCertificates`

**Consume Certificate**: `certificate.get_instance_certificate(name)`, `certificate.get_subaccount_certificate(name, access_strategy, tenant)`

Returns a specific certificate by name.

Consumed APIs:
- `GET /v1/subaccountCertificates/{name}`
- `GET /v1/instanceCertificates/{name}`

**Create Certificate**: `certificate.create_certificate(certificate, level)`

Allows consumer to create a certificate on `provider`, `subscriber` and `sub-account` or `instance` levels.

Consumed APIs:
- `POST /v1/subaccountCertificates`
- `POST /v1/instanceCertificates`

**Update Certificate**: `certificate.update_certificate(certificate, level)`

Allows consumer to update a specific certificate.

Consumed APIs:
- `PUT /v1/subaccountCertificates`
- `PUT /v1/instanceCertificates`

**Delete Certificate**: `certificate.delete_certificate(name, level)`

Allows consumer to delete a specific certificate.

Consumed APIs:
- `DELETE /v1/subaccountCertificates/{name}`
- `DELETE /v1/instanceCertificates/{name}`

### HTTP Client

TBD: Future implementation

## Test Scenarios

Test scenarios are organized by resource type and operation. Integration tests are implemented in `tests/destination/integration/` directory using BDD (Behavior-Driven Development) with `.feature` files.

### Destination Operations

#### List Destinations
- **Instance Level**
  - ✓ List all instance destinations
  - ✓ List with pagination (page, page_size)
  - ✓ List with name filter
  - ✓ Empty list when no destinations exist

- **Subaccount Level**
  - ✓ List with PROVIDER_ONLY access strategy
  - ✓ List with SUBSCRIBER_ONLY access strategy
  - ✓ List with SUBSCRIBER_FIRST access strategy
  - ✓ List with PROVIDER_FIRST access strategy

#### Get Destination
- **Instance Level**
  - ✓ Destination found
  - ✓ Destination not found (returns None)

- **Subaccount Level - PROVIDER_ONLY**
  - ✓ Destination found
  - ✓ Destination not found

- **Subaccount Level - PROVIDER_FIRST**
  - ✓ Destination found on provider
  - ✓ Destination found on subscriber (fallback)
  - ✓ Destination not found
  - ✓ Error when tenant not provided

- **Subaccount Level - SUBSCRIBER_ONLY**
  - ✓ Destination found
  - ✓ Destination not found
  - ✓ Error when tenant not provided

- **Subaccount Level - SUBSCRIBER_FIRST**
  - ✓ Destination found on subscriber
  - ✓ Destination found on provider (fallback)
  - ✓ Destination not found
  - ✓ Error when tenant not provided

#### Create Destination
- ✓ Successfully create instance destination
- ✓ Successfully create subaccount destination
- ✓ Handle creation failure (invalid data, duplicate name)

#### Update Destination
- ✓ Successfully update destination
- ✓ Handle update failure (destination not found, invalid data)

#### Delete Destination
- ✓ Successfully delete destination
  ✓ Handle deletion failure (destination not found)

### Certificate Operations

#### List Certificates
- **Instance Level**
  - ✓ List all instance certificates
  - ✓ List with pagination
  - ✓ List with name filter

- **Subaccount Level**
  - ✓ List with all access strategies (PROVIDER_ONLY, SUBSCRIBER_ONLY, SUBSCRIBER_FIRST, PROVIDER_FIRST)

#### Get Certificate
- **Instance Level**
  - ✓ Certificate found
  - ✓ Certificate not found (returns None)

- **Subaccount Level**
  - ✓ Get with all access strategies
  - ✓ Validate tenant requirements for subscriber access

#### Create Certificate
- ✓ Successfully create certificate
- ✓ Handle creation failure

#### Update Certificate
- ✓ Successfully update certificate
- ✓ Handle update failure

#### Delete Certificate
- ✓ Successfully delete certificate
- ✓ Verify deletion (certificate not found after delete)

### Fragment Operations

#### List Fragments
- **Instance Level**
  - ✓ List all instance fragments
  - ✓ Empty list when no fragments exist

- **Subaccount Level**
  - ✓ List with all access strategies

#### Get Fragment
- **Instance Level**
  - ✓ Fragment found
  - ✓ Fragment not found (returns None)

- **Subaccount Level**
  - ✓ Get with all access strategies
  - ✓ Validate tenant requirements

#### Create Fragment
- ✓ Successfully create fragment
- ✓ Handle creation failure

#### Update Fragment
- ✓ Successfully update fragment
- ✓ Handle update failure

#### Delete Fragment
- ✓ Successfully delete fragment
- ✓ Verify deletion

### Test Files
- `tests/destination/integration/destination.feature` - Destination test scenarios
- `tests/destination/integration/certificate.feature` - Certificate test scenarios
- `tests/destination/integration/fragment.feature` - Fragment test scenarios
- `tests/destination/integration/test_destination_bdd.py` - BDD test implementation

## References

- [HTTP Destinations Properties](https://help.sap.com/docs/connectivity/sap-btp-connectivity-cf/server-certificate-authentication)
- [Multitenancy in Destination Service](https://help.sap.com/docs/connectivity/sap-btp-connectivity-cf/multitenancy-in-destination-service)
- [Accelerator Hub](https://api.sap.com/api/SAP_CP_CF_Connectivity_Destination/overview)
