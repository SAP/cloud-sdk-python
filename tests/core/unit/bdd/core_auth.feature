Feature: Core Auth — IAS Token Fetcher, mTLS Strategy, Token Cache
  As an SDK module developer
  I want generic auth primitives for IAS OAuth2 and mTLS
  So that any service module can authenticate to BTP Business Services

  # ═══════════════════════════════════════════════════════════════════════════
  # IasTokenFetcher
  # ═══════════════════════════════════════════════════════════════════════════

  Scenario: Fetch a client_credentials token successfully
    Given an IasTokenFetcher with ias_url "https://ias.example.com", client_id "cid", client_secret "cs"
    And the IAS token endpoint returns access_token "tok-001" with expires_in 3600
    When I call "fetcher.get_token"
    Then the token "tok-001" should be returned
    And the POST request should use grant_type "client_credentials"

  Scenario: Client credentials token is cached on second call
    Given an IasTokenFetcher with a fresh InMemoryTokenCache
    And the IAS token endpoint returns access_token "tok-cached" with expires_in 3600
    When I call "fetcher.get_token" twice
    Then the IAS token endpoint should be called only once
    And both calls should return "tok-cached"

  Scenario: Cached token is refreshed when within 60-second expiry buffer
    Given an IasTokenFetcher with a cache holding token "old-tok" expiring in 30 seconds
    And the IAS token endpoint returns access_token "new-tok" with expires_in 3600
    When I call "fetcher.get_token"
    Then a new token "new-tok" should be fetched and returned

  Scenario: Exchange user JWT for an IAS OBO token
    Given an IasTokenFetcher
    And the IAS token endpoint returns access_token "user-tok" with expires_in 900
    When I call "fetcher.exchange_token" with user_jwt "user-jwt-abc"
    Then the token "user-tok" should be returned
    And the POST request should use grant_type "urn:ietf:params:oauth:grant-type:jwt-bearer"
    And the POST request should include assertion "user-jwt-abc"

  Scenario: OBO tokens are not cached
    Given an IasTokenFetcher
    And the IAS token endpoint always returns a new access_token
    When I call "fetcher.exchange_token" with user_jwt "jwt-1"
    And I call "fetcher.exchange_token" with user_jwt "jwt-2"
    Then the IAS token endpoint should be called twice

  Scenario: get_token raises AuthError when IAS returns 401
    Given an IasTokenFetcher
    And the IAS token endpoint returns HTTP 401
    When I call "fetcher.get_token"
    Then an AuthError should be raised

  Scenario: get_token raises AuthError when response is missing access_token
    Given an IasTokenFetcher
    And the IAS token endpoint returns an empty JSON body
    When I call "fetcher.get_token"
    Then an AuthError should be raised

  Scenario: get_token raises AuthError on network failure
    Given an IasTokenFetcher
    And the IAS token endpoint is unreachable
    When I call "fetcher.get_token"
    Then an AuthError should be raised

  Scenario: IasTokenFetcher uses custom token cache (Redis replacement)
    Given a custom TokenCache implementation
    And an IasTokenFetcher using that custom cache
    And the IAS token endpoint returns access_token "cached-by-custom"
    When I call "fetcher.get_token"
    Then the custom cache "set" method should be called with the token
    When I call "fetcher.get_token" again
    Then the custom cache "get" method should be called

  # ═══════════════════════════════════════════════════════════════════════════
  # mTLSStrategy
  # ═══════════════════════════════════════════════════════════════════════════

  Scenario: Create mTLSStrategy from PEM strings
    Given valid PEM certificate and key strings
    When I call "mTLSStrategy.from_pem" with cert_pem and key_pem
    Then an mTLSStrategy instance should be returned

  Scenario: Create mTLSStrategy from file paths
    Given cert and key files exist at "/tmp/test.crt" and "/tmp/test.key"
    When I call "mTLSStrategy.from_files" with those paths
    Then an mTLSStrategy instance should be returned

  Scenario: Create mTLSStrategy from a BTP binding directory
    Given a binding directory with files "certificate" and "key"
    When I call "mTLSStrategy.from_binding_path" with that directory
    Then an mTLSStrategy instance should be returned

  Scenario: Create mTLSStrategy from custom binding file names
    Given a binding directory with files "tls.crt" and "tls.key"
    When I call "mTLSStrategy.from_binding_path" with cert_key "tls.crt" and key_key "tls.key"
    Then an mTLSStrategy instance should be returned

  Scenario: Create mTLSStrategy from environment variable paths
    Given env vars "CERT_PATH" and "KEY_PATH" point to cert and key files
    When I call "mTLSStrategy.from_env" with cert_env "CERT_PATH" and key_env "KEY_PATH"
    Then an mTLSStrategy instance should be returned

  Scenario: from_env raises ValueError when env var is not set
    Given the env var "CERT_PATH" is not set
    When I call "mTLSStrategy.from_env" with cert_env "CERT_PATH" and key_env "KEY_PATH"
    Then a ValueError should be raised
    And the error should mention "CERT_PATH"

  Scenario: Apply mTLSStrategy to a requests.Session
    Given an mTLSStrategy with valid cert and key
    When I call "strategy.apply_to_session"
    Then a configured requests.Session should be returned
    And the session cert attribute should be set

  Scenario: Apply mTLSStrategy to an httpx.AsyncClient
    Given an mTLSStrategy with valid cert and key
    When I call "strategy.apply_to_async_client"
    Then a configured httpx.AsyncClient should be returned

  Scenario: from_binding_path raises error when cert file is missing
    Given a binding directory with only a "key" file
    When I call "mTLSStrategy.from_binding_path" with that directory
    Then a ValueError should be raised
    And the error should mention "certificate"

  # ═══════════════════════════════════════════════════════════════════════════
  # TokenCache
  # ═══════════════════════════════════════════════════════════════════════════

  Scenario: InMemoryTokenCache stores and retrieves a token
    Given an InMemoryTokenCache
    When I call "cache.set" with key "cc", value "token-abc", ttl 3600
    Then "cache.get" with key "cc" should return "token-abc"

  Scenario: InMemoryTokenCache returns None for missing key
    Given an InMemoryTokenCache
    When I call "cache.get" with key "nonexistent"
    Then the result should be None

  Scenario: InMemoryTokenCache returns None for expired token
    Given an InMemoryTokenCache
    And I set a token "expired-tok" with ttl 1 second
    And 2 seconds have passed
    When I call "cache.get" with that key
    Then the result should be None

  Scenario: RedisTokenCache stores and retrieves a token
    Given a RedisTokenCache connected to a mock Redis
    When I call "cache.set" with key "cc", value "redis-tok", ttl 3600
    Then "cache.get" with key "cc" should return "redis-tok"
    And Redis should have been called with key prefix "sap_sdk:tokens:"

  Scenario: RedisTokenCache returns None on Redis miss
    Given a RedisTokenCache connected to a mock Redis that returns None
    When I call "cache.get" with key "cc"
    Then the result should be None

  Scenario: RedisTokenCache gracefully handles Redis connection error
    Given a RedisTokenCache where Redis raises a ConnectionError
    When I call "cache.get" with key "cc"
    Then the result should be None
    And no exception should propagate

  Scenario: RedisTokenCache uses custom key prefix
    Given a RedisTokenCache with prefix "my-service:tokens:"
    When I call "cache.set" with key "cc", value "tok", ttl 600
    Then Redis should be called with key "my-service:tokens:cc"
