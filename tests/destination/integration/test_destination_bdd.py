"""BDD step definitions for Destination integration tests."""

import concurrent.futures
from typing import List, Optional

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.destination import (
    Destination,
    Fragment,
    Certificate,
    Label,
    Level,
    AccessStrategy,
    ListOptions,
    ConsumptionOptions,
    PatchLabels,
)
from sap_cloud_sdk.destination.exceptions import (
    HttpError,
    DestinationOperationError,
)
from sap_cloud_sdk.destination.utils._pagination import PagedResult

# Load scenarios from feature files
scenarios("destination.feature")
scenarios("fragment.feature")
scenarios("certificate.feature")


# ==================== CONTEXT CLASS ====================

class ScenarioContext:
    """Context to store test state between steps."""

    def __init__(self):
        self.destination: Optional[Destination] = None
        self.destinations: List[Destination] = []
        self.fragment: Optional[Fragment] = None
        self.fragments: List[Fragment] = []
        self.certificate: Optional[Certificate] = None
        self.certificates: List[Certificate] = []
        self.retrieved_destination: Optional[Destination] = None
        self.retrieved_destinations: Optional[PagedResult[Destination]] = None
        self.retrieved_fragment: Optional[Fragment] = None
        self.retrieved_fragments: List[Fragment] = []
        self.retrieved_certificate: Optional[Certificate] = None
        self.retrieved_certificates: Optional[PagedResult[Certificate]] = None
        self.operation_success: bool = False
        self.operation_error: Optional[Exception] = None
        self.cleanup_destinations: List[tuple] = []  # (name, level, tenant)
        self.cleanup_fragments: List[tuple] = []  # (name, level, tenant)
        self.cleanup_certificates: List[tuple] = []  # (name, level, tenant)
        self.concurrent_results: List[bool] = []
        self.use_network_failure_client: bool = False
        self.updated_certificate_content: Optional[str] = None
        self.tenant: Optional[str] = None
        self.retrieved_labels: List[Label] = []


@pytest.fixture
def context():
    """Provide a fresh test context for each scenario."""
    return ScenarioContext()


# ==================== BACKGROUND STEPS ====================

@given("the destination service is available")
def destination_service_available(destination_client, fragment_client, certificate_client):
    """Verify that destination service clients are available."""
    assert destination_client is not None
    assert fragment_client is not None
    assert certificate_client is not None


@given("I have valid destination clients")
def have_valid_clients(destination_client, fragment_client, certificate_client):
    """Verify all clients are properly configured."""
    assert destination_client is not None
    assert fragment_client is not None
    assert certificate_client is not None


@given("I have valid fragment clients")
def have_valid_fragment_clients(fragment_client):
    """Verify fragment client is properly configured."""
    assert fragment_client is not None


# ==================== DESTINATION GIVEN STEPS ====================

@given(parsers.parse('I have a destination named "{name}" of type "{dest_type}"'))
def have_destination(context, name, dest_type):
    """Create a destination object with given name and type."""
    context.destination = Destination(
        name=name,
        type=dest_type,
    )


@given(parsers.parse('the destination has URL "{url}"'))
def destination_has_url(context, url):
    """Set destination URL."""
    context.destination.url = url


@given(parsers.parse('the destination has proxy type "{proxy_type}"'))
def destination_has_proxy_type(context, proxy_type):
    """Set destination proxy type."""
    context.destination.proxy_type = proxy_type


@given(parsers.parse('the destination has authentication "{auth}"'))
def destination_has_authentication(context, auth):
    """Set destination authentication type."""
    context.destination.authentication = auth


@given(parsers.parse('the destination has property "{key}" with value "{value}"'))
def destination_has_property(context, key, value):
    """Add a custom property to the destination."""
    context.destination.properties[key] = value


@given("I have a destination with empty name")
def have_destination_empty_name(context):
    """Create a destination with empty name."""
    context.destination = Destination(
        name="",
        type="HTTP",
        url="https://example.com",
    )


@given("I have multiple instance destinations:")
def have_multiple_instance_destinations(context, datatable):
    """Prepare for multiple instance destinations from table."""
    context.destinations = []
    # Parse the datatable (skip header row)
    # datatable is a list of lists: [['name', 'type', 'url'], ['value1', 'value2', 'value3'], ...]
    for row in datatable[1:]:
        context.destinations.append(
            Destination(
                name=row[0],
                type=row[1],
                url=row[2],
                authentication="NoAuthentication"
            )
        )


@given("I have multiple subaccount destinations:")
def have_multiple_subaccount_destinations(context, datatable):
    """Prepare for multiple subaccount destinations from table."""
    context.destinations = []
    # Parse the datatable (skip header row)
    # datatable is a list of lists: [['name', 'type', 'url'], ['value1', 'value2', 'value3'], ...]
    for row in datatable[1:]:
        context.destinations.append(
            Destination(
                name=row[0],
                type=row[1],
                url=row[2],
                authentication="NoAuthentication"
            )
        )


@given(parsers.parse('I have multiple destinations to create simultaneously'))
def have_concurrent_destinations(context):
    """Prepare destinations for concurrent operations."""
    context.destinations = [
        Destination(name=f"concurrent-test-{i}", type="HTTP", url=f"https://concurrent{i}.example.com",
                    authentication="NoAuthentication")
        for i in range(5)
    ]


# ==================== FRAGMENT GIVEN STEPS ====================

@given(parsers.parse('I have a fragment named "{name}"'))
def have_fragment(context, name):
    """Create a fragment object with given name."""
    context.fragment = Fragment(name=name)


