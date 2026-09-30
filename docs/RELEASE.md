# Release and Deployment Guide

This guide describes the automated release pipeline for the SAP Cloud SDK for Python.

## Versioning

We follow SemVer: `MAJOR.MINOR.PATCH` (see [SemVer](https://semver.org/)) and PEP 440. Use `X.Y.ZrcN` for release candidates.

The version in `pyproject.toml` is **managed automatically** by the release workflow — do not bump it manually.

---

## Release Pipeline Overview

```
Developer works on a feature/hotfix branch
        │
        ▼
Run /prep-pr to fill in the PR template, open or update the PR
        │
        ▼
PR is reviewed and approved
        │
        ▼
Run /release-prep on the feature/hotfix branch
  Diffs branch against latest tag → proposes version + release notes
  Creates GitHub Release Issue with the branch name embedded
  Labels: release + status: pending tests
        │
        ▼
Automation test repo detects the issue, runs tests against the branch
  Labels during run: status: tests running
        │
        ├─── Tests fail → status: tests failed  (investigate and retry)
        │
        └─── Tests pass → status: tests passed
                │
                ▼
        Release workflow triggers automatically
          1. Bumps pyproject.toml, commits, pushes to the branch
          2. Creates and pushes the git tag (vX.Y.Z)
          3. Builds the distribution (uv build)
          4. Creates the GitHub Release with release notes and artifacts
          5. Publishes to PyPI via OIDC trusted publishing
          6. Closes the release issue (status: released)
        │
        ▼
Merge the branch into main (the version bump commit is already on it)
```

---

## Step 1 — Prepare and open your PR

On your feature or hotfix branch, run `/prep-pr` to fill in the PR template from the diff, then get it reviewed and approved. Do **not** merge yet.

```
/prep-pr
```

---

## Step 2 — Run `/release-prep` on the same branch

Before merging, while still on the feature/hotfix branch, run:

```
/release-prep
```

The skill will:
1. Find the latest release tag and diff from there to `HEAD` on the current branch
2. Classify commits by Conventional Commit type and propose a SemVer bump
3. Generate structured release notes
4. Show a preview and ask you to confirm or override the version
5. Create the GitHub Release Issue referencing this branch, with labels `release` + `status: pending tests`

> The version in `pyproject.toml` is **not** touched at this point — the release workflow owns that step.

---

## Step 3 — Wait for automated tests

Once the issue is created, the automation test repo detects it (via the `status: pending tests` label) and runs the integration test suite against the branch. You can track progress on the release issue — the label updates automatically:

| Label | Meaning |
|---|---|
| `status: pending tests` | Waiting for the automation repo to pick up the issue |
| `status: tests running` | Tests in progress |
| `status: tests passed` | Tests passed — release workflow will trigger shortly |
| `status: tests failed` | Tests failed — see [Handling failures](#handling-failures) |

---

## Step 4 — Automated release (no action required)

When the label changes to `status: tests passed`, the `Release` workflow triggers automatically and:

1. Parses the version and branch from the issue body
2. Bumps `version` in `pyproject.toml`, commits `chore(release): bump version to X.Y.Z`, and pushes to the branch
3. Creates and pushes the annotated git tag `vX.Y.Z`
4. Builds the distribution with `uv build`
5. Creates the GitHub Release with the release notes and build artifacts attached
6. Publishes to PyPI via OIDC trusted publishing
7. Posts a comment on the issue with links to PyPI and the GitHub Release, then closes it

Monitor progress in the **Actions** tab. On success the package is available at:

```
https://pypi.org/project/sap-cloud-sdk/X.Y.Z/
```

---

## Step 5 — Merge the branch

Once the release workflow completes, the branch has the `chore(release): bump version to X.Y.Z` commit on it. Merge (or complete the PR merge) into `main` so the version bump lands on the main branch.

---

## Release candidates

To publish a release candidate, follow the same process with a version like `0.57.0rc1`. The skill will propose a pre-release version if all unreleased commits are on a feature-frozen RC branch.

The GitHub Release is automatically marked as pre-release when the version is a PEP 440 pre-release. Install explicitly:

```bash
pip install sap-cloud-sdk==0.57.0rc1
```

---

## Handling failures

### Tests failed (`status: tests failed`)

Investigate the failures in the automation test repo. Fix the branch, then either:
- Re-run `/release-prep` to create a new release issue, or
- Manually remove `status: tests failed` and add `status: pending tests` to re-trigger the automation test run on the same issue

### Release workflow failed (`status: release failed`)

Check the failed workflow run linked in the issue comment. Common causes:

| Symptom | Fix |
|---|---|
| Version already on PyPI | The version was already published — bump to the next patch and re-run `/release-prep` |
| Tag already exists | Delete the tag (`git push origin :refs/tags/vX.Y.Z`) and re-trigger |
| Build failed | Fix the source, push to the branch, then force-release (see below) |

### Force a release (bypass tests)

If you need to publish without waiting for the automation test repo (e.g. for a critical hotfix already validated manually):

1. Open the release issue
2. Remove any `status: *` label currently on it
3. Add the label `status: tests passed`

The release workflow triggers immediately.

---

## Install

```bash
# Latest stable
pip install sap-cloud-sdk

# Specific version
pip install sap-cloud-sdk==0.57.0

# Release candidate
pip install sap-cloud-sdk==0.57.0rc1
```
