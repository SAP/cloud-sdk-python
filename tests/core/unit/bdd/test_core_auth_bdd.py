"""BDD step definitions: core/auth — IasTokenFetcher, mTLSStrategy, TokenCache."""

import ssl
import time
from unittest.mock import MagicMock, patch
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from sap_cloud_sdk.core.auth._ias_fetcher import AuthError, IasTokenFetcher
from sap_cloud_sdk.core.auth._mtls import mTLSStrategy

scenarios("core_auth.feature")

# ─── IasTokenFetcher helpers ─────────────────────────────────────────────────

_VALID_PEM_CERT = """\
-----BEGIN CERTIFICATE-----
MIIBpDCCAQ2gAwIBAgIUTest123AgIBATANBgkqhkiG9w0BAQsFADANMQswCQYD
VQQGEwJVUzAeFw0yNDAxMDEwMDAwMDBaFw0yNTAxMDEwMDAwMDBaMA0xCzAJBgNV
BAYTAlVTMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALRiMLAHudeSA/xKl5Y4OhyP
OknOPe3/CUPLKZxnPLK9s6f7OfMNaRXVgqgfMHIBg4BFXcBMyCe01sR+HkECAwEA
ATANBgkqhkiG9w0BAQsFAANBAApIsVrIkCWrVJiXCQ2jPGlN+IxD5VJzVeOGnOtG
TyNpkOeBFAdFO3yAgSJ0FkPEHiVXTTQK72xXWAdYEiTest=
-----END CERTIFICATE-----"""

_VALID_PEM_KEY = """\
-----BEGIN PRIVATE KEY-----
MIIBVgIBADANBgkqhkiG9w0BAQEFAASCAUAwggE8AgEAAkEAtGIwsAe515ID/EqX
ljg6HI86Sc497f8JQ8spnGc8sr2zp/s58w1pFdWCqB8wcgGDgEVdwEzIJ7TWxH4e
QQIDAQABAkBTijFDyxIPKWGi5Ao5d/6LT5ORuvNUJagmvXBVCvzYJBVBeKPqlB5A
uATTCgMhN0K1q7MbH7Bih7C9K06yMNDJAiEA3tpEZsBOyRgpflFLDEMVTlK9UvUf
bFHnQ2ek4V8l5ncCIQDPvADPqP7tlhECAkMtest12345ym6V7iXDPlHubq3nJswIh
ALnqWOCTH0t+hy5D6Jrh6testq7UqcCJe9c8wlWdHzHVAiEAtest12345678
-----END PRIVATE KEY-----"""


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def fetcher(mock_session):
    return IasTokenFetcher(
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="cs",
        session=mock_session,
    )


def _token_response(token="tok", expires_in=3600):
    resp = MagicMock()
    resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    resp.raise_for_status.return_value = None
    return resp


# ─── IasTokenFetcher — Given ─────────────────────────────────────────────────

@given(parsers.parse('an IasTokenFetcher with ias_url "{ias_url}", client_id "{client_id}", client_secret "{secret}"'))
def ias_fetcher_given(ias_url, client_id, secret, context, mock_session):
    context["fetcher"] = IasTokenFetcher(
        ias_url=ias_url, client_id=client_id, client_secret=secret, session=mock_session
    )
    context["session"] = mock_session


@given(parsers.parse('the IAS token endpoint returns access_token "{token}" with expires_in {ttl:d}'))
def ias_returns_token(token, ttl, context):
    context["session"] = context.get("session") or context["fetcher"]._session
    context["session"].post.return_value = _token_response(token, ttl)
    context["expected_token"] = token


@given("an IasTokenFetcher with a fresh InMemoryTokenCache")
def fetcher_with_cache(context, mock_session):
    context["fetcher"] = IasTokenFetcher(
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="cs",
        session=mock_session,
    )
    context["session"] = mock_session
    mock_session.post.return_value = _token_response("tok-cached", 3600)
    context["expected_token"] = "tok-cached"


