# AGENTS.md

Conventions for AI coding agents that work in this repo. This file lists only what is
**not** obvious from the code or already stated elsewhere. For the rest, read
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/`](docs/).

## Tooling

- Use `uv`. Do not use `pip`, `poetry`, or a bare `python`/`python3` command.
- Run these checks before you commit:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run ty check .`
  - `uv run pytest -m "not integration"`
- The `ruff` and `ty` versions are pinned. Do not upgrade them to make a check pass.

## Commits and Pull Requests

- [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <description>`.
- Commit messages use a subject line only. Do not add a commit body.
- Follow the pull request template in `.github/pull_request_template.md`.

## Code

- The package root is `src/sap_cloud_sdk/`. A new module copies the structure of an
  existing one (see `destination` or `objectstore`). Give it full type hints, a `py.typed`
  marker, and both unit and BDD integration tests. See
  [`docs/GUIDELINES.md`](docs/GUIDELINES.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Add telemetry with the `@record_metrics` decorator. See
  [`docs/GUIDELINES.md#telemetry`](docs/GUIDELINES.md#telemetry).

## Guidelines and Conventions

- The `docs/*` files describe the coding guidelines and other conventions. Follow them.

## Security (non-negotiable)

- Never log or show credentials or PII.
- **Fail closed.** If a credential is missing or not valid, refuse the operation. Do not
  fall back to a less secure path.
- Support credential-binding rotation. See
  [`docs/GUIDELINES.md#credential-binding-rotation`](docs/GUIDELINES.md#credential-binding-rotation).

## Workflow

- Start every contribution from an accepted GitHub issue. PRs are fork-based and need a
  DCO sign-off. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
- A PR needs an `sdk-review:` label before it can merge. `/prep-pr` or `/review-pr` adds
  it.
- **Never** change the version in `pyproject.toml` by hand. The release pipeline sets it.
  The `Check Version Bump` CI check blocks a manual change.
- Run `/review-pr` before you open a PR. Also run `/security-review` when you change
  authentication, tenant routing, credential loading, or any code that reads external
  input.
- A new service module needs real-service E2E evidence on the PR
  ([`CONTRIBUTING.md`](CONTRIBUTING.md#6-code-review-and-finalization)).

## Skills

- Project skills live in `.claude/skills/`:
  - `review-pr`: Review pull requests for correctness and adherence to guidelines.
  - `security-review`: Perform security reviews on relevant code changes.
  - `scaffold-module`: Scaffold a new module following project conventions.
  - `prep-pr`: Prepare a pull request for submission, ensuring all checks pass and documentation is updated.
