---
name: security-review
description: Security-focused review of a pull request against the cloud-sdk-python security standards. Extends review-pr with deeper checks on tenant isolation, input validation, credential handling, JWT verification, and URL safety, plus regression checks against the project's published GitHub Security Advisories. Use when you want targeted security feedback, or as a sub-step of prep-pr.
tools: Bash, Read
compatibility: gh CLI ≥ 2.0, git, GitHub access to SAP/cloud-sdk-python
---

# Security Review: SAP Cloud SDK for Python

A security-focused extension of `review-pr`. Evaluates 13 security criteria derived from the guardrails introduced in the project (subdomain validation, URL injection safeguards, JWT verification, credential emptiness checks, sensitive data exposure, and more).

The final criterion (**S13**) guards against regressions of the project's own published GitHub Security Advisories: it fetches the live advisory list, reads each one, and checks whether the diff reintroduces a fixed vulnerability — either by weakening the exact guard or by repeating the same vulnerability class in another module.

Run from the root of the `cloud-sdk-python` repository. Can be invoked standalone or as a sub-step of `prep-pr` / `review-pr`.

---

## Phase 1: Identify the PR

Same as `review-pr` Phase 1 — resolve `REPO` and `NUMBER` from user input, or list open PRs if nothing provided.

---

## Phase 2: Gather Data

Run in parallel:

```bash
gh pr diff <NUMBER> --repo <REPO>
gh pr view <NUMBER> --repo <REPO> --json number,title,headRefName,baseRefName,author,files
gh pr view <NUMBER> --repo <REPO> --json commits --jq '.commits[].messageHeadline'
gh api repos/SAP/cloud-sdk-python/security-advisories --jq '.[] | {ghsa: .ghsa_id, cve: .cve_id, severity, summary}'
```

The last command fetches the live list of published advisories for **S13**. If it returns nothing or access is denied, note that and score S13 `⚠️` (see S13).

Fetch each changed `src/` file at the PR head commit SHA (same method as `review-pr` Phase 2 — skip files >500 KB or binary). Store under `/tmp/pr<NUMBER>/`.

Also fetch the current authoritative sources for the security patterns:

```bash
cat src/sap_cloud_sdk/core/_tenant.py
```

---

## Phase 3: Evaluate 13 Security Criteria

Assign each: **✅ Pass** / **⚠️ Warning** / **❌ Fail** / **➖ N/A**

Use `Read /tmp/pr<NUMBER>/<path>` for exact line references. Do not derive line positions from diff hunk offsets.

---

### S1: Tenant subdomain validation

**Applies to**: any code that accepts a `tenant_subdomain`, `tenant`, or subdomain-like parameter and uses it in a URL, HTTP header, or auth token request.

**Rule**: Every caller that receives an external tenant identifier must call `_validate_tenant_subdomain()` from `sap_cloud_sdk.core._tenant` before using the value. Passing an unvalidated subdomain to a URL-construction function, OAuth token request, or HTTP client is a URL injection vector.

**Check**:
- Does the diff introduce or modify a function that takes a subdomain/tenant parameter?
- Is `_validate_tenant_subdomain` called before any use of that parameter in a URL, netloc, or auth request?
- Are there tests covering: valid RFC 1123 labels pass, dot-bearing values are rejected, slash/space values are rejected, hyphen-leading/trailing values are rejected, 64+ char values are rejected, `None` is a no-op?

**Reference**: `src/sap_cloud_sdk/core/_tenant.py`, commits `fc67a8f` and `4d0f2f6`.

---

### S2: URL construction uses structured replacement, not string substitution

**Applies to**: any code that builds a URL by substituting a tenant identifier into a base URL (e.g. replacing the identity zone label to derive a tenant-specific token URL).

**Rule**: Use `_derive_tenant_token_url()` from `sap_cloud_sdk.core._tenant` (or an equivalent `urlparse`/`urlunparse` approach) — never `str.replace(identityzone, tenant_subdomain)`. A bare `str.replace` will corrupt the URL if the identity zone string appears in the path, query, or fragment.

