# Dependency Management

This document describes how dependencies are kept up to date in the SAP Cloud SDK for Python.

## Automated updates

[Dependabot](https://docs.github.com/en/code-security/dependabot) runs automatically and opens PRs to keep dependencies current.

| Ecosystem | Schedule | Grouping |
|---|---|---|
| Python (`pip`) | Weekly, Monday 09:00 | Minor + patch updates batched into one PR; each major in its own PR |
| GitHub Actions | Monthly, Monday 09:00 | All updates batched into one PR |
| Security fixes | As detected | Separate grouped PR, independent of the weekly schedule |

## Auto-merge policy

Minor and patch updates are merged automatically once all required checks pass — no manual approval needed. This keeps `main` current without creating review burden for low-risk bumps.

Major version updates are left open for manual review. Dependabot will comment on the PR to flag it. A maintainer should:

1. Review the changelog and migration guide for the new major version
2. Update any affected code
3. Approve and merge manually

## Releases

Dependency bumps that land on `main` via auto-merge are not automatically released. They accumulate with other changes and are included in the next release triggered via the **Prepare Release** workflow.

The exception is security fixes — these should be released promptly. After a security Dependabot PR is merged, trigger a patch release manually:

**Actions → Prepare Release → Run workflow** with `branch=main` and an explicit `version=X.Y.Z` patch bump.

See [RELEASE.md](RELEASE.md) for the full release process.
