# /review-new-module — orchestrator slash command
Run the SDK Module Review skill against a PR.

## Usage
- `/review-new-module <PR_NUMBER>` — full review, posts findings
- `/review-new-module <PR_NUMBER> --dry-run` — analysis only, no posting

## What it does
1. Detects language (Python vs Java) via `pyproject.toml` / `pom.xml`
2. Fetches PR diff + body
3. Runs 20 deterministic checks in parallel (secrets, license, disclosure, hardcode, telemetry, docs, bdd, patterns, versioning, commits, errors-logging, testing-depth, http-hygiene, concurrency, deps-supply, deletion-hygiene, constants, binding-shape, quality-gate-parity, pr-size)
4. Applies baseline exemptions + scope predicates + tier gating
5. Detects breaking changes via AST diff
6. Posts 4 signals: inline comments, summary comment, check-run, label

## Implementation
Run: `bash .claude/scripts/orchestrate.sh <PR_NUMBER>`

The orchestrator is 100% deterministic — no LLM calls in CI. When run inside Claude Code, the LLM can enrich the summary comment before posting (this happens naturally in the session).