@given(parsers.parse('the fragment has property "{key}" with value "{value}"'))
def fragment_has_property(context, key, value):
    """Add a property to the fragment."""
    context.fragment.properties[key] = value


@given("I have multiple subaccount fragments:")
def have_multiple_subaccount_fragments(context, datatable):
    """Prepare for multiple subaccount fragments from table."""
    context.fragments = []
    # Parse the datatable (skip header row)
    # datatable is a list of lists: [['name', 'property1', 'value1'], ['fragname', 'prop', 'val'], ...]
    for row in datatable[1:]:
        frag = Fragment(name=row[0])
        frag.properties[row[1]] = row[2]
        context.fragments.append(frag)


# ==================== CERTIFICATE GIVEN STEPS ====================

@given(parsers.parse('I have a certificate named "{name}"'))
def have_certificate(context, name):
    """Create a certificate object with given name."""
    context.certificate = Certificate(name=name, content="")


@given(parsers.parse('the certificate has type "{cert_type}"'))
def certificate_has_type(context, cert_type):
    """Set certificate type."""
    context.certificate.type = cert_type


@given("the certificate has valid PEM content")
def certificate_has_pem_content(context, sample_pem_certificate):
    """Set valid PEM certificate content."""
    context.certificate.content = sample_pem_certificate


@given("I have multiple subaccount certificates:")
def have_multiple_subaccount_certificates(context, datatable, sample_pem_certificate):
    """Prepare for multiple subaccount certificates from table."""
    context.certificates = []
    # Parse the datatable (skip header row)
    # datatable is a list of lists: [['name', 'type'], ['certname', 'PEM'], ...]
    for row in datatable[1:]:
        context.certificates.append(
            Certificate(
                name=row[0],
                type=row[1],
                content=sample_pem_certificate
            )
        )


# ==================== FAILURE SIMULATION STEPS ====================

@given("the destination service is configured with an unreachable endpoint")
def destination_service_unreachable(context):
    """Mark context to use network failure client."""
    context.use_network_failure_client = True


@given("the destination service returns authentication failure")
def destination_service_auth_failure(context):
    """Mark context for authentication failure."""
    context.use_auth_failure_client = True


@given(parsers.parse('I use tenant "{tenant}"'))
def use_tenant(context, tenant):
    """Set the tenant to use for subscriber access."""
    context.tenant = tenant


# ==================== DESTINATION WHEN STEPS ====================

@when("I create the destination at instance level")
def create_destination_instance(context, destination_client):
    """Create destination at instance level."""
    # Try to delete first to avoid 409 conflicts (idempotent cleanup)
    try:
        destination_client.delete_destination(context.destination.name, level=Level.SERVICE_INSTANCE)
    except Exception:
        # Ignore cleanup errors (destination may not exist)
        pass


    try:
        destination_client.create_destination(context.destination, level=Level.SERVICE_INSTANCE)
        context.operation_success = True
        context.cleanup_destinations.append((context.destination.name, Level.SERVICE_INSTANCE, None))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I create the destination at subaccount level")