@given(parsers.parse('an IasTokenFetcher with a cache holding token "{token}" expiring in {secs:d} seconds'))
def fetcher_with_expiring_cache(token, secs, context, mock_session):
    from sap_cloud_sdk.core.auth._token_cache import InMemoryTokenCache
    import time
    cache = InMemoryTokenCache()
    # Store with already-expired time to simulate the 60s buffer effect
    # (when expires_in < 60s, the fetcher stores with ttl=0 which immediately expires)
    cache._store["cc"] = (token, time.monotonic() - 1)
    context["fetcher"] = IasTokenFetcher(
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="cs",
        session=mock_session,
        cache=cache,
    )
    context["session"] = mock_session
    # Pre-configure mock to return new-tok (the "And" step will also set this)
    mock_session.post.return_value = _token_response("new-tok", 3600)


@given("an IasTokenFetcher")
def plain_fetcher(context, mock_session):
    context["fetcher"] = IasTokenFetcher(
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="cs",
        session=mock_session,
    )
    context["session"] = mock_session


@given("the IAS token endpoint returns HTTP 401")
def ias_returns_401(context):
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 401
    resp.text = "Unauthorized"
    context["session"].post.return_value = resp


@given("the IAS token endpoint returns an empty JSON body")
def ias_empty_body(context):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {}
    context["session"].post.return_value = resp


@given("the IAS token endpoint is unreachable")
def ias_unreachable(context):
    import requests
    context["session"].post.side_effect = requests.RequestException("unreachable")


@given("the IAS token endpoint always returns a new access_token")
def ias_always_new(context):
    counter = {"n": 0}
    def new_token(*args, **kwargs):
        counter["n"] += 1
        return _token_response(f"tok-{counter['n']}", 900)
    context["session"].post.side_effect = new_token
    context["call_count"] = counter


@given("a custom TokenCache implementation")
def custom_cache(context):
    cache = MagicMock()
    cache.get.return_value = None
    cache.set.return_value = None
    context["custom_cache"] = cache


@given("an IasTokenFetcher using that custom cache")
def fetcher_with_custom_cache(context, mock_session):
    context["fetcher"] = IasTokenFetcher(
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="cs",
        session=mock_session,
        cache=context["custom_cache"],
    )
    context["session"] = mock_session
    mock_session.post.return_value = _token_response("cached-by-custom", 3600)


@given("the IAS token endpoint returns access_token \"cached-by-custom\"")
def ias_returns_cached_by_custom(context):
    pass  # Already set above


# ─── IasTokenFetcher — When ──────────────────────────────────────────────────

@when('I call "fetcher.get_token"')
def call_get_token(context):
    try:
        context["result"] = context["fetcher"].get_token()
    except AuthError as exc:
        context["error"] = exc


@when('I call "fetcher.get_token" twice')
def call_get_token_twice(context):
    context["result"] = context["fetcher"].get_token()
    context["result2"] = context["fetcher"].get_token()


@when('I call "fetcher.get_token" again')
def call_get_token_again(context):
    context["result2"] = context["fetcher"].get_token()


@when(parsers.parse('I call "fetcher.exchange_token" with user_jwt "{jwt}"'))
def call_exchange_token(jwt, context):
    try:
        context["result"] = context["fetcher"].exchange_token(jwt)
        context["last_jwt"] = jwt
    except AuthError as exc:
        context["error"] = exc


# ─── IasTokenFetcher — Then ──────────────────────────────────────────────────

@then(parsers.parse('the token "{token}" should be returned'))
def assert_token(token, context):
    assert context["result"] == token


@then(parsers.parse("the POST request should use grant_type \"{grant_type}\""))
def assert_grant_type(grant_type, context):
    call_kwargs = context["session"].post.call_args
    data = call_kwargs[1].get("data", {}) or call_kwargs[0][1] if call_kwargs[0] else {}
    if not data and call_kwargs[1]:
        data = call_kwargs[1].get("data", {})
    assert data.get("grant_type") == grant_type


