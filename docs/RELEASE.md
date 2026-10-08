# Release and Deployment Guide

This guide describes the automated release pipeline for the SAP Cloud SDK for Python.

## Versioning

We follow SemVer: `MAJOR.MINOR.PATCH` (see [SemVer](https://semver.org/)) and PEP 440. Use `X.Y.ZrcN` for release candidates.

The version in `pyproject.toml` is **managed automatically** by the release workflow — do not bump it manually.

---

## Release Pipeline Overview

```
Merge to main (or any release branch)
        │
        ▼
Run "Prepare Release" workflow manually
  Diffs branch against latest tag → generates release notes
  Creates a draft GitHub Release (vX.Y.Z) — tag created here
  Creates a release branch, bumps pyproject.toml, opens auto-merge PR
        │
        ▼
Review and edit the draft release notes in GitHub
        │
        ▼
Automation test repo runs tests against the branch
  On success → publishes the draft release (removes draft flag)
        │
        ├─── Tests fail → draft stays unpublished (investigate and retry)
        │
        └─── Tests pass → draft is published → Release workflow triggers
                │
                ▼
        Release workflow runs automatically
          1. Runs integration tests against the branch
          2. Builds the distribution (uv build)
          3. Uploads artifacts to the GitHub Release
          4. Publishes to PyPI via OIDC trusted publishing
```

---

## Step 1 — Prepare and merge your PR

On your feature or hotfix branch, run `/prep-pr` to fill in the PR template from the diff, get it reviewed, approved, and merged into `main`.

```
/prep-pr
```

---

## Step 2 — Prepare the release

Once the branch is ready to release, trigger the **Prepare Release** workflow from the Actions tab:

**Actions → Prepare Release → Run workflow**

| Input | Required | Description |
|---|---|---|
| `branch` | Yes | Branch to release from (e.g. `main`) |
| `version` | No | Target version (e.g. `0.58.0`) — must be greater than the current version. Leave blank for an automatic minor bump. |

The workflow will:
1. Read the current version from `pyproject.toml` on the selected branch
2. Compute the target version (or validate the one you provided)
3. Diff commits since the last tag and generate structured release notes
4. Create a **draft** GitHub Release at `vX.Y.Z` targeting the selected branch — the git tag is created at this point
5. Open a version bump PR (`chore(release): bump version to X.Y.Z`) that auto-merges back into the branch

---

## Step 3 — Review the draft release

Go to **Releases** and open the draft. Review and edit the release notes as needed before the automation tests run.

To skip the integration test step in the release workflow, add the text `skip-integration-tests` anywhere in the release body.

---

## Step 4 — Automated tests (handled by the automation repo)

The automation test repo detects the draft release, runs the integration test suite against the branch, and on success publishes the draft (removes the draft flag). This triggers the Release workflow automatically.

If tests fail, the draft remains unpublished. Fix the branch and re-trigger the test run from the automation repo.

---

## Step 5 — Automated release (no action required)

When the draft is published, the `Release` workflow triggers automatically and:

1. Runs the full integration test suite against the branch (skippable — see Step 3)
2. Builds the distribution with `uv build`
3. Uploads build artifacts (wheel + sdist) to the GitHub Release
4. Publishes to PyPI via OIDC trusted publishing

Monitor progress in the **Actions** tab. On success the package is available at:

```
https://pypi.org/project/sap-cloud-sdk/X.Y.Z/
```

---

## Release candidates

To publish a release candidate, trigger the **Prepare Release** workflow with a version like `0.58.0rc1`. The GitHub Release is automatically marked as pre-release when the version is a PEP 440 pre-release string.

Install explicitly:

```bash
pip install sap-cloud-sdk==0.58.0rc1
```

---

## Handling failures

### Tests failed

The draft release remains unpublished. Investigate the failures in the automation test repo, fix the branch, and re-trigger the test run. The same draft release can be reused — no need to create a new one unless the version changes.

### Release workflow failed

Check the failed workflow run linked in the Actions tab. Common causes:

| Symptom | Fix |
|---|---|
| Version already on PyPI | The version was already published — create a new draft with a higher version |
| Tag already exists | Delete the tag (`git push origin :refs/tags/vX.Y.Z`) and re-publish the draft |
| Build failed | Fix the source, push to the branch, delete the draft release, and re-run the Prepare Release workflow |

---

## Install

```bash
# Latest stable
pip install sap-cloud-sdk

# Specific version
pip install sap-cloud-sdk==0.58.0

# Release candidate
pip install sap-cloud-sdk==0.58.0rc1
```
