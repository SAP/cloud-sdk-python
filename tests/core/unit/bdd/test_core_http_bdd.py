"""BDD step definitions: core/http — AsyncHttpClient and ODataBatch."""

import asyncio
import json
import pytest
import httpx
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.core.http._async_client import AsyncHttpClient, HttpError, NotFoundError
from sap_cloud_sdk.core.http._batch import ODataBatchBuilder, ODataBatchResponse, ODataBatchPart

scenarios("core_http.feature")


# ─── RESPX transport helper ──────────────────────────────────────────────────

def _mock_client(status: int = 200, body: str = '{"ok": true}', headers=None):
    """Return an httpx.AsyncClient backed by a mock transport."""
    transport = httpx.MockTransport(
        handler=lambda req: httpx.Response(
            status_code=status,
            content=body.encode(),
            headers=headers or {"Content-Type": "application/json"},
        )
    )
    return httpx.AsyncClient(transport=transport, base_url="https://api.example.com")


def _run(coro):
    """Run a coroutine synchronously (pytest-bdd steps are sync)."""
    return asyncio.run(coro)


# ─── Background ───────────────────────────────────────────────────────────────

@given(parsers.parse('an AsyncHttpClient with base_url "{base_url}"'))
def plain_client(base_url, context):
    context["base_url"] = base_url
    context["captured_request"] = {}

# ─── Given: responses ──────────────────────────────────────────────────────────

@given(parsers.parse("the mock server returns {status:d} with body '{body}'"))
def mock_returns(status, body, context):
    context["mock_client"] = _mock_client(status, body)


@given(parsers.parse("the mock server returns {status:d}"))
def mock_returns_simple(status, context):
    context["mock_client"] = _mock_client(status, "")


@given(parsers.parse("the mock server returns {status:d} with body \"{body}\""))
def mock_returns_with_body(status, body, context):
    context["mock_client"] = _mock_client(status, body)


@given("the mock server accepts GET \"/items\" with params")
def mock_accepts_params(context):
    context["mock_client"] = _mock_client(200, '{"value": []}')


@given(parsers.parse("an AsyncHttpClient with a sync get_token that returns \"{token}\""))
def client_with_sync_token(token, context):
    context["mock_client"] = _mock_client(200, '{"ok": true}')
    context["get_token"] = lambda: token
    context["expected_token"] = token


@given(parsers.parse("an AsyncHttpClient with an async get_token that returns \"{token}\""))
def client_with_async_token(token, context):
    context["mock_client"] = _mock_client(200, '{"ok": true}')
    async def _async_get_token():
        return token
    context["get_token"] = _async_get_token
    context["expected_token"] = token


@given(parsers.parse("an AsyncHttpClient with default_headers '{{\"X-Custom\": \"{value}\"}}' "))
@given(parsers.parse("an AsyncHttpClient with default_headers '{\"X-Custom\": \"default\"}'"))
def client_with_default_headers(context):
    context["mock_client"] = _mock_client(200, '{"ok": true}')
    context["default_headers"] = {"X-Custom": "default"}


@given(parsers.parse("an AsyncHttpClient with default_headers '{{\"X-Custom\": \"{value}\"}}'"))
def client_with_custom_default(value, context):
    context["mock_client"] = _mock_client(200, '{"ok": true}')
    context["default_headers"] = {"X-Custom": value}


# ─── When ─────────────────────────────────────────────────────────────────────



def _build_client(context) -> AsyncHttpClient:
    return AsyncHttpClient(
        base_url=context.get("base_url", "https://api.example.com"),
        get_token=context.get("get_token"),
        client=context.get("mock_client", _mock_client()),
        default_headers=context.get("default_headers"),
    )


@when(parsers.parse("I call \"client.get\" with path \"{path}\""))
def call_get(path, context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.get(path))
        context["request_headers"] = dict(context["response"].request.headers)
    except (HttpError, NotFoundError) as exc:
        context["error"] = exc


@when(parsers.parse("I call \"client.get\" with path \"{path}\" and params {{\"$top\": \"5\", \"$filter\": \"Name eq 'x'\"}}"))
def call_get_with_params(path, context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.get(path, params={"$top": "5", "$filter": "Name eq 'x'"}))
        context["request_url"] = str(context["response"].request.url)
    except Exception as exc:
        context["error"] = exc


@when("I call \"client.get\" with any path")
def call_get_any(context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.get("/test"))
        context["request_headers"] = dict(context["response"].request.headers)
    except Exception as exc:
        context["error"] = exc


@when(parsers.parse("I call \"client.get\" with path \"{path}\" and headers '{{\"X-Custom\": \"{value}\"}}'"))
def call_get_with_override_header(path, value, context):
    client = _build_client(context)
    context["response"] = _run(client.get(path, headers={"X-Custom": value}))
    context["request_headers"] = dict(context["response"].request.headers)
    context["expected_override"] = value


