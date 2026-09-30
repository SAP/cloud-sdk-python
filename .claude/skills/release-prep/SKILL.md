---
name: release-prep
description: Prepare a release issue for the SAP Cloud SDK for Python. Diffs the current branch against the latest tag, generates structured release notes, proposes a SemVer bump, confirms with the user, then creates a GitHub release issue with the correct labels so the automation pipeline can pick it up.
tools: Bash, Read
compatibility: gh CLI ≥ 2.0, git, GitHub write access to SAP/cloud-sdk-python
---

# Release Prep: SAP Cloud SDK for Python

Prepares a release by analysing what changed since the last tag, generating release notes, and creating the GitHub issue that drives the rest of the pipeline.

Run from the root of the `cloud-sdk-python` repository on the branch you intend to release.

---

## Phase 1: Pre-flight checks

Run all checks **in parallel**:

```bash
# 1a. Confirm we are inside the repo
git rev-parse --show-toplevel

# 1b. Get current branch name
git rev-parse --abbrev-ref HEAD

# 1c. Confirm the branch is pushed to origin and remote ref exists
git ls-remote --heads origin $(git rev-parse --abbrev-ref HEAD)

# 1d. Get the latest semver tag (the release baseline)
git tag --sort=-version:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+' | head -1

# 1e. Read current version from pyproject.toml
grep '^version = ' pyproject.toml | cut -d'"' -f2
```

**Fail fast** if:
- `1c` returns empty — the branch is not on origin. Tell the user: "Push the branch first (`git push -u origin HEAD`), then re-run `/release-prep`." Stop here.
- `1d` returns empty — no semver tag exists yet. Use the initial commit as the baseline and note this in the summary.

Capture:
- `CURRENT_BRANCH` — from 1b
- `LATEST_TAG` — from 1d (e.g. `v0.56.1`)
- `CURRENT_VERSION` — from 1e (e.g. `0.56.1`)

---

## Phase 2: Collect the diff

Run both commands **in parallel**:

```bash
# All commits between the latest tag and HEAD, in reverse chronological order
git log {LATEST_TAG}..HEAD --pretty=format:"%H %s" --reverse

# List of changed files (for breaking-change detection)
git diff {LATEST_TAG}..HEAD --name-only
```

If the log is empty (no commits since the last tag), tell the user: "No commits since `{LATEST_TAG}`. Nothing to release." Stop here.

---

## Phase 3: Classify commits and propose version

### 3.1 Classify by Conventional Commit type

For each commit subject, extract the type prefix (`feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `ci`, `perf`, `style`, `build`, `revert`).

Group commits into four buckets:

| Bucket | Conventional Commit types |
|---|---|
| **Breaking Changes** | any subject containing `!` after the type/scope, or `BREAKING CHANGE` in the footer |
| **New Features** | `feat` |
| **Bug Fixes** | `fix` |
| **Improvements & Other** | `refactor`, `perf`, `chore`, `docs`, `test`, `ci`, `style`, `build`, `revert`, unrecognised |

### 3.2 Determine bump type

Apply SemVer rules to the commits since `LATEST_TAG`:

| Condition | Bump |
|---|---|
| Any breaking change present | **major** |
| Any `feat` commit present (no breaking changes) | **minor** |
| Only fixes, refactors, docs, chores, etc. | **patch** |

### 3.3 Compute proposed version

Parse `CURRENT_VERSION` as `MAJOR.MINOR.PATCH` and increment the appropriate segment. Reset lower segments to `0`.

Example: `0.56.1` + minor → `0.57.0`.

---

## Phase 4: Generate release notes

Produce a markdown string following the exact structure below. Omit sections that have no entries.

```markdown
### What's New
- **[scope]**: description of feat commit (commit abc1234)
- ...

### Improvements
- **[scope]**: description (commit abc1234)
- ...

### Bug Fixes
- **[scope]**: description (commit abc1234)
- ...

### Breaking Changes
> ⚠️ **Important**: Migration steps for users upgrading from `{LATEST_TAG}`.
- **[scope]**: description and what the user must change (commit abc1234)
- ...
```

Rules:
- Use the commit scope (the part in parentheses) as the bold prefix. If no scope, omit the bold prefix.
- Write in present tense, third person (e.g. "adds", "fixes", "removes").
- Be specific about class/method/parameter names that changed.
- Include the short commit SHA `(commit abc1234)` at the end of each bullet so it is traceable.
- Do **not** include `chore`, `ci`, `test`, `docs`-only commits in the release notes unless they represent a notable change visible to SDK users.

---

## Phase 5: Present and confirm

Show the user a preview in this exact format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Release Prep Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Branch:        {CURRENT_BRANCH}
  Baseline tag:  {LATEST_TAG}
  Commits:       N commits analysed
  Bump type:     patch | minor | major
  Version:       {CURRENT_VERSION}  →  {PROPOSED_VERSION}

  Release Notes preview:
  ──────────────────────
  {RELEASE_NOTES}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Ask the user:

> "Does this look correct? You can accept, or provide a different version / bump type. Reply `yes` to create the release issue, `no` to cancel, or type a version override (e.g. `0.58.0`)."

If the user provides a version override, re-derive the bump type from the override vs `CURRENT_VERSION` and update `PROPOSED_VERSION`. If the override is not a valid SemVer / PEP 440 string, tell the user and ask again.

If the user says `no`, stop here with: "Release prep cancelled. No issue was created."

---

## Phase 6: Create the release issue

Once the user confirms, run the following (do **not** modify `pyproject.toml` — the GitHub Action owns that step):

### 6.1 Build the issue body

Construct the issue body using the GitHub issue form field IDs so the structured data is machine-parseable by the release workflow:

```markdown
### Version

{PROPOSED_VERSION}

### Bump Type

{bump_type}

### Branch

{CURRENT_BRANCH}

### Release Notes

{RELEASE_NOTES}

### Breaking Changes

{BREAKING_CHANGES_SECTION or "_None_"}
```

> **Important:** The section headers (`### Version`, `### Branch`, etc.) must match the issue template field labels exactly — the release GitHub Action parses the body using these anchors.

### 6.2 Create the issue

```bash
gh issue create \
  --repo SAP/cloud-sdk-python \
  --title "Release v{PROPOSED_VERSION}" \
  --label "release" \
  --label "status: pending tests" \
  --body "{ISSUE_BODY}"
```

If `gh issue create` fails because the labels do not exist yet, tell the user:

> "Labels are missing from the repo. Create them first by running:
> `gh label create 'release' --color '0052CC' --description '...' --repo SAP/cloud-sdk-python`
> (or apply `.github/labels.yml` via the sync-labels workflow), then re-run `/release-prep`."

### 6.3 Summary

After the issue is created, print:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Release issue created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Issue:    #{NUMBER} — {ISSUE_URL}
  Version:  {PROPOSED_VERSION}
  Branch:   {CURRENT_BRANCH}

  Next steps (automated):
  1. Automation test repo picks up the issue (label: status: pending tests)
  2. Tests run against branch {CURRENT_BRANCH}
  3. On success → label updated to "status: tests passed"
  4. Release workflow triggers → bumps pyproject.toml, builds, publishes to PyPI,
     creates GitHub Release, tags commit, closes this issue

  If tests fail:
  → Issue is labelled "status: tests failed". Fix the branch and re-run /release-prep.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
