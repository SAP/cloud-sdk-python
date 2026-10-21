# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Security

- **`DestinationHttpClient` no longer follows HTTP redirects by default.**
  Destination credentials (auth tokens, API keys, `x-sap-*` headers) pre-baked into the
  session are now never forwarded to a redirect target implicitly. This prevents credential
  leakage to a different origin. This is a **behavioral change**: callers that previously
  relied on transparent redirect following will now receive the 3xx response directly.

  To opt in to same-origin redirect following:
  ```python
  http = DestinationHttpClient(dest, redirect_mode=RedirectMode.SAME_ORIGIN)
  ```
  `RedirectMode` is now exported from `sap_cloud_sdk.destination`.

- `HttpClient` (internal SAP service client used by Destination, AI Core, and others) also
  stops following redirects.
- Passing `allow_redirects=True` in `**kwargs` to `DestinationHttpClient.request()` is now
  silently ignored. Redirect behavior is controlled exclusively via `redirect_mode`.
