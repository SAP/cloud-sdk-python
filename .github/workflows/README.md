# GitHub Actions Workflows

This directory contains the CI/CD workflows for the SAP Cloud SDK for Python.

## Workflow Structure

The CI pipeline is split into three independent workflows for optimal performance and security:

### 1. Code Quality Checks (`checks.yaml`)

**Trigger**: `pull_request` (runs on all PRs)
**Purpose**: Fast feedback on code style and type safety
**Jobs**:
- `lint` - Ruff linter checks
- `format` - Ruff formatter checks
- `typecheck` - ty type checker

**Parallelization**: All jobs run in parallel (~1-2 min total)

**Security**:
- Uses `pull_request` trigger (read-only by default)
- ✅ SAFE: Only runs static analysis tools (no code execution)
- ❌ NO secrets or write permissions

**Fork-friendly**: Contributors get immediate feedback on code quality checks.

### 2. Tests & Coverage (`test.yaml`)

**Trigger**: `pull_request` (runs on all PRs)
**Purpose**: Run tests and report coverage
**Jobs**:
- `test` - Unit tests with coverage reporting

**Permissions**:
- `contents: read` - Read-only access

**Security**:
- Uses `pull_request` trigger (read-only)
- Coverage visible in workflow summary

### 3. Build & Package (`build.yaml`)

**Trigger**: `pull_request` (requires approval for fork PRs)
**Purpose**: Build and verify distribution packages
**Jobs**:
- `build` - Creates wheel and source distributions

**Artifacts**:
- Uploads built packages for 7 days

## Workflow Execution Flow

```
Fork PR opened
    ↓
┌─────────────────────────────────────────┐
│  checks.yaml (auto-runs)                │
│  ├─ lint (parallel)                     │
│  ├─ format (parallel)                   │
│  └─ typecheck (parallel)                │
└─────────────────────────────────────────┘
    ↓ (1-2 min)
    ✓ Quick feedback to contributor

    ↓ (Runs in parallel)

┌─────────────────────────────────────────┐
│  test.yaml (auto-runs)                  │
│  └─ test (with coverage)                │
└─────────────────────────────────────────┘
    ↓ (3-5 min)

    ↓ (Maintainer clicks "Approve and run")

┌─────────────────────────────────────────┐
│  build.yaml (requires approval)         │
│  └─ build (package creation)            │
└─────────────────────────────────────────┘
    ↓ (1-2 min)

    ✓ All checks passed, ready to merge
```

## Benefits

### For Contributors
- **Immediate feedback** on code style and tests
- **Faster iteration** - fix issues quickly
- **Clear separation** of concerns in CI status

### For Maintainers
- **Parallel execution** - faster CI overall (~3-5 min vs ~8-10 min)
- **Security** - limited permissions for all workflows
- **Selective approval** - only approve build jobs

## Security Considerations

### Why Build Requires Approval

The `build.yaml` workflow requires approval because it:
- Creates distribution packages
- May access secrets in the future (e.g., PyPI tokens)

## Local Development

Run checks locally before pushing:

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check .

# Tests
uv run pytest -m "not integration"

# Build
uv build
```

## Troubleshooting

### Fork PR workflows not running?

1. **checks.yaml/test.yaml not running**: Check if Actions are enabled in repository settings
2. **build.yaml not running**: Requires manual approval for fork PRs - look for "Approve and run" button

### All workflows require approval?

This means fork PR workflows are disabled in repository settings:
1. Go to Settings → Actions → General
2. Enable "Fork pull request workflows from outside collaborators"
3. Select "Require approval for first-time contributors"

## References

- [GitHub Actions: Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [Keeping your GitHub Actions secure](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Using pull_request_target safely](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/)