def create_destination_subaccount(context, destination_client):
    """Create destination at subaccount level."""
    try:
        destination_client.create_destination(context.destination, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        context.cleanup_destinations.append((context.destination.name, Level.SUB_ACCOUNT, None))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I create all instance destinations")
def create_all_instance_destinations(context, destination_client):
    """Create all destinations at instance level."""
    context.concurrent_results = []
    for dest in context.destinations:
        try:
            destination_client.create_destination(dest, level=Level.SERVICE_INSTANCE)
            context.concurrent_results.append(True)
            context.cleanup_destinations.append((dest.name, Level.SERVICE_INSTANCE, None))
        except Exception:
            context.concurrent_results.append(False)


@when("I create all subaccount destinations")
def create_all_subaccount_destinations(context, destination_client):
    """Create all destinations at subaccount level."""
    context.concurrent_results = []
    for dest in context.destinations:
        # Try to delete first to avoid 409 conflicts (idempotent cleanup)
        try:
            destination_client.delete_destination(dest.name, level=Level.SUB_ACCOUNT)
        except Exception:
            # Ignore cleanup errors (destination may not exist)
            pass

        try:
            destination_client.create_destination(dest, level=Level.SUB_ACCOUNT)
            context.concurrent_results.append(True)
            context.cleanup_destinations.append((dest.name, Level.SUB_ACCOUNT, None))
        except Exception:
            context.concurrent_results.append(False)


@when("I attempt to create the destination at subaccount level")
def attempt_create_destination_subaccount(context, destination_client, failure_simulation):
    """Attempt to create destination at subaccount level with potential failure."""
    try:
        if context.use_network_failure_client:
            client = failure_simulation.create_client_with_network_failure()
        elif getattr(context, 'use_auth_failure_client', False):
            client = failure_simulation.create_client_with_auth_failure()
        else:
            client = destination_client

        client.create_destination(context.destination, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        context.cleanup_destinations.append((context.destination.name, Level.SUB_ACCOUNT, None))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I update the destination URL to "{url}"'))
def update_destination_url(context, url):
    """Update destination URL."""
    context.destination.url = url


@when("I update the destination at subaccount level")
def update_destination_subaccount(context, destination_client):
    """Update destination at subaccount level."""
    try:
        destination_client.update_destination(context.destination, level=Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I delete the subaccount destination "{name}"'))
def delete_subaccount_destination(context, destination_client, name):
    """Delete a subaccount destination."""
    try:
        destination_client.delete_destination(name, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        # Remove from cleanup list if present
        context.cleanup_destinations = [(n, l, t) for n, l, t in context.cleanup_destinations if n != name]
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get instance destination "{name}"'))
def get_instance_destination(context, destination_client, name):
    """Get an instance destination."""
    try:
        context.retrieved_destination = destination_client.get_instance_destination(name)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get subaccount destination "{name}" with "{strategy}" access strategy'))
def get_subaccount_destination_with_access_strategy(context, destination_client, name, strategy):
    """Get a subaccount destination with access strategy."""
    try:
        access_strategy = AccessStrategy[strategy]
        context.retrieved_destination = destination_client.get_subaccount_destination(
            name=name,
            access_strategy=access_strategy,
            tenant=context.tenant
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I list instance destinations")
def list_instance_destinations(context, destination_client):
    """List all instance-level destinations."""
    try:
        context.retrieved_destinations = destination_client.list_instance_destinations()
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list subaccount destinations with "{strategy}" access strategy'))
def list_subaccount_destinations_with_access_strategy(context, destination_client, strategy):
    """List subaccount destinations with access strategy."""
    try:
        access_strategy = AccessStrategy[strategy]
        context.retrieved_destinations = destination_client.list_subaccount_destinations(
            access_strategy=access_strategy,
            tenant=context.tenant
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list subaccount destinations with "{strategy}" access strategy and label filter key "{key}" values "{value}"'))
def list_subaccount_destinations_with_label_filter(context, destination_client, strategy, key, value):
    """List subaccount destinations with access strategy and label filter."""
    try:
        access_strategy = AccessStrategy[strategy]
        filter_opts = ListOptions(filter_labels=[Label(key=key, values=[value])])
        context.retrieved_destinations = destination_client.list_subaccount_destinations(
            access_strategy=access_strategy,
            tenant=context.tenant,
            filter=filter_opts,
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list instance destinations filtered by names "{names}"'))
def list_instance_destinations_filtered(context, destination_client, names):
    """List instance destinations filtered by names."""
    try:
        name_list = [n.strip() for n in names.split(',')]
        filter_opts = ListOptions(filter_names=name_list)
        context.retrieved_destinations = destination_client.list_instance_destinations(filter=filter_opts)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I attempt to list instance destinations")
def attempt_list_instance_destinations(context, destination_client, failure_simulation):
    """Attempt to list instance destinations with potential failure."""
    try:
        if context.use_network_failure_client:
            client = failure_simulation.create_client_with_network_failure()
        else:
            client = destination_client

        context.retrieved_destinations = client.list_instance_destinations()
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I perform concurrent destination creation operations")
def perform_concurrent_destination_creation(context, destination_client):
    """Perform concurrent destination creation operations."""
    context.concurrent_results = []

    def create_dest(dest):
        try:
            destination_client.create_destination(dest, level=Level.SUB_ACCOUNT)
            context.cleanup_destinations.append((dest.name, Level.SUB_ACCOUNT, None))
            return True
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_dest, dest) for dest in context.destinations]
        context.concurrent_results = [f.result() for f in concurrent.futures.as_completed(futures)]


# ==================== V2 CONSUMPTION API WHEN STEPS ====================

@when(parsers.parse('I consume the destination "{name}" with fragment "{fragment_name}" and tenant context'))
def consume_destination_with_fragment_and_tenant(context, destination_client, name, fragment_name):
    """Consume destination using v2 API with both fragment and tenant."""
    try:
        options = ConsumptionOptions(
            fragment_name=fragment_name,
            tenant=context.tenant
        )
        context.retrieved_destination = destination_client.get_destination(name, options=options)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


# ==================== SUBSCRIBER WRITE WHEN STEPS ====================

@when("I create the destination at subaccount level for subscriber")
def create_destination_subaccount_subscriber(context, destination_client):
    """Create destination at subaccount level scoped to subscriber tenant."""
    try:
        destination_client.delete_destination(context.destination.name, level=Level.SUB_ACCOUNT, tenant=context.tenant)
    except Exception:
        pass

    try:
        destination_client.create_destination(context.destination, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
        context.cleanup_destinations.append((context.destination.name, Level.SUB_ACCOUNT, context.tenant))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I update the destination at subaccount level for subscriber")
def update_destination_subaccount_subscriber(context, destination_client):
    """Update destination at subaccount level scoped to subscriber tenant."""
    try:
        destination_client.update_destination(context.destination, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I delete the subaccount destination "{name}" for subscriber'))
def delete_subaccount_destination_subscriber(context, destination_client, name):
    """Delete a subaccount destination scoped to subscriber tenant."""
    try:
        destination_client.delete_destination(name, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
        context.cleanup_destinations = [(n, l, t) for n, l, t in context.cleanup_destinations if n != name]
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I create the fragment at subaccount level for subscriber")
def create_fragment_subaccount_subscriber(context, fragment_client):
    """Create fragment at subaccount level scoped to subscriber tenant."""
    try:
        fragment_client.delete_fragment(context.fragment.name, level=Level.SUB_ACCOUNT, tenant=context.tenant)
    except Exception:
        pass

    try:
        fragment_client.create_fragment(context.fragment, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
        context.cleanup_fragments.append((context.fragment.name, Level.SUB_ACCOUNT, context.tenant))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I update the fragment at subaccount level for subscriber")
def update_fragment_subaccount_subscriber(context, fragment_client):
    """Update fragment at subaccount level scoped to subscriber tenant."""
    try:
        fragment_client.update_fragment(context.fragment, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I delete the subaccount fragment "{name}" for subscriber'))
def delete_subaccount_fragment_subscriber(context, fragment_client, name):
    """Delete a subaccount fragment scoped to subscriber tenant."""
    try:
        fragment_client.delete_fragment(name, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
        context.cleanup_fragments = [(n, l, t) for n, l, t in context.cleanup_fragments if n != name]
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I create the certificate at subaccount level for subscriber")
def create_certificate_subaccount_subscriber(context, certificate_client):
    """Create certificate at subaccount level scoped to subscriber tenant."""
    try:
        certificate_client.delete_certificate(context.certificate.name, level=Level.SUB_ACCOUNT, tenant=context.tenant)
    except Exception:
        pass

    try:
        certificate_client.create_certificate(context.certificate, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
        context.cleanup_certificates.append((context.certificate.name, Level.SUB_ACCOUNT, context.tenant))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e
        print(f"Subscriber certificate creation failed: {type(e).__name__}: {e}")


@when("I update the certificate at subaccount level for subscriber")
def update_certificate_subaccount_subscriber(context, certificate_client):
    """Update certificate at subaccount level scoped to subscriber tenant."""
    try:
        certificate_client.update_certificate(context.certificate, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I delete the subaccount certificate "{name}" for subscriber'))
def delete_subaccount_certificate_subscriber(context, certificate_client, name):
    """Delete a subaccount certificate scoped to subscriber tenant."""
    try:
        certificate_client.delete_certificate(name, level=Level.SUB_ACCOUNT, tenant=context.tenant)
        context.operation_success = True
        context.cleanup_certificates = [(n, l, t) for n, l, t in context.cleanup_certificates if n != name]
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


# ==================== FRAGMENT WHEN STEPS ====================

@when("I create the fragment at subaccount level")
def create_fragment_subaccount(context, fragment_client):
    """Create fragment at subaccount level."""
    # Try to delete first to avoid 409 conflicts (idempotent cleanup)
    try:
        fragment_client.delete_fragment(context.fragment.name, level=Level.SUB_ACCOUNT)
    except Exception:
        # Ignore cleanup errors (destination may not exist)
        pass

    try:
        fragment_client.create_fragment(context.fragment, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        context.cleanup_fragments.append((context.fragment.name, Level.SUB_ACCOUNT, None))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I create the fragment at instance level")
def create_fragment_instance(context, fragment_client):
    """Create fragment at instance level."""
    # Try to delete first to avoid 409 conflicts (idempotent cleanup)
    try:
        fragment_client.delete_fragment(context.fragment.name, level=Level.SERVICE_INSTANCE)
    except Exception:
        # Ignore cleanup errors (destination may not exist)
        pass

    try:
        fragment_client.create_fragment(context.fragment, level=Level.SERVICE_INSTANCE)
        context.operation_success = True
        context.cleanup_fragments.append((context.fragment.name, Level.SERVICE_INSTANCE, None))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I create all instance fragments")
def create_all_instance_fragments(context, fragment_client):
    """Create all fragments at instance level."""
    context.concurrent_results = []
    for frag in context.fragments:
        try:
            fragment_client.create_fragment(frag, level=Level.SERVICE_INSTANCE)
            context.concurrent_results.append(True)
            context.cleanup_fragments.append((frag.name, Level.SERVICE_INSTANCE, None))
        except Exception:
            context.concurrent_results.append(False)


@when("I create all subaccount fragments")
def create_all_subaccount_fragments(context, fragment_client):
    """Create all fragments at subaccount level."""
    context.concurrent_results = []
    for frag in context.fragments:
        try:
            fragment_client.create_fragment(frag, level=Level.SUB_ACCOUNT)
            context.concurrent_results.append(True)
            context.cleanup_fragments.append((frag.name, Level.SUB_ACCOUNT, None))
        except Exception:
            context.concurrent_results.append(False)


@when(parsers.parse('I update the fragment property "{key}" to "{value}"'))
def update_fragment_property(context, key, value):
    """Update fragment property."""
    context.fragment.properties[key] = value


@when("I update the fragment at subaccount level")
def update_fragment_subaccount(context, fragment_client):
    """Update fragment at subaccount level."""
    try:
        fragment_client.update_fragment(context.fragment, level=Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I delete the subaccount fragment "{name}"'))
def delete_subaccount_fragment(context, fragment_client, name):
    """Delete a subaccount fragment."""
    try:
        fragment_client.delete_fragment(name, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        context.cleanup_fragments = [(n, l, t) for n, l, t in context.cleanup_fragments if n != name]
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get instance fragment "{name}"'))
def get_instance_fragment(context, fragment_client, name):
    """Get an instance fragment."""
    try:
        context.retrieved_fragment = fragment_client.get_instance_fragment(name=name)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get subaccount fragment "{name}" with "{strategy}" access strategy'))
def get_subaccount_fragment_with_access_strategy(context, fragment_client, name, strategy):
    """Get a subaccount fragment with access strategy."""
    try:
        access_strategy = AccessStrategy[strategy]
        context.retrieved_fragment = fragment_client.get_subaccount_fragment(
            name=name,
            tenant=context.tenant,
            access_strategy=access_strategy
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I list instance fragments")
def list_instance_fragments(context, fragment_client):
    """List instance fragments."""
    try:
        context.retrieved_fragments = fragment_client.list_instance_fragments()
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list subaccount fragments with "{strategy}" access strategy'))
def list_subaccount_fragments_with_access_strategy(context, fragment_client, strategy):
    """List subaccount fragments with access strategy."""
    try:
        access_strategy = AccessStrategy[strategy]
        context.retrieved_fragments = fragment_client.list_subaccount_fragments(
            access_strategy=access_strategy,
            tenant=context.tenant,
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list subaccount fragments with "{strategy}" access strategy and label filter key "{key}" values "{value}"'))
def list_subaccount_fragments_with_label_filter(context, fragment_client, strategy, key, value):
    """List subaccount fragments with access strategy and label filter."""
    try:
        access_strategy = AccessStrategy[strategy]
        filter_opts = ListOptions(filter_labels=[Label(key=key, values=[value])])
        context.retrieved_fragments = fragment_client.list_subaccount_fragments(
            access_strategy=access_strategy,
            tenant=context.tenant,
            filter=filter_opts,
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


# ==================== CERTIFICATE WHEN STEPS ====================

@when("I create the certificate at subaccount level")
def create_certificate_subaccount(context, certificate_client):
    """Create certificate at subaccount level."""
    try:
        certificate_client.create_certificate(context.certificate, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        context.cleanup_certificates.append((context.certificate.name, Level.SUB_ACCOUNT, None))
    except Exception as e:
        context.operation_success = False
        context.operation_error = e
        print(f"Certificate creation failed: {type(e).__name__}: {e}")


@when("I create all instance certificates")
def create_all_subaccount_certificates(context, certificate_client, sample_pem_certificate):
    """Create all certificates at subaccount level."""
    context.concurrent_results = []
    for cert in context.certificates:
        # Set content if not already set
        if not cert.content:
            cert.content = sample_pem_certificate
        try:
            certificate_client.create_certificate(cert, level=Level.SERVICE_INSTANCE)
            context.concurrent_results.append(True)
            context.cleanup_certificates.append((cert.name, Level.SERVICE_INSTANCE, None))
        except Exception:
            context.concurrent_results.append(False)


@when("I create all subaccount certificates")
def create_all_subaccount_certificates(context, certificate_client, sample_pem_certificate):
    """Create all certificates at subaccount level."""
    context.concurrent_results = []
    for cert in context.certificates:
        # Set content if not already set
        if not cert.content:
            cert.content = sample_pem_certificate
        try:
            certificate_client.create_certificate(cert, level=Level.SUB_ACCOUNT)
            context.concurrent_results.append(True)
            context.cleanup_certificates.append((cert.name, Level.SUB_ACCOUNT, None))
        except Exception:
            context.concurrent_results.append(False)


@when("I update the certificate content")
def update_certificate_content(context, sample_pem_certificate):
    """Update certificate content with new PEM data."""
    # Generate a new certificate
    context.updated_certificate_content = sample_pem_certificate
    context.certificate.content = context.updated_certificate_content


@when("I update the certificate at subaccount level")
def update_certificate_subaccount(context, certificate_client):
    """Update certificate at subaccount level."""
    try:
        certificate_client.update_certificate(context.certificate, level=Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I delete the subaccount certificate "{name}"'))
def delete_subaccount_certificate(context, certificate_client, name):
    """Delete a subaccount certificate."""
    try:
        certificate_client.delete_certificate(name, level=Level.SUB_ACCOUNT)
        context.operation_success = True
        context.cleanup_certificates = [(n, l, t) for n, l, t in context.cleanup_certificates if n != name]
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get instance certificate "{name}"'))
def get_instance_certificate(context, certificate_client, name):
    """Get an instance certificate."""
    try:
        context.retrieved_certificate = certificate_client.get_instance_certificate(name)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get subaccount certificate "{name}" with "{strategy}" access strategy'))
def get_subaccount_certificate_with_access_strategy(context, certificate_client, name, strategy):
    """Get a subaccount certificate with access strategy."""
    try:
        access_strategy = AccessStrategy[strategy]
        context.retrieved_certificate = certificate_client.get_subaccount_certificate(
            name=name,
            access_strategy=access_strategy,
            tenant=context.tenant
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when("I list instance certificates")
def list_instance_certificates(context, certificate_client):
    """List instance certificates."""
    try:
        context.retrieved_certificates = certificate_client.list_instance_certificates()
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list subaccount certificates with "{strategy}" access strategy'))
def list_subaccount_certificates_with_access_strategy(context, certificate_client, strategy):
    """List subaccount certificates with access strategy."""
    try:
        access_strategy = AccessStrategy[strategy]
        context.retrieved_certificates = certificate_client.list_subaccount_certificates(
            access_strategy=access_strategy,
            tenant=context.tenant
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I list subaccount certificates with "{strategy}" access strategy and label filter key "{key}" values "{value}"'))
def list_subaccount_certificates_with_label_filter(context, certificate_client, strategy, key, value):
    """List subaccount certificates with access strategy and label filter."""
    try:
        access_strategy = AccessStrategy[strategy]
        filter_opts = ListOptions(filter_labels=[Label(key=key, values=[value])])
        context.retrieved_certificates = certificate_client.list_subaccount_certificates(
            access_strategy=access_strategy,
            tenant=context.tenant,
            filter=filter_opts,
        )
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


# ==================== THEN STEPS - SUCCESS ====================

@then("the destination creation should be successful")
def destination_creation_successful(context):
    """Verify destination creation succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the destination should be consumed successfully")
def destination_consumed_successfully(context):
    """Verify destination was consumed via v2 API."""
    assert context.operation_success is True
    assert context.retrieved_destination is not None
    assert context.operation_error is None


@then(parsers.parse('the consumed destination should have URL "{url}"'))
def consumed_destination_url_should_be(context, url):
    """Verify consumed destination URL matches expected value."""
    assert context.retrieved_destination is not None
    assert context.retrieved_destination.url == url


@then("the destination update should be successful")
def destination_update_successful(context):
    """Verify destination update succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the destination deletion should be successful")
def destination_deletion_successful(context):
    """Verify destination deletion succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the destination should be retrieved successfully")
def destination_retrieved_successfully(context):
    """Verify destination was retrieved."""
    assert context.operation_success is True
    assert context.retrieved_destination is not None


@then("the fragment creation should be successful")
def fragment_creation_successful(context):
    """Verify fragment creation succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the fragment update should be successful")
def fragment_update_successful(context):
    """Verify fragment update succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the fragment deletion should be successful")
def fragment_deletion_successful(context):
    """Verify fragment deletion succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the fragment should be retrieved successfully")
def fragment_retrieved_successfully(context):
    """Verify fragment was retrieved."""
    assert context.operation_success is True
    assert context.retrieved_fragment is not None


@then("the certificate creation should be successful")
def certificate_creation_successful(context):
    """Verify certificate creation succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the certificate update should be successful")
def certificate_update_successful(context):
    """Verify certificate update succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the certificate deletion should be successful")
def certificate_deletion_successful(context):
    """Verify certificate deletion succeeded."""
    assert context.operation_success is True
    assert context.operation_error is None


@then("the certificate should be retrieved successfully")
def certificate_retrieved_successfully(context):
    """Verify certificate was retrieved."""
    assert context.operation_success is True
    assert context.retrieved_certificate is not None


@then("all destination creations should be successful")
def all_destination_creations_successful(context):
    """Verify all destination creations succeeded."""
    assert all(context.concurrent_results)


@then("all fragment creations should be successful")
def all_fragment_creations_successful(context):
    """Verify all fragment creations succeeded."""
    assert all(context.concurrent_results)


@then("all certificate creations should be successful")
def all_certificate_creations_successful(context):
    """Verify all certificate creations succeeded."""
    assert all(context.concurrent_results)


@then("all concurrent destination creations should be successful")
def all_concurrent_destination_creations_successful(context):
    """Verify all concurrent destination creations succeeded."""
    assert all(context.concurrent_results)


@then("the expected number of destinations should be created")
def expected_destinations_created(context):
    """Verify expected number of destinations were created."""
    assert len(context.concurrent_results) == len(context.destinations)


# ==================== THEN STEPS - NOT FOUND ====================

@then("the destination should not be found")
def destination_not_found(context):
    """Verify destination was not found."""
    assert context.retrieved_destination is None


@then("the fragment should not be found")
def fragment_not_found(context):
    """Verify fragment was not found."""
    assert context.retrieved_fragment is None


@then("the certificate should not be found")
def certificate_not_found(context):
    """Verify certificate was not found."""
    assert context.retrieved_certificate is None


# ==================== THEN STEPS - VALIDATION ====================

@then(parsers.parse('the destination URL should be "{url}"'))
def destination_url_should_be(context, url):
    """Verify destination URL matches expected value."""
    assert context.retrieved_destination is not None
    assert context.retrieved_destination.url == url


@then(parsers.parse('the destination should have property "{key}" with value "{value}"'))
def destination_should_have_property(context, key, value):
    """Verify destination has expected property value."""
    assert context.retrieved_destination is not None
    assert key in context.retrieved_destination.properties
    assert context.retrieved_destination.properties[key] == value


@then(parsers.parse('the fragment should have property "{key}" with value "{value}"'))
def fragment_should_have_property(context, key, value):
    """Verify fragment has expected property value."""
    assert context.retrieved_fragment is not None
    assert key in context.retrieved_fragment.properties
    assert context.retrieved_fragment.properties[key] == value


@then(parsers.parse('the certificate type should be "{cert_type}"'))
def certificate_type_should_be(context, cert_type):
    """Verify certificate type matches expected value."""
    assert context.retrieved_certificate is not None
    assert context.retrieved_certificate.type == cert_type


@then("the certificate should have updated content")
def certificate_has_updated_content(context):
    """Verify certificate content was updated."""
    assert context.retrieved_certificate is not None
    assert context.retrieved_certificate.content == context.updated_certificate_content


# ==================== THEN STEPS - LIST OPERATIONS ====================

@then(parsers.parse('the list should contain at least {count:d} destinations'))
def list_contains_at_least_destinations(context, count):
    """Verify list contains at least specified number of destinations."""
    items = context.retrieved_destinations.items
    assert len(items) >= count


@then(parsers.parse('the list should contain exactly {count:d} destinations'))
def list_contains_exactly_destinations(context, count):
    """Verify list contains exactly specified number of destinations."""
    items = context.retrieved_destinations.items
    assert len(items) == count


@then("the destination list should be retrieved successfully")
def destination_list_retrieved_successfully(context):
    """Verify destination list was retrieved successfully."""
    assert context.operation_success is True
    assert context.retrieved_destinations is not None


@then(parsers.parse('the destination "{name}" should be in the list'))
def destination_in_list(context, name):
    """Verify destination is in the list."""
    items = context.retrieved_destinations.items
    dest_names = [d.name for d in items]
    assert name in dest_names


@then(parsers.parse('the destination "{name}" should not be in the list'))
def destination_not_in_list(context, name):
    """Verify destination is not in the list."""
    items = context.retrieved_destinations.items
    dest_names = [d.name for d in items]
    assert name not in dest_names


@then(parsers.parse('the fragment list should contain at least {count:d} fragments'))
def fragment_list_contains_at_least(context, count):
    """Verify fragment list contains at least specified number of fragments."""
    items = context.retrieved_fragments
    assert len(items) >= count


@then("the fragment list should be retrieved successfully")
def fragment_list_retrieved_successfully(context):
    """Verify fragment list was retrieved successfully."""
    assert context.operation_success is True
    assert context.retrieved_fragments is not None


@then(parsers.parse('the fragment "{name}" should be in the list'))
def fragment_in_list(context, name):
    """Verify fragment is in the list."""
    items = context.retrieved_fragments
    frag_names = [f.name for f in items]
    assert name in frag_names


@then(parsers.parse('the fragment "{name}" should not be in the list'))
def fragment_not_in_list(context, name):
    """Verify fragment is not in the list."""
    items = context.retrieved_fragments
    frag_names = [f.name for f in items]
    assert name not in frag_names


@then(parsers.parse('the certificate list should contain at least {count:d} certificates'))
def certificate_list_contains_at_least(context, count):
    """Verify certificate list contains at least specified number of certificates."""
    items = context.retrieved_certificates.items
    assert len(items) >= count


@then("the certificate list should be retrieved successfully")
def certificate_list_retrieved_successfully(context):
    """Verify certificate list was retrieved successfully."""
    assert context.operation_success is True
    assert context.retrieved_certificates is not None


@then(parsers.parse('the certificate "{name}" should be in the list'))
def certificate_in_list(context, name):
    """Verify certificate is in the list."""
    items = context.retrieved_certificates.items
    cert_names = [c.name for c in items]
    assert name in cert_names


@then(parsers.parse('the certificate "{name}" should not be in the list'))
def certificate_not_in_list(context, name):
    """Verify certificate is not in the list."""
    items = context.retrieved_certificates.items
    cert_names = [c.name for c in items]
    assert name not in cert_names


# ==================== THEN STEPS - ERRORS ====================

@then("the destination creation should fail with a network error")
def destination_creation_network_error(context):
    """Verify destination creation failed with network error."""
    assert context.operation_success is False
    assert context.operation_error is not None
    # Network errors can be various exception types
    assert isinstance(context.operation_error, (HttpError, DestinationOperationError, Exception))


@then("the list operation should fail with a network error")
def list_operation_network_error(context):
    """Verify list operation failed with network error."""
    assert context.operation_success is False
    assert context.operation_error is not None
    assert isinstance(context.operation_error, (HttpError, DestinationOperationError, Exception))


@then("the operation should fail with a validation error")
def operation_validation_error(context):
    """Verify operation failed with validation error."""
    assert context.operation_success is False
    assert context.operation_error is not None


@then("the operation should fail with an authentication error")
def operation_authentication_error(context):
    """Verify operation failed with authentication error."""
    assert context.operation_success is False
    assert context.operation_error is not None


# ==================== CLEANUP STEPS ====================

@then(parsers.parse('I clean up the instance destination "{name}"'))
def cleanup_instance_destination(context, destination_client, name):
    """Clean up an instance-level destination."""
    try:
        destination_client.delete_destination(name, level=Level.SERVICE_INSTANCE)
        context.cleanup_destinations = [(n, l, t) for n, l, t in context.cleanup_destinations if n != name]
    except Exception:
        pass  # Ignore cleanup errors


@then(parsers.parse('I clean up the subaccount destination "{name}"'))
def cleanup_subaccount_destination(context, destination_client, name):
    """Clean up a subaccount destination."""
    try:
        destination_client.delete_destination(name, level=Level.SUB_ACCOUNT)
        context.cleanup_destinations = [(n, l, t) for n, l, t in context.cleanup_destinations if n != name]
    except Exception:
        pass  # Ignore cleanup errors


@then("I clean up all instance destinations")
def cleanup_all_instance_destinations(context, destination_client):
    """Clean up all instance destinations."""
    for dest in context.destinations:
        try:
            destination_client.delete_destination(dest.name, level=Level.SERVICE_INSTANCE)
        except Exception:
            pass


@then("I clean up all subaccount destinations")
def cleanup_all_subaccount_destinations(context, destination_client):
    """Clean up all subaccount destinations."""
    for dest in context.destinations:
        try:
            destination_client.delete_destination(dest.name, level=Level.SUB_ACCOUNT)
        except Exception:
            pass


@then("I clean up all concurrent test destinations")
def cleanup_all_concurrent_destinations(context, destination_client):
    """Clean up all concurrent test destinations."""
    for dest in context.destinations:
        try:
            destination_client.delete_destination(dest.name, level=Level.SUB_ACCOUNT)
        except Exception:
            pass


@then(parsers.parse('I clean up the subaccount fragment "{name}"'))
def cleanup_subaccount_fragment(context, fragment_client, name):
    """Clean up a subaccount fragment."""
    try:
        fragment_client.delete_fragment(name, level=Level.SUB_ACCOUNT)
        context.cleanup_fragments = [(n, l, t) for n, l, t in context.cleanup_fragments if n != name]
    except Exception:
        pass


@then(parsers.parse('I clean up the instance fragment "{name}"'))
def cleanup_instance_fragment(context, fragment_client, name):
    """Clean up a instance fragment."""
    try:
        fragment_client.delete_fragment(name, level=Level.SERVICE_INSTANCE)
        context.cleanup_fragments = [(n, l, t) for n, l, t in context.cleanup_fragments if n != name]
    except Exception:
        pass


@then("I clean up all subaccount fragments")
def cleanup_all_subaccount_fragments(context, fragment_client):
    """Clean up all subaccount fragments."""
    for frag in context.fragments:
        try:
            fragment_client.delete_fragment(frag.name, level=Level.SUB_ACCOUNT)
        except Exception:
            pass


@then(parsers.parse('I clean up the subaccount certificate "{name}"'))
def cleanup_subaccount_certificate(context, certificate_client, name):
    """Clean up a subaccount certificate."""
    try:
        certificate_client.delete_certificate(name, level=Level.SUB_ACCOUNT)
        context.cleanup_certificates = [(n, l, t) for n, l, t in context.cleanup_certificates if n != name]
    except Exception:
        pass


@then("I clean up all subaccount certificates")
def cleanup_all_subaccount_certificates(context, certificate_client):
    """Clean up all subaccount certificates."""
    for cert in context.certificates:
        try:
            certificate_client.delete_certificate(cert.name, level=Level.SUB_ACCOUNT)
        except Exception:
            pass


# ==================== FINAL CLEANUP ====================

@pytest.fixture(autouse=True)
def cleanup_after_scenario(context, destination_client, fragment_client, certificate_client):
    """Cleanup resources after each scenario."""
    yield

    # Cleanup destinations
    for name, level, tenant in context.cleanup_destinations:
        try:
            destination_client.delete_destination(name, level=level, tenant=tenant)
        except Exception:
            pass

    # Cleanup fragments
    for name, level, tenant in context.cleanup_fragments:
        try:
            fragment_client.delete_fragment(name, level=level, tenant=tenant)
        except Exception:
            pass

    # Cleanup certificates
    for name, level, tenant in context.cleanup_certificates:
        try:
            certificate_client.delete_certificate(name, level=level, tenant=tenant)
        except Exception:
            pass


# ==================== LABEL WHEN STEPS ====================

@when(parsers.parse('I update labels on the destination "{name}" at subaccount level: key "{key}" values "{value}"'))
def update_destination_labels(context, destination_client, name, key, value):
    """Replace labels on a subaccount destination."""
    try:
        labels = [Label(key=key, values=[value])]
        destination_client.update_destination_labels(name, labels, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I patch labels on the destination "{name}" at subaccount level with action "{action}": key "{key}" values "{value}"'))
def patch_destination_labels(context, destination_client, name, action, key, value):
    """Patch labels on a subaccount destination."""
    try:
        patch = PatchLabels(action=action, labels=[Label(key=key, values=[value])])
        destination_client.patch_destination_labels(name, patch, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get labels for the destination "{name}" at subaccount level'))
def get_destination_labels(context, destination_client, name):
    """Get labels for a subaccount destination."""
    try:
        context.retrieved_labels = destination_client.get_destination_labels(name, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I update labels on the fragment "{name}" at subaccount level: key "{key}" values "{value}"'))
def update_fragment_labels(context, fragment_client, name, key, value):
    """Replace labels on a subaccount fragment."""
    try:
        labels = [Label(key=key, values=[value])]
        fragment_client.update_fragment_labels(name, labels, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I patch labels on the fragment "{name}" at subaccount level with action "{action}": key "{key}" values "{value}"'))
def patch_fragment_labels(context, fragment_client, name, action, key, value):
    """Patch labels on a subaccount fragment."""
    try:
        patch = PatchLabels(action=action, labels=[Label(key=key, values=[value])])
        fragment_client.patch_fragment_labels(name, patch, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get labels for the fragment "{name}" at subaccount level'))
def get_fragment_labels(context, fragment_client, name):
    """Get labels for a subaccount fragment."""
    try:
        context.retrieved_labels = fragment_client.get_fragment_labels(name, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I update labels on the certificate "{name}" at subaccount level: key "{key}" values "{value}"'))
def update_certificate_labels(context, certificate_client, name, key, value):
    """Replace labels on a subaccount certificate."""
    try:
        labels = [Label(key=key, values=[value])]
        certificate_client.update_certificate_labels(name, labels, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I patch labels on the certificate "{name}" at subaccount level with action "{action}": key "{key}" values "{value}"'))
def patch_certificate_labels(context, certificate_client, name, action, key, value):
    """Patch labels on a subaccount certificate."""
    try:
        patch = PatchLabels(action=action, labels=[Label(key=key, values=[value])])
        certificate_client.patch_certificate_labels(name, patch, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


@when(parsers.parse('I get labels for the certificate "{name}" at subaccount level'))
def get_certificate_labels(context, certificate_client, name):
    """Get labels for a subaccount certificate."""
    try:
        context.retrieved_labels = certificate_client.get_certificate_labels(name, Level.SUB_ACCOUNT)
        context.operation_success = True
    except Exception as e:
        context.operation_success = False
        context.operation_error = e


# ==================== LABEL THEN STEPS ====================

@then("the destination label operation should be successful")
def destination_label_operation_successful(context):
    """Assert label operation succeeded."""
    assert context.operation_success, f"Expected label operation to succeed, got: {context.operation_error}"


@then("the fragment label operation should be successful")
def fragment_label_operation_successful(context):
    """Assert label operation succeeded."""
    assert context.operation_success, f"Expected label operation to succeed, got: {context.operation_error}"


@then("the certificate label operation should be successful")
def certificate_label_operation_successful(context):
    """Assert label operation succeeded."""
    assert context.operation_success, f"Expected label operation to succeed, got: {context.operation_error}"


@then(parsers.parse('the destination should have label key "{key}" with value "{value}"'))
def destination_should_have_label(context, key, value):
    """Assert retrieved labels contain the specified key/value."""
    assert any(
        lbl.key == key and value in lbl.values
        for lbl in context.retrieved_labels
    ), f"Expected label key='{key}' value='{value}' in {context.retrieved_labels}"


@then(parsers.parse('the fragment should have label key "{key}" with value "{value}"'))
def fragment_should_have_label(context, key, value):
    """Assert retrieved labels contain the specified key/value."""
    assert any(
        lbl.key == key and value in lbl.values
        for lbl in context.retrieved_labels
    ), f"Expected label key='{key}' value='{value}' in {context.retrieved_labels}"


@then(parsers.parse('the certificate should have label key "{key}" with value "{value}"'))
def certificate_should_have_label(context, key, value):
    """Assert retrieved labels contain the specified key/value."""
    assert any(
        lbl.key == key and value in lbl.values
        for lbl in context.retrieved_labels
    ), f"Expected label key='{key}' value='{value}' in {context.retrieved_labels}"
