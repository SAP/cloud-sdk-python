---
name: review-pr
description: Review a pull request against all cloud-sdk-python contribution standards. Use when you want to review a PR, check if a PR is ready to merge, or get structured feedback on pending changes.
tools: Bash, Read
compatibility: gh CLI ≥ 2.0, git, GitHub access to SAP/cloud-sdk-python
---

# PR Review: SAP Cloud SDK for Python

Reviews a PR against 23 criteria across 6 sections. Run from the root of the `cloud-sdk-python` repository.

---

## Phase 1: Identify the PR

Determine `REPO` and `NUMBER` from what the user provided:

- **Full GitHub URL** (e.g. `https://github.com/<owner>/cloud-sdk-python/pull/1`):
  parse `REPO=<owner>/cloud-sdk-python`, `NUMBER=1`.
- **`owner/repo#number`** (e.g. `<owner>/cloud-sdk-python#1`):
  parse accordingly.
- **Plain number** (e.g. `93`):
  `REPO=SAP/cloud-sdk-python`, `NUMBER=93`.
- **Nothing provided**: list open PRs from the default repo and ask the user to pick one:
  ```bash
  gh pr list --repo SAP/cloud-sdk-python --state open --json number,title,author,headRefName
  ```

Use `REPO` and `NUMBER` in every subsequent command.

---

## Phase 2: Gather Data

**Step 1** — Run all five commands **in parallel**:

```bash
gh pr view <NUMBER> --repo <REPO> --json number,title,body,state,labels,headRefName,baseRefName,author,commits,reviews,reviewRequests,files,additions,deletions
```
```bash
gh pr diff <NUMBER> --repo <REPO>
```
```bash
gh pr checks <NUMBER> --repo <REPO> 2>/dev/null || echo "CI checks not yet available"
```
```bash
gh pr view <NUMBER> --repo <REPO> --comments
```
```bash
gh pr view <NUMBER> --repo <REPO> --json commits --jq '.commits[].messageHeadline'
```

**Step 2** — Fetch each changed file at the PR head ref for accurate line references.

From the `files` array in Step 1, for each non-binary file run (in parallel):

```bash
mkdir -p /tmp/pr<NUMBER>/$(dirname <path>)
gh api "repos/<REPO>/contents/<path>?ref=<headCommitSHA>" \
  -H "Accept: application/vnd.github.raw+json" \
  > /tmp/pr<NUMBER>/<path>
```

Use the head **commit SHA** (not the branch name) as the ref — branch names are ambiguous for forks.

Skip files larger than 500 KB or with binary extensions (`.png`, `.jpg`, `.whl`, `.gz`, etc.).

This gives you the full file content at the exact PR state, which you will use in Phase 3 for all `file:line` citations.

---

## Phase 3: Evaluate 23 Criteria

Assign each: **✅ Pass** / **⚠️ Warning** / **❌ Fail** / **➖ N/A**

For every `file:line` reference: use `Read /tmp/pr<NUMBER>/<path>` on the files fetched in Phase 2. Line numbers in that output are exact. Do not derive line positions from diff hunk offsets — diff arithmetic is unreliable.

If you need to verify a specific rule, read the authoritative source directly:
- `CONTRIBUTING.md`
- `docs/GUIDELINES.md`
- `docs/DEVELOPMENT.md`
- `.github/pull_request_template.md`
- `.github/workflows/` (exact CI job names)

---

### Section A: Process & Compliance

**A1: PR template complete**
Template requires: Description, Related Issue, Type of Change (one box ticked), How to Test (numbered steps), checklist of 9 items all ticked. Empty or placeholder body → ❌.

**A2: Conventional Commits**
Every commit headline must match `type(scope): description`. Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `perf`, `style`, `build`, `revert`. PR title is also validated. Check `commit-validation` CI job. Quote failing commit titles.

**A3: Issue linked**
PR body must contain `Closes #N`, `Fixes #N`, or `Resolves #N`.

