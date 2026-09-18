# Release and Deployment Guide

This guide consolidates the full release and deployment process for the Cloud SDK for Python, including versioning policy, preparation steps, tagging, GitHub release notes, and artifact publication.

## Versioning

- We follow SemVer: MAJOR.MINOR.PATCH (see [SemVer](https://semver.org/))

## Prepare the Release

1. Create a feature branch from main
   ```bash
   git checkout main && git pull
   git checkout -b branch-name
   ```

2. Bump version

   - In `pyproject.toml`: set `project.version = "X.Y.Z"` (PEP 440; no leading 'v')
   - Run `uv lock` so the project version in `uv.lock` matches
   - Use `X.Y.Zrc1`, `X.Y.Zrc2`, and so on for release candidates

3. Commit changes

   ```bash
   git add pyproject.toml uv.lock
   git commit -m "feat: did something"
   ```

4. Push and open PR, get approval and merge

   ```bash
   git push -u origin branch-name
   ```
   - Merge commit message should follow Conventional Commits
   - Example: `feat(): add xyz`
   - See: [Conventional Commits](https://www.conventionalcommits.org/)

### Release candidate cycle

After the first release candidate (`X.Y.Zrc1`), that release line is feature-frozen. If a blocking issue requires a code change, publish and validate another release candidate (`X.Y.Zrc2`, `X.Y.Zrc3`, and so on) before the stable release.

To promote the final release candidate, open a pull request that changes the version from `X.Y.ZrcN` to `X.Y.Z` and updates `uv.lock`. The stable release should otherwise contain the same code as the final release candidate.

## Create and Publish GitHub Release

5. Create GitHub release (this will automatically publish to PyPI)

   - Go to the repository's **Releases** page
   - Click **"Draft a new release"**
   - Create or select the tag that exactly matches the project version with a leading `v`
   - Target the merged release commit on `main`
   - Fill in the release title: `vX.Y.Z - Month D, YYYY`
   - For an RC, select **Set as a pre-release** and do not set it as latest
   - Add release notes:
     - Highlight key features and changes
     - Include breaking changes (if any)
     - Reference relevant issues/PRs
   - Click **"Publish release"**

6. Automated PyPI publication

   - The [Publish Package to PyPI](../.github/workflows/release.yml) workflow will automatically trigger
   - The workflow will:
     - Extract version from `pyproject.toml`
     - Check if version already exists on PyPI (prevents duplicates)
     - Build the package with `uv build`
     - Publish to PyPI using trusted publishing (OIDC)
   - Monitor the workflow in the **Actions** tab to confirm successful publication
   - Package will be available at: `https://pypi.org/project/sap-cloud-sdk/X.Y.Z/`

> **Note:** The version in `pyproject.toml` must match the release tag (without the 'v' prefix). For example, tag `vX.Y.Z` requires `version = "X.Y.Z"` in `pyproject.toml`.

## Install and Verify

Install a specific release candidate explicitly:

```bash
pip install sap-cloud-sdk==1.0.0rc1
```

Install the current stable release normally:

```bash
pip install sap-cloud-sdk
```