@when(parsers.parse("I call \"client.post\" with path \"{path}\" and json '{body}'"))
def call_post(path, body, context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.post(path, json=json.loads(body)))
        context["request_headers"] = dict(context["response"].request.headers)
    except (HttpError, NotFoundError) as exc:
        context["error"] = exc


@when(parsers.parse("I call \"client.patch\" with path \"{path}\" and json '{body}'"))
def call_patch(path, body, context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.patch(path, json=json.loads(body)))
    except Exception as exc:
        context["error"] = exc


@when(parsers.parse("I call \"client.put\" with path \"{path}\" and json '{body}'"))
def call_put(path, body, context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.put(path, json=json.loads(body)))
    except Exception as exc:
        context["error"] = exc


@when(parsers.parse("I call \"client.delete\" with path \"{path}\""))
def call_delete(path, context):
    client = _build_client(context)
    try:
        context["response"] = _run(client.delete(path))
    except Exception as exc:
        context["error"] = exc


@when("I use AsyncHttpClient as an async context manager")
def async_cm_setup(context):
    context["mock_client"] = _mock_client(200, '{"ok": true}')


@when("I call \"client.get\" inside the context")
def call_get_in_context(context):
    async def _inner():
        async with AsyncHttpClient(
            base_url="https://api.example.com",
            client=context["mock_client"],
        ) as client:
            context["response"] = await client.get("/test")
            context["client_ref"] = client
    _run(_inner())


# ─── AsyncHttpClient — Then ───────────────────────────────────────────────────

@then(parsers.parse("the response status should be {status:d}"))
def assert_status(status, context):
    assert context["response"].status_code == status


@then(parsers.parse("the response JSON should equal '{body}'"))
def assert_json(body, context):
    assert context["response"].json() == json.loads(body)


@then(parsers.parse("the request URL should include \"{fragment}\""))
def assert_url_fragment(fragment, context):
    from urllib.parse import unquote
    url = context.get("request_url", "")
    assert fragment in url or fragment in unquote(url), f"Expected '{fragment}' in '{url}'"


@then(parsers.parse("the request Content-Type should be \"{content_type}\""))
def assert_content_type(content_type, context):
    headers = context.get("request_headers", {})
    assert content_type in headers.get("content-type", "")


@then(parsers.parse("the request Authorization header should be \"{auth_value}\""))
def assert_auth_header(auth_value, context):
    headers = context.get("request_headers", {})
    assert headers.get("authorization") == auth_value


@then(parsers.parse("the request should include header \"{name}\" with value \"{value}\""))
def assert_custom_header(name, value, context):
    headers = context.get("request_headers", {})
    assert headers.get(name.lower()) == value or headers.get(name) == value


@then("a NotFoundError should be raised")
def assert_not_found(context):
    assert isinstance(context.get("error"), NotFoundError)


@then("an HttpError should be raised")
def assert_http_error(context):
    assert isinstance(context.get("error"), HttpError)


@then(parsers.parse("the HttpError status_code should be {code:d}"))
def assert_http_code(code, context):
    assert context["error"].status_code == code


@then(parsers.parse("the HttpError response_text should contain \"{text}\""))
def assert_http_text(text, context):
    assert text in (context["error"].response_text or "")


@then("the client should be closed after exiting the context")
def assert_client_closed(context):
    assert context["client_ref"]._client.is_closed


# ─── ODataBatchBuilder — Given ────────────────────────────────────────────────

@given("an ODataBatchBuilder")
def builder_given(context):
    context["builder"] = ODataBatchBuilder()


@given("an ODataBatchBuilder with an open change set")
def builder_with_cs(context):
    context["builder"] = ODataBatchBuilder()
    context["builder"].begin_change_set()


@given(parsers.parse('an ODataBatchBuilder with boundary "{boundary}"'))
def builder_with_boundary(boundary, context):
    context["builder"] = ODataBatchBuilder(boundary=boundary)


# ─── ODataBatchBuilder — When ─────────────────────────────────────────────────

@when(parsers.parse('I call "builder.add_get" with path "{path}"'))
def batch_add_get(path, context):
    try:
        context["builder"].add_get(path)
    except RuntimeError as exc:
        context["error"] = exc


@when(parsers.parse('I call "builder.add_get" with path "{path}" and params {{"{k}": "{v}"}}'))
def batch_add_get_params(path, k, v, context):
    context["builder"].add_get(path, params={k: v})


@when("I add 3 GET requests to the batch")
def batch_add_three_gets(context):
    for i in range(3):
        context["builder"].add_get(f"Documents({i})")


@when(parsers.parse('I call "builder.add_post" with path "{path}" and body \'{body}\''))
def batch_add_post(path, body, context):
    context["builder"].add_post(path, body=json.loads(body))


@when(parsers.parse('I call "builder.add_patch" with path "{path}" and body \'{body}\''))
def batch_add_patch(path, body, context):
    context["builder"].add_patch(path, body=json.loads(body))


@when(parsers.parse('I call "builder.add_delete" with path "{path}"'))
def batch_add_delete(path, context):
    context["builder"].add_delete(path)