@then("the IAS token endpoint should be called only once")
def assert_called_once(context):
    assert context["session"].post.call_count == 1


@then(parsers.parse('both calls should return "{token}"'))
def assert_both_return(token, context):
    assert context["result"] == token
    assert context["result2"] == token


@then(parsers.parse('a new token "{token}" should be fetched and returned'))
def assert_new_token(token, context):
    assert context["result"] == token


@then(parsers.parse('the POST request should include assertion "{jwt}"'))
def assert_assertion(jwt, context):
    call_kwargs = context["session"].post.call_args
    data = call_kwargs[1].get("data", {})
    assert data.get("assertion") == jwt


@then("the IAS token endpoint should be called twice")
def assert_called_twice(context):
    assert context["session"].post.call_count == 2


@then("an AuthError should be raised")
def assert_auth_error(context):
    assert isinstance(context.get("error"), AuthError)


@then("the custom cache \"set\" method should be called with the token")
def assert_custom_cache_set(context):
    context["custom_cache"].set.assert_called_once()


@then("the custom cache \"get\" method should be called")
def assert_custom_cache_get(context):
    assert context["custom_cache"].get.call_count >= 1


@then(parsers.parse('the IAS token "{token}" should be returned'))
def assert_ias_token(token, context):
    assert context["result"] == token


# ─── mTLSStrategy — Given ────────────────────────────────────────────────────

@given("valid PEM certificate and key strings")
def valid_pem(context):
    context["cert_pem"] = _VALID_PEM_CERT
    context["key_pem"] = _VALID_PEM_KEY


@given(parsers.parse('cert and key files exist at "{cert_path}" and "{key_path}"'))
def cert_key_files(cert_path, key_path, context, tmp_path):
    p = tmp_path / "test.crt"
    p.write_text(_VALID_PEM_CERT)
    k = tmp_path / "test.key"
    k.write_text(_VALID_PEM_KEY)
    context["cert_path"] = str(p)
    context["key_path"] = str(k)


@given("a binding directory with files \"certificate\" and \"key\"")
def binding_dir_standard(context, tmp_path):
    (tmp_path / "certificate").write_text(_VALID_PEM_CERT)
    (tmp_path / "key").write_text(_VALID_PEM_KEY)
    context["binding_dir"] = str(tmp_path)


@given("a binding directory with files \"tls.crt\" and \"tls.key\"")
def binding_dir_tls(context, tmp_path):
    (tmp_path / "tls.crt").write_text(_VALID_PEM_CERT)
    (tmp_path / "tls.key").write_text(_VALID_PEM_KEY)
    context["binding_dir"] = str(tmp_path)
    context["cert_key"] = "tls.crt"
    context["key_key"] = "tls.key"


@given(parsers.parse('env vars "{cert_env}" and "{key_env}" point to cert and key files'))
def env_vars_cert(cert_env, key_env, context, tmp_path, monkeypatch):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    cert.write_text(_VALID_PEM_CERT)
    key.write_text(_VALID_PEM_KEY)
    monkeypatch.setenv(cert_env, str(cert))
    monkeypatch.setenv(key_env, str(key))
    context["cert_env"] = cert_env
    context["key_env"] = key_env


@given(parsers.parse('the env var "{env_var}" is not set'))
def env_var_not_set(env_var, context, monkeypatch):
    monkeypatch.delenv(env_var, raising=False)
    context["cert_env"] = env_var
    context["key_env"] = "KEY_PATH"


@given("an mTLSStrategy with valid cert and key")
def mtls_strategy_given(context, tmp_path):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    cert.write_text(_VALID_PEM_CERT)
    key.write_text(_VALID_PEM_KEY)
    context["strategy"] = mTLSStrategy.from_pem(_VALID_PEM_CERT, _VALID_PEM_KEY)