**Check**:
- Does the diff use `str.replace` or f-string concatenation to substitute a tenant value into a URL?
- If yes → ❌. Point to the exact line.
- Are there tests covering: identityzone appears only in hostname (replaced correctly), identityzone also appears in path (path segment untouched), port preserved, non-matching hostname returned unchanged?

**Reference**: `src/sap_cloud_sdk/core/_tenant.py::_derive_tenant_token_url`, commit `fadcdb0`.

---

### S3: Credential fields validated for emptiness before use

**Applies to**: any code that reads a credential field (client ID, client secret, token URL, API key) from a config object, service binding, destination properties, or environment variable.

**Rule**: An empty string credential silently breaks auth at runtime without a clear error. Validate that required credential fields are non-empty immediately after reading them — raise a descriptive exception (`ValueError` or a domain-specific subclass) rather than silently passing an empty string downstream.

**Check**:
- Does the diff read `clientId`, `client_id`, `clientSecret`, `apiKey`, `token_url`, or similar fields?
- Is there an explicit non-empty check (`if not client_id: raise ...`) before the value is used?
- Empty string, `None`, and whitespace-only should all be treated as absent.

**Reference**: commits `d1bf978` (empty IAS client ID), `fc283` (agw credentials).

---

### S4: JWT tokens verified before trust

**Applies to**: any code that reads a JWT from a request (header, body, cookie) and uses claims from it (user identity, tenant ID, permissions) without verifying the signature.

**Rule**: Never trust JWT claims from an unverified token. Signature verification must happen before any claim is read for identity, authorization, or audit purposes. Use `IASVerifier` (from `sap_cloud_sdk.ias`) or an equivalent JWKS-backed verifier. Decoding without verification (`options={"verify_signature": False}`) is only acceptable for logging/debugging and must never reach production paths.

**Check**:
- Does the diff decode a JWT (`jwt.decode`, `PyJWT`, manual base64 split)?
- Is signature verification performed (`IASVerifier.verify()`, `PyJWKClient`, or equivalent)?
- Are there tests covering: valid token accepted, tampered/expired/wrong-audience token rejected?

**Reference**: `src/sap_cloud_sdk/ias/_verifier.py`, commit `545a9b1`.

---

### S5: No hardcoded credentials or secrets

**Applies to**: all files in the diff.

**Rule**: No hardcoded passwords, API keys, tokens, client secrets, certificate private keys, or SAP-internal account identifiers. Use env vars, service bindings, or the `secret_resolver` module.

**Check**:
- Scan diff for: `password`, `secret`, `apiKey`, `token`, `key` assigned a string literal that looks like a credential (long hex/base64, UUID-like, `Bearer ...`).
- SAP-internal URLs embedded as literals (non-public hostnames, internal tooling references) → ❌.
- Test fixtures using obviously fake values (`"fake-secret"`, `"test-token"`) are fine.

---

### S6: Sensitive data not logged

**Applies to**: any `logger.*` call in the diff.

**Rule**: Do not log credentials, tokens, or PII. Tenant subdomains, tenant IDs, and subaccount IDs are **acceptable** to log — they are operational identifiers, not secrets. Log token *length* (e.g. `len(access_token)`) rather than token *value*. Full request/response bodies that may contain PII should not be logged at INFO or above.

**Check**:
- Does any `logger.*` call include a raw token, client secret, password, or private key value in the formatted message?
- `repr(exception)` is usually safe; `str(token)` where token is a bearer/JWT value is not.
- Logging tenant IDs, subaccount IDs, subdomains, URLs, and variable names (not values) is fine.

---

### S7: External input not used to construct file paths

**Applies to**: any code that reads from the filesystem using a path derived from user input, request parameters, or external config.

**Rule**: Path traversal is possible if external input is joined directly to a base path without normalization. Use `pathlib.Path(...).resolve()` and verify the result is still under the expected base directory before opening.

**Check**:
- Does the diff join user-controlled or externally-sourced strings into a file path?
- Is `os.path.join` / `Path(...)` used without a subsequent `resolve()` + prefix check?

---

### S8: HTTP requests use validated base URLs

