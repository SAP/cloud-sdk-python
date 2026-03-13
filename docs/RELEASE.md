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

3. Update changelog
   - Use the official Changelog template

4. Commit changes
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "feat: did something"
   ```

5. Push and open PR, get approval and merge
   ```bash
   git push -u origin branch-name
   ```
   - Merge commit message should follow Conventional Commits
   - Example: `feat(): add xyz`
   - See: [Conventional Commits](https://www.conventionalcommits.org/)

## Create and Publish GitHub Release

6. Create GitHub release (this will automatically publish to PyPI)
   - Go to the repository's **Releases** page
   - Click **"Draft a new release"**
   - Choose the tag: `vX.Y.Z` (or create new tag from main)
   - Fill in the release title: `vX.Y.Z`
   - Add release notes:
     - Highlight key features and changes
     - Include breaking changes (if any)
     - Reference relevant issues/PRs
     - Use the changelog as reference
   - Click **"Publish release"**

7. Automated PyPI publication
   - The [Publish Package to PyPI](../.github/workflows/release.yaml) workflow will automatically trigger
   - The workflow will:
     - Extract version from `pyproject.toml`
     - Check if version already exists on PyPI (prevents duplicates)
     - Build the package with `uv build`
     - Publish to PyPI using trusted publishing (OIDC)
   - Monitor the workflow in the **Actions** tab to confirm successful publication
   - Package will be available at: `https://pypi.org/project/sap-cloud-sdk/X.Y.Z/`

> **Note:** The version in `pyproject.toml` must match the release tag (without the 'v' prefix). For example, tag `vX.Y.Z` requires `version = "X.Y.Z"` in `pyproject.toml`.