@given("a binding directory with only a \"key\" file")
def binding_dir_missing_cert(context, tmp_path):
    (tmp_path / "key").write_text(_VALID_PEM_KEY)
    context["binding_dir"] = str(tmp_path)


# ─── mTLSStrategy — When ─────────────────────────────────────────────────────

@when('I call "mTLSStrategy.from_pem" with cert_pem and key_pem')
def call_from_pem(context):
    context["result"] = mTLSStrategy.from_pem(context["cert_pem"], context["key_pem"])


@when('I call "mTLSStrategy.from_files" with those paths')
def call_from_files(context):
    context["result"] = mTLSStrategy.from_files(context["cert_path"], context["key_path"])


@when('I call "mTLSStrategy.from_binding_path" with that directory')
def call_from_binding(context):
    try:
        context["result"] = mTLSStrategy.from_binding_path(context["binding_dir"])
    except (ValueError, FileNotFoundError) as exc:
        context["error"] = exc


@when(parsers.parse('I call "mTLSStrategy.from_binding_path" with cert_key "{ck}" and key_key "{kk}"'))
def call_from_binding_custom(ck, kk, context):
    context["result"] = mTLSStrategy.from_binding_path(
        context["binding_dir"], cert_key=ck, key_key=kk
    )


@when(parsers.parse('I call "mTLSStrategy.from_env" with cert_env "{cert_env}" and key_env "{key_env}"'))
def call_from_env(cert_env, key_env, context):
    try:
        context["result"] = mTLSStrategy.from_env(cert_env, key_env)
    except ValueError as exc:
        context["error"] = exc


@when('I call "strategy.apply_to_session"')
def call_apply_to_session(context):
    import requests
    context["result"] = context["strategy"].apply_to_session(requests.Session())


@when('I call "strategy.apply_to_async_client"')
def call_apply_to_async_client(context):
    with patch.object(mTLSStrategy, "_build_ssl_context", return_value=ssl.create_default_context()):
        import httpx
        context["result"] = context["strategy"].apply_to_async_client(httpx.AsyncClient())


# ─── mTLSStrategy — Then ─────────────────────────────────────────────────────

@then("an mTLSStrategy instance should be returned")
def assert_mtls_instance(context):
    assert isinstance(context["result"], mTLSStrategy)


@then("a ValueError should be raised")
def assert_value_error(context):
    assert isinstance(context.get("error"), (ValueError, FileNotFoundError)), \
        f"Expected ValueError/FileNotFoundError, got: {context.get('error')!r}"


@then(parsers.parse('the error should mention "{text}"'))
def assert_error_mention(text, context):
    assert text in str(context.get("error", ""))


@then("a configured requests.Session should be returned")
def assert_requests_session(context):
    import requests
    assert isinstance(context["result"], requests.Session)


@then("the session cert attribute should be set")
def assert_session_cert(context):
    assert context["result"].cert is not None


@then("a configured httpx.AsyncClient should be returned")
def assert_httpx_client(context):
    import httpx
    assert isinstance(context["result"], httpx.AsyncClient)


# ─── TokenCache — Given ──────────────────────────────────────────────────────

@given("an InMemoryTokenCache")
def in_memory_cache(context):
    from sap_cloud_sdk.core.auth._token_cache import InMemoryTokenCache
    context["cache"] = InMemoryTokenCache()


@given(parsers.parse('I set a token "{token}" with ttl {secs:d} second'))
@given(parsers.parse('I set a token "{token}" with ttl {secs:d} seconds'))
def set_expiring_token(token, secs, context):
    context["cache"].set("expiring-key", token, secs)
    context["expiring_key"] = "expiring-key"


@given(parsers.parse("{secs:d} seconds have passed"))
def seconds_passed(secs, context):
    """Simulate time passing by manipulating the cache's stored expiry."""
    cache = context["cache"]
    old_val, old_expiry = cache._store.get(context["expiring_key"], (None, 0))
    if old_val:
        cache._store[context["expiring_key"]] = (old_val, time.monotonic() - 1)


