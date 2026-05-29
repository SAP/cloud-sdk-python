Feature: Core HTTP — AsyncHttpClient
  As an SDK module developer
  I want a generic async HTTP client
  So that any module can make authenticated async HTTP calls

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
