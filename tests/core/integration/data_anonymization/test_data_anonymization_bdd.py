"""BDD step definitions for data anonymization integration tests."""

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Iterator, Optional

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sap_cloud_sdk.core.data_anonymization.client import DataAnonymizationClient
from sap_cloud_sdk.core.data_anonymization.exceptions import TransportError
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeTextRequest,
    PseudonymizeTextRequest,
)


scenarios("data_anonymization.feature")


@dataclass
class IntegrationContext:
    client: Optional[DataAnonymizationClient] = None
    result: Any = None
    last_error: Optional[Exception] = None
    original_text: Optional[str] = None
    temp_file_path: Optional[Path] = None


@pytest.fixture
def context() -> Iterator[IntegrationContext]:
    ctx = IntegrationContext()
    yield ctx
    if ctx.temp_file_path is not None and ctx.temp_file_path.exists():
        ctx.temp_file_path.unlink()


def _require_client(context: IntegrationContext) -> DataAnonymizationClient:
    assert context.client is not None
    return context.client


@given("the data anonymization service is available")
def service_is_available(data_anonymization_client: DataAnonymizationClient) -> None:
    assert data_anonymization_client is not None


@given("I have a valid data anonymization client")
def valid_client(
    context: IntegrationContext,
    data_anonymization_client: DataAnonymizationClient,
) -> None:
    context.client = data_anonymization_client


@given("a data anonymization client with network failure")
def client_with_network_failure(context: IntegrationContext, failure_simulation) -> None:
    context.client = failure_simulation.create_client_with_network_failure()


@given(
    parsers.parse('I have a text file named "{file_name}" containing "{content}"')
)
def prepared_text_file(
    context: IntegrationContext,
    file_name: str,
    content: str,
) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=f"-{file_name}", delete=False
    ) as handle:
        handle.write(content)
        context.temp_file_path = Path(handle.name)


@when(parsers.parse('I anonymize the text "{text}"'))
def anonymize_text(context: IntegrationContext, text: str) -> None:
    try:
        context.original_text = text
        context.result = _require_client(context).anonymize_text(
            AnonymizeTextRequest(text=text)
        )
        context.last_error = None
    except Exception as error:  # noqa: BLE001
        context.result = None
        context.last_error = error


@when(parsers.parse('I pseudonymize the text "{text}"'))
def pseudonymize_text(context: IntegrationContext, text: str) -> None:
    try:
        context.original_text = text
        context.result = _require_client(context).pseudonymize_text(
            PseudonymizeTextRequest(text=text)
        )
        context.last_error = None
    except Exception as error:  # noqa: BLE001
        context.result = None
        context.last_error = error


@when("I anonymize the prepared file")
def anonymize_prepared_file(context: IntegrationContext) -> None:
    try:
        context.result = _require_client(context).anonymize_file(
            AnonymizeFileRequest(file_path=str(context.temp_file_path))
        )
        context.last_error = None
    except Exception as error:  # noqa: BLE001
        context.result = None
        context.last_error = error


@when("I anonymize an empty text payload")
def anonymize_empty_text(context: IntegrationContext) -> None:
    try:
        context.result = _require_client(context).anonymize_text(
            AnonymizeTextRequest(text=" ")
        )
        context.last_error = None
    except Exception as error:  # noqa: BLE001
        context.result = None
        context.last_error = error


@then(parsers.parse('the text result should contain "{text}"'))
def assert_text_result_contains(context: IntegrationContext, text: str) -> None:
    assert context.last_error is None
    assert text in context.result.result


@then("the text result should not equal the original text")
def assert_text_result_not_original(context: IntegrationContext) -> None:
    assert context.last_error is None
    assert context.result.result != context.original_text


@then(parsers.parse('the operation should fail with validation error "{message}"'))
def assert_validation_error(context: IntegrationContext, message: str) -> None:
    assert context.last_error is not None
    assert isinstance(context.last_error, ValueError)
    assert message in str(context.last_error)


@then(parsers.parse('the operation should fail with transport error "{message}"'))
def assert_transport_error(context: IntegrationContext, message: str) -> None:
    assert context.last_error is not None
    assert isinstance(context.last_error, TransportError)
    assert message in str(context.last_error)
