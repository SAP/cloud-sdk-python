Prepare a release for the changes on the current branch. Do the following steps in order:

## Step 1 — Understand the changes

Run `git diff main...HEAD` and `git log main...HEAD --oneline` to understand what was changed on this branch. Read all modified source files to understand the nature of the changes (new feature, bug fix, breaking change, docs, etc.).

## Step 2 — Determine the new version

Read `pyproject.toml` to get the current version. Apply SemVer rules based on the changes:
- PATCH bump: bug fixes, docs, refactors, non-breaking improvements
- MINOR bump: new non-breaking features or new public API surface
- MAJOR bump: breaking changes (changes to existing public API signatures or behavior)

Compute the new version string (no leading `v`).

## Step 3 — Bump version in pyproject.toml

Edit `pyproject.toml` and update `version = "..."` to the new version.

## Step 4 — Create PULL_REQUEST.md

Create `PULL_REQUEST.md` at the repo root following the structure of `.github/pull_request_template.md`. Fill it in based on what you learned from the diff:

- **Description**: clear summary of what changed and why
- **Related Issue**: leave as `Closes #` with a note to fill in the issue number
- **Type of Change**: check the relevant boxes (use `[x]`)
- **How to Test**: concrete steps to verify the change works
- **Checklist**: check all boxes that apply given the changes made
- **Breaking Changes**: fill in if applicable, otherwise remove the section
- **Additional Notes**: any relevant context for reviewers

> **Disclaimer:** Do not include SAP-internal or customer-specific information in this PR (e.g. internal system URLs, customer names, tenant IDs, or confidential configurations). This is a public repository.

## Step 5 — Create RELEASE.md

Create `RELEASE.md` at the repo root using this exact template structure:

```
## [vX.Y.Z] - MM DD, YYYY

### What's New
- ...

### Improvements
- ...

### Bug Fixes
- ...

### Breaking Changes
> ⚠️ **Important**: This section is critical for users upgrading from previous versions
- **[Breaking Change]**: ...

### Contributors
...
```

Fill in the version and today's date. Remove sections that don't apply. Infer the content from the diff — be specific about what changed (class names, method names, parameter names) so that users upgrading know exactly what to update.

## Step 6 — Summarize

Tell the user:
- The old and new version
- Which files were created/updated
- Any sections in PULL_REQUEST.md or RELEASE.md that still need manual input (e.g. issue number, contributors)