**A4: AI-generated code disclosure**
If the diff looks AI-generated, the PR description must explicitly disclose it and reference the [SAP AI contribution guideline](https://github.com/SAP/.github/blob/main/CONTRIBUTING_USING_GENAI.md). Required by `CONTRIBUTING.md`.

---

### Section B: Security & Sensitive Data

**B1: No sensitive data in code**
Scan diff for: hardcoded credentials/tokens/API keys, SAP-internal URLs (non-public hostnames or internal tooling URLs that should not be in a public repo), tenant IDs as literals, customer names, environment-specific configs. Any hit → ❌.

**B2: No sensitive data in PR body**
Check the PR body for the same categories as B1: account-specific URLs containing GUIDs or subaccount identifiers, real tenant IDs, internal email addresses, internal tooling references (e.g., Slack channels, internal issue trackers). The PR template disclaimer applies.

---

### Section C: Code Quality

**C1: CI checks passing**
| Job name | Meaning |
|---|---|
| `Code Quality Checks` | ruff lint + ruff format + ty type check |
| `Unit Tests with Coverage` | pytest, coverage ≥ 80% |
| `Build SDK` | `uv build` produces `.whl` + `.tar.gz` |
| `commit-validation` | commitlint on all commits |
| `Enforce version bump when src/ is modified` | version must increase if `src/` changed |
| `Verify generated proto code is up-to-date` | only for proto changes |
| `Analyze (python)` | CodeQL security scan |

Any required job ❌ → overall ❌. Pending → ⚠️.

**C2: Version bump**
If diff touches any `src/` file: `version` in `pyproject.toml` MUST be incremented (semver). Only `docs/`, `tests/`, `.github/`, `.claude/` changed → ➖ N/A.

**C3: Type hints**
All new/modified public functions, methods, class attributes must have full annotations (params + return type). New modules need `py.typed`. Missing `Optional`, `Union`, or return type on a public method → ⚠️ or ❌.

**C4: No hardcoded values**
No magic strings (e.g., `/etc/secrets/appfnd` inline) or magic numbers. Use module-level constants or enum values.

**C5: Import organization**
Top-level imports preferred (PEP 8). Lazy imports inside functions are a smell without a documented circular-import reason. No `requirements-*.txt` for deps already in `pyproject.toml`.

**C6: Naming conventions**
- Enum values: `SCREAMING_SNAKE_CASE = "snake_case_value"` (e.g., `AGENT_GATEWAY = "agent_gateway"`)
- Enum members and module-level lists: alphabetical order
- Private methods/attributes/modules: leading underscore
- File names: `snake_case.py`
- GitHub workflow files: `.yaml` extension, not `.yml`

**C7: No unused code**
No unused imports, variables, or dead methods introduced.

**C8: No unjustified new dependencies**
New runtime dep in `pyproject.toml`: must be minimal, justified, checked for CVEs. No duplicate `requirements-*.txt` alongside `pyproject.toml`.

**C9: Proto code freshness**
If `.proto` files under `src/sap_cloud_sdk/core/auditlog_ng/proto/` changed: "Verify generated proto code is up-to-date" CI job must pass.

---

### Section D: API & Design

**D1: API future-proofing**
New config/behavior options should be a `*Config` dataclass, not individual params. Enums over bare string constants. `create_client()` factory present; direct constructor warns users to use factory instead.

**D2: Public API hygiene**
`__init__.py` and `__all__` expose only genuinely public symbols. Internal helpers prefixed `_`. No unnecessary wrapper classes (wrapping `requests.Session` 1:1 without adding value).

**D3: Breaking changes properly marked**
Breaking = removing/renaming a public function/method/param, changing return type, making optional param required. If present and NOT marked with the "Breaking Changes" checkbox + migration section → ❌.

**D4: Pagination & tenant filtering consistency**
New list/query operations: encapsulate pagination params like existing modules (see `destination`). Tenant-scoped operations: filter by tenant property for consistency.

**D5: Telemetry instrumentation**
New client methods: `@record_metrics(Module.X, Operation.Y)` from `core/telemetry`. New module: constant added to `core/telemetry/module.py` and operations to `core/telemetry/operation.py`. If module is called by other SDK modules: `_telemetry_source: Optional[Module] = None` param present.

---

### Section E: Tests & Documentation

**E1: Tests added/updated**
Every changed `src/` file → corresponding change in `tests/`. Unit: `tests/[module]/unit/test_*.py`. Integration (BDD): `tests/[module]/integration/*.feature` + `test_*_bdd.py`. Test names: `test_<functionality>_<condition>_<expected_result>`. New env vars for integration tests documented in `.env_integration_tests`.

**E2: Documentation quality**
New modules: `user-guide.md` with overview, quick start, config examples, API examples, troubleshooting. Changed public APIs: docstrings updated (Google/NumPy style: `Args:`, `Returns:`, `Raises:`). Sub-audience features not mixed into the general user guide.

**E3: Module structure compliance**
New modules follow:
```
src/sap_cloud_sdk/[module]/
├── __init__.py   (create_client(), __all__)
├── client.py     (or {service}_client.py)
├── config.py     (load_from_env_or_mount(), *Config dataclass)
├── exceptions.py (exception hierarchy)
├── _models.py    (Pydantic models)
├── py.typed      (empty PEP 561 marker)
└── user-guide.md

tests/[module]/unit/
tests/[module]/integration/  (optional, BDD)
```

---

## Phase 4: Report

```markdown
## PR Review: #<number>: <title>

**Author**: <author>  **Branch**: `<headRef>` → `<baseRef>`
**Verdict**: ✅ Ready to Merge | ⚠️ Needs Minor Work | ❌ Blocked
**Summary**: <one sentence>

---

### A: Process & Compliance
| # | Criterion | Status | Finding |
|---|-----------|--------|---------|
| A1 | PR template complete | | |
| A2 | Conventional Commits | | |
| A3 | Issue linked | | |
| A4 | AI-generated code disclosure | | |

### B: Security & Sensitive Data
| # | Criterion | Status | Finding |
|---|-----------|--------|---------|
| B1 | No sensitive data in code | | |
| B2 | No sensitive data in PR body | | |

### C: Code Quality
| # | Criterion | Status | Finding |
|---|-----------|--------|---------|
| C1 | CI checks passing | | |
| C2 | Version bump | | |
| C3 | Type hints | | |
| C4 | No hardcoded values | | |
| C5 | Import organization | | |
| C6 | Naming conventions | | |
| C7 | No unused code | | |
| C8 | No unjustified new dependencies | | |
| C9 | Proto code freshness | | |

### D: API & Design
| # | Criterion | Status | Finding |
|---|-----------|--------|---------|
| D1 | API future-proofing | | |
| D2 | Public API hygiene | | |
| D3 | Breaking changes marked | | |
| D4 | Pagination & tenant filtering | | |
| D5 | Telemetry instrumentation | | |

### E: Tests & Documentation
| # | Criterion | Status | Finding |
|---|-----------|--------|---------|
| E1 | Tests added/updated | | |
| E2 | Documentation quality | | |
| E3 | Module structure compliance | | |

---

### ❌ Blocking Issues
- **[C2]**: <specific finding with file:line>

### ⚠️ Non-Blocking Suggestions
- **[C6]**: <suggestion>

### ✅ Things Done Well
- <observation>
```

Verdict: any ❌ → **Blocked** · any ⚠️ → **Needs Minor Work** · all ✅/➖ → **Ready to Merge**

---

## Phase 5 (Optional): Post Review

Ask: "Post as GitHub PR review? (comment / request-changes / approve / skip)"

```bash
gh pr review <number> --comment --body "<report>"
gh pr review <number> --request-changes --body "<report>"
gh pr review <number> --approve --body "<report>"
```
