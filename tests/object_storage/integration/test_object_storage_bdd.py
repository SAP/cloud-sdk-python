"""Step definitions for the multi-provider object storage integration suite."""

import io
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sap_cloud_sdk.object_storage import ObjectStoreClient
from sap_cloud_sdk.object_storage.exceptions import (
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

from .conftest import build_live_client, build_unreachable_client

scenarios("object_storage.feature")

_ERRORS = {
    "ObjectNotFoundError": ObjectNotFoundError,
    "ObjectOperationError": ObjectOperationError,
    "ListObjectsError": ListObjectsError,
    "ValueError": ValueError,
}


@dataclass
class ScenarioContext:
    client: ObjectStoreClient | None = None
    prefix: str = ""
    error: BaseException | None = None
    downloaded: bytes = b""
    created: list[str] = field(default_factory=list)

    def key(self, name: str) -> str:
        return f"{self.prefix}{name}" if name else name


@pytest.fixture
def context(object_prefix):
    ctx = ScenarioContext(prefix=object_prefix)
    yield ctx
    if ctx.client is not None and ctx.created:
        for key in ctx.created:
            try:
                ctx.client.delete_object(key)
            except Exception:
                pass


def _run(context: ScenarioContext, action):
    """Execute ``action`` and stash any exception for later assertion."""
    context.error = None
    try:
        return action()
    except Exception as exc:  # noqa: BLE001 - scenarios assert on the captured type
        context.error = exc
        return None


@given(parsers.parse('a live "{provider}" object storage client'))
def _live(context, provider):
    context.client = build_live_client(provider)


@given(parsers.parse('an unreachable "{provider}" object storage client'))
def _unreachable(context, provider):
    context.client = build_unreachable_client(provider)


@when(parsers.parse('I upload "{content}" as bytes to "{name}"'))
def _upload_bytes(context, content, name):
    key = context.key(name)
    _run(
        context,
        lambda: context.client.put_object_from_bytes(
            key, content.encode(), "text/plain"
        ),
    )
    if context.error is None:
        context.created.append(key)


@when(parsers.parse('I upload a 5-byte stream to "{name}"'))
def _upload_stream(context, name):
    key = context.key(name)
    _run(
        context,
        lambda: context.client.put_object(
            key, io.BytesIO(b"abcde"), 5, "application/octet-stream"
        ),
    )
    if context.error is None:
        context.created.append(key)


@when(parsers.parse('I upload a temporary file to "{name}"'))
def _upload_file(context, name, tmp_path):
    source = tmp_path / "payload.txt"
    source.write_text("file-content")
    key = context.key(name)
    _run(
        context,
        lambda: context.client.put_object_from_file(key, str(source), "text/plain"),
    )
    if context.error is None:
        context.created.append(key)


@when(parsers.parse('I upload the missing file "{path}" to "{name}"'))
def _upload_missing_file(context, path, name):
    _run(
        context,
        lambda: context.client.put_object_from_file(
            context.key(name), path, "text/plain"
        ),
    )


@when(parsers.parse('I download the missing object "{name}"'))
def _download_missing(context, name):
    _run(context, lambda: context.client.get_object(context.key(name)))


@when(parsers.parse('I fetch metadata for "{name}"'))
def _head(context, name):
    _run(context, lambda: context.client.head_object(context.key(name)))


@when(parsers.parse('I check whether "{name}" exists'))
def _check_exists(context, name):
    _run(context, lambda: context.client.object_exists(context.key(name)))


@when(parsers.parse('I delete "{name}"'))
def _delete(context, name):
    _run(context, lambda: context.client.delete_object(context.key(name)))


@when("I list the test prefix")
def _list_prefix(context):
    _run(context, lambda: context.client.list_objects(context.prefix))


@then(parsers.parse('downloading "{name}" returns "{expected}"'))
def _download_matches(context, name, expected):
    reader = context.client.get_object(context.key(name))
    with reader as stream:
        assert stream.read().decode() == expected


@then(parsers.parse('the metadata size of "{name}" is {size:d}'))
def _metadata_size(context, name, size):
    assert context.client.head_object(context.key(name)).size == size


@then(parsers.parse('listing the test prefix includes "{name}"'))
def _list_includes(context, name):
    keys = {meta.key for meta in context.client.list_objects(context.prefix)}
    assert context.key(name) in keys


@then(parsers.parse('the object "{name}" exists'))
def _exists(context, name):
    assert context.client.object_exists(context.key(name)) is True


@then(parsers.parse('the object "{name}" does not exist'))
def _not_exists(context, name):
    assert context.client.object_exists(context.key(name)) is False


@then(parsers.parse('the operation fails with "{error_name}"'))
def _fails_with(context, error_name):
    assert context.error is not None, "expected an error but none was raised"
    assert isinstance(context.error, _ERRORS[error_name]), (
        f"expected {error_name}, got {type(context.error).__name__}"
    )


@then("no error is raised")
def _no_error(context):
    assert context.error is None, f"unexpected error: {context.error!r}"