**Applies to**: any code that constructs an HTTP request URL from config values or tenant-derived values.

**Rule**: The base URL must come from a trusted source (service binding, validated config). Do not construct URLs by appending user-supplied path segments without sanitization — this can lead to SSRF or path injection. Relative path segments in the base URL must be stripped or rejected.

**Check**:
- Does the diff build URLs by concatenating a config base URL with an externally-supplied path?
- Is the base URL taken directly from a service binding or validated config, or could it be influenced by request parameters?

---

### S9: Multi-tenancy isolation — no cross-tenant data leakage

**Applies to**: any code that fetches, caches, or returns data that is scoped to a tenant.

**Rule**: Caches, connection pools, and in-memory state keyed by tenant must use the tenant identifier (subdomain or tenant ID) as an explicit cache key. A missing or defaulting key risks returning one tenant's data to another.

**Check**:
- Does the diff introduce a cache (`dict`, `lru_cache`, module-level variable) that stores tenant-scoped data?
- Is the tenant identifier explicitly part of the cache key?
- Is there a test that verifies two different tenants get different cached values?

---

### S10: Dependency additions checked for known CVEs

**Applies to**: changes to `pyproject.toml` that add new runtime dependencies.

**Rule**: New dependencies must not introduce known vulnerabilities. Check the new package on [PyPI](https://pypi.org) for security advisories and verify the pinned version is not in a known CVE range.

**Check**:
- Does the diff add entries under `[project.dependencies]` in `pyproject.toml`?
- Are any of the added packages known to have CVEs in the pinned version range?
- Flag for manual CVE check if a new non-trivial dependency is introduced.

---

### S11: No `verify=False` in HTTP requests

**Applies to**: any `requests.get/post/Session` or `httpx` calls in the diff.

**Rule**: Disabling TLS certificate verification (`verify=False`) opens the connection to MITM attacks. Never disable it in production paths. Test helpers may use it only when connecting to a local mock server and must be clearly scoped to tests.

**Check**:
- Does the diff include `verify=False` or `ssl=False` in any HTTP call?
- Is it scoped to `tests/` only, with a comment explaining why?

---

### S12: Audit-sensitive operations use the audit log

**Applies to**: operations that create, update, or delete resources on behalf of a tenant (configuration writes, credential changes, subscription callbacks).

**Rule**: Mutating operations in multi-tenant contexts should emit an audit log entry via `sap_cloud_sdk.auditlog_ng` when the service they touch is subject to audit requirements. Missing audit entries in these paths are a compliance gap.

**Check**:
- Does the diff add new mutating operations (create/update/delete) on behalf of a tenant?
- Is an audit log call present or is there a documented reason it is not needed?
- This is ⚠️ (not ❌) if missing — flag it for the author to confirm scope.

---

### S13: No regression of published security advisories

**Applies to**: any PR that changes source under `src/`. Score `➖ N/A` only when the diff is limited to docs, CI, or pure test data with no source change. A source change in a module *different* from where an advisory was originally fixed still applies — vulnerability classes recur across modules.

**Rule**: The diff must not reintroduce (regress) a vulnerability that a published GitHub Security Advisory already fixed. A regression is either (a) **direct** — the diff removes, weakens, or bypasses the guard the fix added; or (b) **pattern reintroduction** — the diff adds new code that repeats the same vulnerability class elsewhere. Any confirmed regression of a published advisory is **❌ and blocking**, regardless of the advisory's original severity.

**Check**:
- **Fetch** the live advisory list (from Phase 2: `gh api repos/SAP/cloud-sdk-python/security-advisories`). If it returns nothing or access is denied → score **⚠️** with "could not fetch advisories; regression check not performed". Never score ✅ without having fetched the list.
- **Read** each advisory for detail and derive its **guard** (the check/function the fix introduced) and **call site(s)** (where the guard must run). Use `gh api repos/SAP/cloud-sdk-python/security-advisories/<GHSA>` and the linked fix commit / `references`.
- For each advisory, check both regression modes against the diff (quote the exact `file:line` via `Read /tmp/pr<NUMBER>/<path>`):
  - **Direct**: does the diff edit the guard or its call site to drop/weaken/bypass it? e.g. deleting a `_validate_tenant_subdomain(...)` call, flipping a `verify` flag, broadening a validation regex, or removing a fail-closed `return`.
  - **Pattern reintroduction (cross-module)**: does the diff add *new* code that repeats the fixed class in another module? e.g. a new client that builds a tenant/OAuth URL by host or string substitution without `_validate_tenant_subdomain`, reads JWT claims without signature verification, or joins external input into a path/URL without the `_validate_path_component` / `_assert_within_base` pattern.
- **Core strictness** — if the diff changes any file under `src/sap_cloud_sdk/core/` (any depth), raise the rigor: advisory guards live in core, and a past SSRF fix already regressed once because the HTTP client was refactored *into* core. In that case:
  - `➖ N/A` is not allowed for an advisory whose guard or call site is in core.
  - Verify guards **repo-wide, not just in the diff**: grep `src/` to confirm each core guard still exists *and* is still invoked at its call site in the current tree, then `Read` and quote the confirming line. A refactor can drop a call without editing the guard file.
  - Widen the pattern search to all modules that consume the changed core primitive (HTTP client under `core/protocol/http/`, `core/_tenant.py`, `core/runtime_context/`, `core/secret_resolver/`, auth/token helpers). A plausible but unconfirmed weakening here is `⚠️`, never silent `✅`.

---

## Phase 4: Report

```markdown
## Security Review: #<number>: <title>

**Author**: <author>  **Branch**: `<headRef>` → `<baseRef>`
**Verdict**: ✅ No security issues | ⚠️ Needs attention | ❌ Blocked

---

| # | Criterion | Status | Finding |
|---|-----------|--------|---------|
| S1 | Tenant subdomain validation | | |
| S2 | URL construction (structured, not str.replace) | | |
| S3 | Credential emptiness checks | | |
| S4 | JWT tokens verified before trust | | |
| S5 | No hardcoded credentials/secrets | | |
| S6 | Sensitive data not logged | | |
| S7 | No path traversal from external input | | |
| S8 | HTTP base URLs validated | | |
| S9 | Multi-tenant cache isolation | | |
| S10 | New dependencies checked for CVEs | | |
| S11 | No verify=False in HTTP calls | | |
| S12 | Audit log for mutating tenant operations | | |
| S13 | No regression of published advisories | | |

---

### ❌ Blocking Issues
- **[S1]**: <specific finding with file:line>

### ⚠️ Non-Blocking Suggestions
- **[S12]**: <finding>

### ✅ Things Done Well
- <observation>

### Unit Test Coverage Gaps
<list any security criteria that lack the required unit test cases>
```

Verdict: any ❌ → **Blocked** · any ⚠️ → **Needs attention** · all ✅/➖ → **No security issues**

S13 is a single roll-up row: its status is the worst outcome across all advisories, and its finding names the affected advisory with `file:line` (e.g. `<GHSA-id>: _validate_tenant_subdomain call removed at models.py:121`). A confirmed advisory regression is ❌ and forces **Blocked**.

---

## Phase 5: Unit Test Suggestions

For each ❌ or ⚠️ finding that involves missing unit tests, generate the missing test stubs. Follow the test conventions from `tests/core/unit/test_tenant.py` and `tests/core/unit/test_http_client.py`:

- Use `pytest.mark.parametrize` for input validation cases (valid inputs that must pass, invalid inputs that must raise).
- Test class name: `Test<SubjectClass>` or `Test<FunctionName>`.
- Test method name pattern: `test_<functionality>_<condition>_<expected_result>`.
- One assert per test where possible.
- Use `pytest.raises(ValueError, match="...")` for validation error assertions — include the expected message fragment.

Present test stubs as a diff or ready-to-paste code block. Do not write them to disk unless the user confirms.

---

## Phase 6 (Optional): Post Review

Ask: "Post as GitHub PR review? (comment / request-changes / approve / skip)"

```bash
gh pr review <number> --comment --body "<report>"
gh pr review <number> --request-changes --body "<report>"
```
