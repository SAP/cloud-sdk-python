# SDK Module Review

Every PR to this repo is reviewed automatically by the **SDK Module Review** skill.
This document explains what it checks, how to interact with findings, and how to tune noisy rules.

> **Required before review.** The `sdk-module-review` check-run must be green **before a maintainer will review the PR**. It is a required status check in branch protection — merges are blocked until it passes. Reviewers will not spend time on PRs where the automated review is failing.

---

## How it runs

**Automatic (GitHub Action):** fires on every PR event (`opened`, `synchronize`, `reopened`, `ready_for_review`). No action needed from the contributor — the review appears on the PR within a minute or two.

**Manual (maintainer, via CLI):**
```bash
gh workflow run sdk-module-review.yml -f pr_number=<N>
```

**Local (dev iteration, requires Claude Code):**
```
/review-new-module <PR_NUMBER>            # full review, posts to PR
/review-new-module <PR_NUMBER> --dry-run  # analysis only, prints locally
```

The skill is **100% deterministic** — no LLM calls in CI. Every run on the same
commit produces the same findings.

---

## Signals posted to your PR

Every run posts up to four signals:

1. **Inline comments** — one per finding, anchored to `file:line` in the diff
2. **Summary comment** — aggregated table of all check results in an issue comment
3. **Check-run** — appears in the "Checks" tab (green ✅ or red ❌)
4. **PR label** — `sdk-review: ✅ passed` / `❌ blocked` / `⚠️ flagged` / `skipped`

On re-run (push more commits, dispatch workflow again), all four artifacts are
**replaced** — you won't see duplicate comments accumulating.

---

## Severities

- **BLOCK** — must fix before merge. Check-run fails; branch protection refuses the merge.
- **FLAG** — should fix; does not block merge. Check-run passes with warning.
- **PASS** — no findings for this check.
- **SHADOW** — internal telemetry; not posted, used to evaluate new rules before promoting them.

Some rules are **locked** (marked `BLOCK_LOCKED` in `.claude/config/rules.yaml`).
Locked rules cannot be suppressed via inline comments or downgraded via config —
they are safety-critical (secrets, license, SAP-internal URL leaks, breaking-change
declarations).

---

## What the skill checks

20 checks · ~150 rules. Configured in [`.claude/config/rules.yaml`](../.claude/config/rules.yaml).

| Check | Purpose |
|-------|---------|
| **secrets** | AWS keys, JWT, GitHub PATs, private keys, plaintext credentials |
| **license-spdx** | SPDX headers on new source files (respects `REUSE.toml`) |
| **disclosure** | No SAP-internal URLs, ORD IDs, internal Jira in public artifacts |
| **hardcode** | No hardcoded URLs, credentials, magic timeouts |
| **telemetry** | `@record_metrics` decorator on public client methods + emission tests |
| **docs** | `user-guide.md` completeness including BTP dep + regional availability |
| **bdd** | Feature files exist + cross-language parity |
| **patterns** | Factory pattern, exception hierarchy, type hints, `py.typed` |
| **versioning** | SemVer bump matches diff scope; BREAKING family fires on API changes |
| **commits** | Conventional Commits |
| **errors-logging** | `raise X from e` chaining, no sensitive info in exception messages |
| **testing-depth** | Bug fixes have tests; new modules have integration tests |
| **http-hygiene** | Session reuse, configurable timeouts |
| **concurrency** | `asyncio.Queue` dedup, thread safety on shared state |
| **deps-supply** | Dep justification, lockfile drift, no internal artifactory |
| **deletion-hygiene** | Removed symbols have zero residual references |
| **constants** | Magic values → constants/enums |
| **binding-shape** | BTP binding parsing (no `url + "/oauth/token"` concat) |
| **quality-gate-parity** | CI runs the full dev gate (ruff + format + typecheck) |
| **pr-size** | Advisory on large PRs (recommends stacked-PR workflow) |

---

## Documenting BTP dependencies (DC-11..DC-16)

If your module imports `destination`, `Fragment*`, `Certificate*`, or has
region-specific constants, `user-guide.md` **must** contain the corresponding
section. The skill fires **BLOCK** if these are missing:

- **DC-11** — `destination` import → `## Dependencies` section mentioning "Destination Service"
- **DC-12** — Fragment usage → same section + `create_fragment_client` example
- **DC-13** — Certificate usage → same section + `create_certificate_client` example
- **DC-14** — Region constants → `## Regional Availability` section listing supported/unsupported regions
- **DC-15** — Reads `VCAP_SERVICES` → `## Configuration` section with sample binding JSON
- **DC-16** — Cross-module SDK dep → note in `## Dependencies`

### Example templates

