# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Security

- Destination, fragment, and certificate resource names are now validated against an
  allowlist grammar at every public SDK method boundary. Names must match
  `[A-Za-z0-9][A-Za-z0-9._\-]{0,199}`. A `ValueError` is raised for invalid names
  before any OAuth token is fetched or HTTP request is sent. This prevents path
  traversal via crafted resource names in URL path segments.
- `get_destination()` auto-parses a `@ConsumptionLevel` suffix in the name string for
  backward compatibility (e.g. `"my-dest@provider_subaccount"` continues to work without
  changes; the `level=` parameter is the canonical form). No breaking changes.
- Added a defense-in-depth guard in `_request()` that rejects paths containing `..`
  segments before issuing any HTTP request.