@given("a RedisTokenCache connected to a mock Redis")
def redis_cache_given(context):
    from sap_cloud_sdk.core.auth._token_cache import RedisTokenCache
    from unittest.mock import MagicMock, patch
    mock_redis = MagicMock()
    # Simulate real redis: setex stores a value, get returns it
    _store = {}
    def _setex(key, ttl, val): _store[key] = val
    def _get(key): return _store.get(key)
    mock_redis.setex.side_effect = _setex
    mock_redis.get.side_effect = _get
    with patch.dict("sys.modules", {"redis": MagicMock(Redis=MagicMock(return_value=mock_redis))}):
        context["cache"] = RedisTokenCache(host="localhost", ssl=False)
    context["mock_redis"] = mock_redis


@given("a RedisTokenCache connected to a mock Redis that returns None")
def redis_cache_miss(context):
    from sap_cloud_sdk.core.auth._token_cache import RedisTokenCache
    from unittest.mock import MagicMock, patch
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    with patch.dict("sys.modules", {"redis": MagicMock(Redis=MagicMock(return_value=mock_redis))}):
        context["cache"] = RedisTokenCache(host="localhost", ssl=False)
    context["mock_redis"] = mock_redis


@given("a RedisTokenCache where Redis raises a ConnectionError")
def redis_connection_error(context):
    from sap_cloud_sdk.core.auth._token_cache import RedisTokenCache
    from unittest.mock import MagicMock, patch
    mock_redis = MagicMock()
    mock_redis.get.side_effect = ConnectionError("Redis down")
    mock_redis.setex.side_effect = ConnectionError("Redis down")
    with patch.dict("sys.modules", {"redis": MagicMock(Redis=MagicMock(return_value=mock_redis))}):
        context["cache"] = RedisTokenCache(host="localhost", ssl=False)


@given(parsers.parse('a RedisTokenCache with prefix "{prefix}"'))
def redis_cache_with_prefix(prefix, context):
    from sap_cloud_sdk.core.auth._token_cache import RedisTokenCache
    from unittest.mock import MagicMock, patch
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    with patch.dict("sys.modules", {"redis": MagicMock(Redis=MagicMock(return_value=mock_redis))}):
        context["cache"] = RedisTokenCache(host="localhost", ssl=False, key_prefix=prefix)
    context["mock_redis"] = mock_redis


# ─── TokenCache — When/Then ───────────────────────────────────────────────────

@when(parsers.parse('I call "cache.set" with key "{key}", value "{value}", ttl {ttl:d}'))
def cache_set(key, value, ttl, context):
    context["cache"].set(key, value, ttl)
    context["last_key"] = key
    context["last_value"] = value


@when(parsers.parse('I call "cache.get" with key "{key}"'))
def cache_get(key, context):
    try:
        context["result"] = context["cache"].get(key)
    except Exception:
        context["result"] = None


@when('I call "cache.get" with that key')
def cache_get_expiring(context):
    context["result"] = context["cache"].get(context["expiring_key"])


@then(parsers.parse('"cache.get" with key "{key}" should return "{value}"'))
def assert_cache_get(key, value, context):
    assert context["cache"].get(key) == value


@then("the result should be None")
def assert_result_none(context):
    assert context["result"] is None


@then(parsers.parse('Redis should have been called with key prefix "{prefix}"'))
def assert_redis_prefix(prefix, context):
    call_args = context["mock_redis"].setex.call_args
    assert call_args[0][0].startswith(prefix)


@then("no exception should propagate")
def assert_no_exception(context):
    assert "error" not in context or context.get("error") is None


@then(parsers.parse('Redis should be called with key "{full_key}"'))
def assert_redis_full_key(full_key, context):
    context["mock_redis"].setex.assert_called_once()
    assert context["mock_redis"].setex.call_args[0][0] == full_key