**DC-11 Destination Service required:**
```markdown
## Dependencies

This module requires **SAP BTP Destination Service**:
- Service instance name: `default` (configurable via `create_client(instance="...")`)
- Required binding: `xsuaa` credentials + `destination` service credentials
- Mount path: `/etc/secrets/sapbtp/destination/<instance>/`
- Local dev: set `CLOUD_SDK_LOCALDEV_DESTINATION=true` to use mock backing
```

**DC-14 Regional Availability:**
```markdown
## Regional Availability

Available in the following BTP regions:
- ✅ `eu10` (Frankfurt)
- ✅ `us10` (Ashburn)
- ✅ `ap11` (Singapore)
- ❌ `cn40` (Shanghai) — not supported due to <reason>
```

---

## Breaking changes (BREAKING-01..04)

If your diff contains a **breaking change** (public API removal, method signature
change, dataclass field deletion, enum value removal, exception hierarchy change),
the skill requires:

1. Commit message uses `feat!:` or `fix!:` prefix
2. PR body has a `## Breaking Changes` section with **non-empty** content
3. PR body ticks the "Breaking change" checkbox
4. `pyproject.toml` / `pom.xml` version is bumped MINOR (or MAJOR if pre-1.0)
5. Migration path documented in PR body or `RELEASE.md`

All four must be true — half-declared breakages are BLOCKed. This is enforced by
`BREAKING-01` and `BREAKING-02`, both `BLOCK_LOCKED` (cannot be suppressed).

---

## Incremental delivery for large contributions

For features exceeding ~500 lines or touching multiple modules, prefer **stacked PRs**:

1. Open a feature branch off `main`: `feat/<capability>`
2. Send small, isolated PRs (≤400 lines each) targeting **your feature branch**
3. Each sub-PR passes CI standalone
4. When feature is complete, open a final PR from your feature branch to `main`

The skill flags `PR-SIZE-01..05` (currently SHADOW tier — logged only) when a PR
exceeds thresholds. See `CONTRIBUTING.md § Incremental Delivery`.

---

## Suppressing false positives

If a rule fires incorrectly on a specific line, add a comment:

```python
# Python
timeout = 30  # sdk-review: ignore[hardcode]
```

```java
// Java
final int timeout = 30;  // sdk-review: ignore[hardcode]
```

Or for an entire file (first 20 lines):
```python
# sdk-review-ignore-file: hardcode,patterns
```

**You cannot suppress:**
- Any `SEC-*` rule (secrets)
- `HC-03` (SAP-internal URL leak)
- `DIS-06` (internal artifactory `--index-url`)
- `LIC-01/02` (SPDX headers)
- `BND-02` (BTP token URL concat)
- `BND-05` (binding logs credentials)
- `BREAKING-*` family

These are locked. Fix the finding or open a discussion with maintainers.

---

## When cross-language BDD parity can't be verified

The skill checks that new modules have BDD feature files in **both** SDKs (Python
and Java). If the sibling repo can't be reached (SSO required, network unavailable,
missing checkout), `check-bdd.sh` degrades to a FLAG "cross-language parity not
verified" instead of blocking.

The alias map at `.claude/config/module-aliases.yaml` handles name divergences
(e.g., Python `dms` ↔ Java `documentmanagement`).

---

## Re-running

Just push a new commit — the Action reruns automatically and replaces prior
review artifacts. Or dispatch manually:

```bash
gh workflow run sdk-module-review.yml -f pr_number=<N>
```

---

## Tuning noisy rules

Maintainers can adjust rule severity or disable rules in
`.claude/config/rules.yaml`:

```yaml
rules:
  HC-04:
    tier: OFF     # disable
  # or
  HC-04:
    tier: FLAG    # downgrade from BLOCK to FLAG
```

Locked rules ignore these overrides.

---

## What if something breaks?

- **False positive that survived suppression** → open an issue with label `sdk-review-tuning`
- **Skill errors on your PR** → open an issue with label `sdk-review-bug`
- **Suggested new rule** → open an issue with label `sdk-review-enhancement`

---

## Reference

- Rule catalog: [`.claude/config/rules.yaml`](../.claude/config/rules.yaml)
- Module aliases: [`.claude/config/module-aliases.yaml`](../.claude/config/module-aliases.yaml)
- Baseline exemptions: [`.claude/config/baseline.json`](../.claude/config/baseline.json)
- Check scripts: [`.claude/scripts/check-*.sh`](../.claude/scripts/)
- Orchestrator: [`.claude/scripts/orchestrate.sh`](../.claude/scripts/orchestrate.sh)
- Workflow: [`.github/workflows/sdk-module-review.yml`](../.github/workflows/sdk-module-review.yml)