@when('I call "builder.begin_change_set"')
def batch_begin_cs(context):
    context["builder"].begin_change_set()


@when('I call "builder.end_change_set"')
def batch_end_cs(context):
    context["builder"].end_change_set()


@when('I call "builder.build"')
def batch_build(context):
    context["content_type"], context["body"] = context["builder"].build()


@when("I add a GET, then a change set with POST, then another GET")
def batch_mixed(context):
    context["builder"].add_get("BeforeCS")
    context["builder"].begin_change_set()
    context["builder"].add_post("InsideCS", body={"k": "v"})
    context["builder"].end_change_set()
    context["builder"].add_get("AfterCS")


# ─── ODataBatchBuilder — Then ─────────────────────────────────────────────────

@then(parsers.parse('the Content-Type should contain "{expected}"'))
def assert_content_type_batch(expected, context):
    assert expected in context["content_type"]


@then(parsers.parse('the body should contain "{text}"'))
def assert_body_contains(text, context):
    assert text in context["body"], f"Expected '{text}' in batch body"


@then(parsers.parse("the body should contain '{text}'"))
def assert_body_contains_sq(text, context):
    assert text in context["body"], f"Expected '{text}' in batch body"


@then(parsers.parse("the body should contain {n:d} boundary parts"))
def assert_boundary_parts(n, context):
    boundary = context["content_type"].split("boundary=")[-1].strip('"')
    count = context["body"].count(f"--{boundary}\r\n")
    assert count == n


@then("a RuntimeError should be raised")
def assert_runtime_error(context):
    assert isinstance(context.get("error"), RuntimeError)


@then(parsers.parse('the error should mention "{text}"'))
def assert_error_mention(text, context):
    assert text.lower() in str(context.get("error", "")).lower()


@then("the body should have the GET requests outside the change set")
def assert_gets_outside(context):
    assert "GET BeforeCS" in context["body"]
    assert "GET AfterCS" in context["body"]


@then("the POST should be inside the change set boundary")
def assert_post_inside(context):
    assert "POST InsideCS" in context["body"]


# ─── ODataBatchResponse — Given/When/Then ─────────────────────────────────────

@given("a batch response body with 2 parts:")
def batch_response_body(context):
    boundary = "batch_test123"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/http\r\n\r\n"
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n\r\n"
        '{"id": "doc-001"}\r\n'
        f"--{boundary}\r\n"
        "Content-Type: application/http\r\n\r\n"
        "HTTP/1.1 201 Created\r\n"
        "Content-Type: application/json\r\n\r\n"
        '{"id": "rel-001"}\r\n'
        f"--{boundary}--\r\n"
    )
    context["batch_content_type"] = f"multipart/mixed; boundary={boundary}"
    context["batch_body"] = body


@given("a batch response with one part returning 204 and no body")
def batch_response_204(context):
    boundary = "batch_empty"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/http\r\n\r\n"
        "HTTP/1.1 204 No Content\r\n\r\n"
        f"--{boundary}--\r\n"
    )
    context["batch_content_type"] = f"multipart/mixed; boundary={boundary}"
    context["batch_body"] = body


@given(parsers.parse("a batch response Content-Type with quoted boundary: '{ct}'"))
def batch_quoted_boundary(ct, context):
    body = (
        "--batch xyz\r\n"
        "Content-Type: application/http\r\n\r\n"
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n\r\n"
        '{"id": "ok"}\r\n'
        "--batch xyz--\r\n"
    )
    context["batch_content_type"] = ct
    context["batch_body"] = body


@given(parsers.parse("an ODataBatchPart with status {status:d}"))
def batch_part_given(status, context):
    context["batch_part"] = ODataBatchPart(status=status, headers={}, body=None)


@when('I call "ODataBatchResponse.parse" with that content type and body')
def parse_batch(context):
    result = ODataBatchResponse.parse(
        context["batch_content_type"], context["batch_body"]
    )
    context["parts"] = result.parts


@when('I call "ODataBatchResponse.parse"')
def parse_batch_simple(context):
    result = ODataBatchResponse.parse(
        context["batch_content_type"], context["batch_body"]
    )
    context["parts"] = result.parts


@then(parsers.parse("{n:d} ODataBatchPart objects should be returned"))
@then(parsers.parse("{n:d} ODataBatchPart should be returned"))
def assert_n_parts(n, context):
    assert len(context["parts"]) == n


@then(parsers.parse("part {idx:d} status should be {status:d}"))
def assert_part_status(idx, status, context):
    assert context["parts"][idx].status == status


@then(parsers.parse("part {idx:d} body should be None"))
def assert_part_body_none(idx, context):
    assert context["parts"][idx].body is None


@then('"part.ok" should be True')
def assert_part_ok_true(context):
    assert context["batch_part"].ok is True


@then('"part.ok" should be False')
def assert_part_ok_false(context):
    assert context["batch_part"].ok is False


@then("the parts should be parsed correctly")
def assert_parts_parsed(context):
    assert len(context["parts"]) >= 1
    assert context["parts"][0].status == 200
