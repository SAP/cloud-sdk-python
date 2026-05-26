Feature: Core HTTP — AsyncHttpClient and OData Batch
  As an SDK module developer
  I want a generic async HTTP client and OData batch builder
  So that any module can make authenticated async HTTP calls and batch requests

  # ═══════════════════════════════════════════════════════════════════════════
  # AsyncHttpClient
  # ═══════════════════════════════════════════════════════════════════════════

  Background:
    Given an AsyncHttpClient with base_url "https://api.example.com"

  Scenario: GET request returns 200 with response body
    Given the mock server returns 200 with body '{"value": "ok"}'
    When I call "client.get" with path "/items"
    Then the response status should be 200
    And the response JSON should equal '{"value": "ok"}'

  Scenario: GET request with query parameters
    Given the mock server accepts GET "/items" with params
    When I call "client.get" with path "/items" and params {"$top": "5", "$filter": "Name eq 'x'"}
    Then the request URL should include "$top=5"
    And the request URL should include "$filter=Name+eq+'x'"

  Scenario: POST request sends JSON body and returns 201
    Given the mock server returns 201 with body '{"id": "new-001"}'
    When I call "client.post" with path "/items" and json '{"Name": "New"}'
    Then the response status should be 201
    And the request Content-Type should be "application/json"

  Scenario: PATCH request sends JSON body
    Given the mock server returns 200 with body '{"id": "upd-001"}'
    When I call "client.patch" with path "/items/upd-001" and json '{"Name": "Updated"}'
    Then the response status should be 200

  Scenario: PUT request sends JSON body
    Given the mock server returns 200
    When I call "client.put" with path "/items/put-001" and json '{"Name": "Put"}'
    Then the response status should be 200

  Scenario: DELETE request returns 204
    Given the mock server returns 204
    When I call "client.delete" with path "/items/del-001"
    Then the response status should be 204

  Scenario: Bearer token is injected from a sync get_token callable
    Given an AsyncHttpClient with a sync get_token that returns "bearer-sync-tok"
    When I call "client.get" with any path
    Then the request Authorization header should be "Bearer bearer-sync-tok"

  Scenario: Bearer token is injected from an async get_token callable
    Given an AsyncHttpClient with an async get_token that returns "bearer-async-tok"
    When I call "client.get" with any path
    Then the request Authorization header should be "Bearer bearer-async-tok"

  Scenario: Default headers are sent on every request
    Given an AsyncHttpClient with default_headers '{"X-Custom": "sdk-header"}'
    When I call "client.get" with any path
    Then the request should include header "X-Custom" with value "sdk-header"

  Scenario: Per-request headers override default headers
    Given an AsyncHttpClient with default_headers '{"X-Custom": "default"}'
    When I call "client.get" with path "/x" and headers '{"X-Custom": "override"}'
    Then the request should include header "X-Custom" with value "override"

  Scenario: 404 response raises NotFoundError
    Given the mock server returns 404
    When I call "client.get" with path "/missing"
    Then a NotFoundError should be raised

  Scenario: 500 response raises HttpError with status code
    Given the mock server returns 500 with body "Internal Server Error"
    When I call "client.get" with path "/broken"
    Then an HttpError should be raised
    And the HttpError status_code should be 500
    And the HttpError response_text should contain "Internal Server Error"

  Scenario: 403 response raises HttpError
    Given the mock server returns 403
    When I call "client.post" with path "/protected" and json '{}'
    Then an HttpError should be raised
    And the HttpError status_code should be 403

  Scenario: AsyncHttpClient used as async context manager closes the connection
    When I use AsyncHttpClient as an async context manager
    And I call "client.get" inside the context
    Then the client should be closed after exiting the context

  # ═══════════════════════════════════════════════════════════════════════════
  # ODataBatchBuilder
  # ═══════════════════════════════════════════════════════════════════════════

  Scenario: Build a batch with a single GET request
    Given an ODataBatchBuilder
    When I call "builder.add_get" with path "Documents"
    And I call "builder.build"
    Then the Content-Type should contain "multipart/mixed; boundary=batch_"
    And the body should contain "GET Documents HTTP/1.1"

  Scenario: Build a batch with GET and query params
    Given an ODataBatchBuilder
    When I call "builder.add_get" with path "Documents" and params {"$filter": "Name eq 'x'"}
    And I call "builder.build"
    Then the body should contain "$filter=Name eq 'x'"

  Scenario: Build a batch with multiple GETs
    Given an ODataBatchBuilder
    When I add 3 GET requests to the batch
    And I call "builder.build"
    Then the body should contain 3 boundary parts

  Scenario: Build a batch with a POST request
    Given an ODataBatchBuilder
    When I call "builder.add_post" with path "DocumentRelations" and body '{"DocumentRelationID": "001"}'
    And I call "builder.build"
    Then the body should contain "POST DocumentRelations HTTP/1.1"
    And the body should contain '"DocumentRelationID": "001"'

  Scenario: Build a batch with a PATCH request
    Given an ODataBatchBuilder
    When I call "builder.add_patch" with path "Document('001')" and body '{"DocumentName": "new.pdf"}'
    And I call "builder.build"
    Then the body should contain "PATCH Document('001') HTTP/1.1"

  Scenario: Build a batch with a DELETE request
    Given an ODataBatchBuilder
    When I call "builder.add_delete" with path "Document('001')"
    And I call "builder.build"
    Then the body should contain "DELETE Document('001') HTTP/1.1"

  Scenario: Build a batch with a change set containing POST and PATCH
    Given an ODataBatchBuilder
    When I call "builder.begin_change_set"
    And I call "builder.add_post" with path "Documents" and body '{}'
    And I call "builder.add_patch" with path "Documents('x')" and body '{}'
    And I call "builder.end_change_set"
    And I call "builder.build"
    Then the body should contain "multipart/mixed; boundary=changeset_"
    And the body should contain "POST Documents HTTP/1.1"
    And the body should contain "PATCH Documents('x') HTTP/1.1"

  Scenario: Adding a GET inside a change set raises RuntimeError
    Given an ODataBatchBuilder with an open change set
    When I call "builder.add_get" with path "Documents"
    Then a RuntimeError should be raised
    And the error should mention "change set"

  Scenario: Custom boundary is used when specified
    Given an ODataBatchBuilder with boundary "my_custom_boundary"
    When I call "builder.build"
    Then the Content-Type should contain "boundary=my_custom_boundary"
    And the body should contain "--my_custom_boundary"

  Scenario: Mixed batch with GET before and after a change set
    Given an ODataBatchBuilder
    When I add a GET, then a change set with POST, then another GET
    And I call "builder.build"
    Then the body should have the GET requests outside the change set
    And the POST should be inside the change set boundary

  # ═══════════════════════════════════════════════════════════════════════════
  # ODataBatchResponse
  # ═══════════════════════════════════════════════════════════════════════════

  Scenario: Parse a valid batch response with two parts
    Given a batch response body with 2 parts:
      | status | body                  |
      | 200    | {"id": "doc-001"}     |
      | 201    | {"id": "rel-001"}     |
    When I call "ODataBatchResponse.parse" with that content type and body
    Then 2 ODataBatchPart objects should be returned
    And part 0 status should be 200
    And part 1 status should be 201

  Scenario: ODataBatchPart.ok is True for 2xx
    Given an ODataBatchPart with status 200
    Then "part.ok" should be True

  Scenario: ODataBatchPart.ok is False for 4xx
    Given an ODataBatchPart with status 404
    Then "part.ok" should be False

  Scenario: Parse batch response with empty body part
    Given a batch response with one part returning 204 and no body
    When I call "ODataBatchResponse.parse"
    Then 1 ODataBatchPart should be returned
    And part 0 status should be 204
    And part 0 body should be None

  Scenario: Parse batch response with quoted boundary
    Given a batch response Content-Type with quoted boundary: 'multipart/mixed; boundary="batch xyz"'
    When I call "ODataBatchResponse.parse"
    Then the parts should be parsed correctly
