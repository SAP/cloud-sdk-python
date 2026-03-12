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

## Release and Deployment

For the end-to-end process to cut a release and publish artifacts, see the [Release and Deployment Guide](RELEASE.md).:

## Contributing
For guidance on contributing with new features, see the [Contributing Guide](../CONTRIBUTING.md).
