# Hotfix Guide

This guide describes how to apply a hotfix to a previously released version without including unreleased changes from `main`.

## When to Use This

Use this process when a critical bug is found in a published release and `main` already contains unreleased changes that must not be included in the fix.

## Steps

### 1. Create a branch from the release tag's commit

Find the commit hash the release tag points to:

```bash
git log --oneline --decorate | grep "tag: v"
```

Or look it up directly:

```bash
git rev-list -n 1 vX.Y.Z
```

Create a branch from that commit:

```bash
git checkout -b hotfix/vX.Y.Z+1 <commit-hash>
```

For example, if `v0.36.0` is at `eb6648d`:

```bash
git checkout -b hotfix/v0.36.1 eb6648d
```

### 2. Apply the fix

Make the necessary changes, then bump the patch version in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z+1"
```

### 3. Commit and push

```bash
git add pyproject.toml
git commit -m "fix: <description of the fix>"
git push -u origin hotfix/vX.Y.Z+1
```

### 4. Open a PR against `main` (for tracking)

Even though the hotfix branch is not based on `main`, open a PR so the fix is reviewed and later cherry-picked into `main`.

Cherry-pick the fix commit into `main` after the hotfix is released:

```bash
git checkout main
git cherry-pick <fix-commit-hash>
```

### 5. Create the GitHub Release from the hotfix branch

- Go to the repository's **Releases** page
- Click **"Draft a new release"**
- Create a new tag `vX.Y.Z+1` pointing to the **tip of the hotfix branch** (not `main`)
- Fill in the release title and notes
- Click **"Publish release"**

> **Important:** When creating the tag, make sure it points to the hotfix branch commit, not to `main`. The release workflow checks out the tagged commit, so `pyproject.toml` and all code will be taken from that commit.

### 6. Verify the release

The [Publish Package to PyPI](../.github/workflows/release.yml) workflow will trigger automatically. Monitor the **Actions** tab to confirm the correct version was published.
