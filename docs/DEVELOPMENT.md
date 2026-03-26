# Development Guide

## Requirements

- Python 3.11+
- uv (package manager)
- Docker

## Setup

```bash
# Clone the repository
git clone https://github.com/SAP/cloud-sdk-python.git
cd cloud-sdk-python

# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install all development dependencies
uv sync --all-extras --group dev
```

Activation notes:
- macOS/Linux (bash/zsh): `source .venv/bin/activate`
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`

Tip:
- After changing `pyproject.toml`, run `uv sync` again to update dependencies.

## Type Check

```bash
uv run ty check .
```

## Code Quality Checks

Run all quality checks before committing:

```bash
# Lint
uv run ruff check .

# Format check
uv run ruff format --check .

# Type check
uv run ty check .
```

## Pre-commit Hooks (Recommended)

Automatically run quality checks before each commit using pre-commit hooks.

### Setup

1. **Install pre-commit:**
   ```bash
   uv pip install pre-commit
   ```

2. **Install the git hooks:**
   ```bash
   pre-commit install
   ```

3. **Run on all files (one-time init):**
   ```bash
   pre-commit run --all-files
   ```

### What It Does

The `.pre-commit-config.yaml` file configures hooks to:
- Check YAML files
- Fix end-of-file issues
- Remove trailing whitespace
- Run `ruff format --check` (code formatting)
- Run `ruff check --fix` (linting with auto-fix)
- Run `ty check` (type checking)

Hooks run automatically on `git commit`. If checks fail, the commit is blocked until issues are fixed.

### Manual Hook Execution

Run hooks manually without committing:
```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run ruff-check
```

## Build Project

```bash
uv build
```

## Code Guidelines

- [Code Guidelines](GUIDELINES.md)

## Tests

```bash
# All tests
uv run pytest -v

# Unit tests only (exclude integration)
uv run pytest -m "not integration" -q

# Integration tests (see INTEGRATION_TESTS.md)
uv run pytest -m integration -v
```

See [Integration Tests](INTEGRATION_TESTS.md) for more details on integration testing.

### Coverage

```bash
# Basic coverage
uv run pytest --cov=src
```

## Validating changes in a real application

Sometimes we want to validate our changes in a real application before publishing them to PyPI. It's extremely important to test like that to ensure that there are no issues with our changes and we encourage contributors to do so.

For that, we can reference the package using the GitHub endpoint in the `requirements.txt` or `pyproject.toml` of the test application. This way, we can install the package directly from the branch, commit, or tag that contains our changes without needing to publish it to PyPI first.

Using `requirements.txt`:

```bash
# Other dependencies...
sap-cloud-sdk @ git+https://github.com/sap/cloud-sdk-python@<branch-or-commit-or-tag>
# You also could use your forked repository if you have one, for example:
sap-cloud-sdk @ git+https://github.com/your-username/cloud-sdk-python@<branch-or-commit-or-tag>
```

Using `pyproject.toml`:

```toml
dependencies = [
    # Other dependencies...
    "sap-cloud-sdk @ git+https://github.com/sap/cloud-sdk-python@<branch-or-commit-or-tag>"
    # You also could use your forked repository if you have one, for example:
    "sap-cloud-sdk @ git+https://github.com/your-username/cloud-sdk-python@<branch-or-commit-or-tag>"
]
```

See the pip official documentation for more details on installing packages from VCS like Git: [VCS Support](https://pip.pypa.io/en/stable/topics/vcs-support/#vcs-support)

## Release and Deployment

For the end-to-end process to cut a release and publish artifacts, see the [Release and Deployment Guide](RELEASE.md).

## Contributing
For guidance on contributing with new features, see the [Contributing Guide](../CONTRIBUTING.md).
