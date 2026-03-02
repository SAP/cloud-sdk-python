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
   - In `version.txt`: set `vX.Y.Z`

3. Update changelog
   - Use the official Changelog template

4. Commit changes
   ```bash
   git add version.txt pyproject.toml CHANGELOG.md
   git commit -m "feat: did something"
   ```

> Make sure to test your development build before opening the PR. See the [Development Builds](#development-builds) section.

5. Push and open PR, get approval and merge
   ```bash
   git push -u origin branch-name
   ```
   - Merge commit message should follow Conventional Commits
   - Example: `feat(): add xyz`
   - See: [Conventional Commits](https://www.conventionalcommits.org/)

## Tag and Create the GitHub Release

6. Tag on main and push tag
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

7. Create GitHub release
TODO: To be defined

## Publish Artifact (CI/CD)

1. Navigate to the repository’s **Actions** tab
2. Select the **"Release Artifact"** workflow
3. Click **"Run workflow"**
4. Select the branch to deploy from (`main` for releases, your feature branch for test builds)
5. Click **"Run workflow"** to start

## Development Builds
Before merging your branch to main, make sure to deploy a test artifact and test it. Use the standard PEP 440-compliant format:

```
<target_version>.dev<YYYYMMDD>+<description>
```

Examples:
```toml
# Testing new authentication feature
version = "0.2.0.dev20251013+feature.auth"

# Performance improvements
version = "0.1.1.dev20251013+perf.optimization"
```

Format breakdown:
- Target Version: `0.2.0` — next planned release
- Dev Identifier: `.dev` — indicates development version
- Date: `20251013` — creation date (YYYYMMDD)
- Local Separator: `+`
- Description: `feature.auth` — brief description
