# Changelog

## [0.20.2] - 2026-05-26

### Fixed

- Record ALS v3 (`auditlog_ng`) capability telemetry when `AuditClient` is
  initialized, including direct `AuditClient(config)` construction. The
  `send()` and `send_json()` APIs remain uninstrumented so the metric continues
  to represent client initialization rather than audit event volume.
