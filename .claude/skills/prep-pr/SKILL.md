---
name: prep-pr
description: Fill in the pull request template for the current branch. Diffs the current branch against its base branch (or reads the existing PR diff), infers description, type of change, testing steps, breaking changes, and checklist state, then either creates a new PR or edits the body of an existing one.
tools: Bash, Read
compatibility: gh CLI ≥ 2.0, git, GitHub access to SAP/cloud-sdk-python
---

# PR Prep: SAP Cloud SDK for Python

Fills in `.github/pull_request_template.md` from the diff of the current branch against its base, then creates or updates the GitHub PR.

---

## Phase 1: Pre-flight

Run in parallel:

```bash
# 1a. Current branch name
git rev-parse --abbrev-ref HEAD

# 1b. Confirm branch is pushed to origin
git ls-remote --heads origin $(git rev-parse --abbrev-ref HEAD)

# 1c. Check if a PR already exists for this branch
gh pr list --repo SAP/cloud-sdk-python --head $(git rev-parse --abbrev-ref HEAD) \
  --json number,title,url,state,baseRefName --jq '.[0] // empty'
```

**Fail fast** if `1b` returns empty — the branch is not on origin. Tell the user:
> "Push the branch first (`git push -u origin HEAD`), then re-run `/prep-pr`." Stop.

Capture:
- `CURRENT_BRANCH` — from 1a
- `EXISTING_PR` — from 1c (number, url, baseRefName — or empty if none)
- `BASE_BRANCH` — from `EXISTING_PR.baseRefName` if a PR exists; otherwise `main`

---

## Phase 2: Gather the diff

If `EXISTING_PR` exists, fetch the actual PR diff from GitHub (most accurate, includes only what the PR changes):

```bash
gh pr diff {EXISTING_PR.number} --repo SAP/cloud-sdk-python
```

Otherwise diff the branch against its base locally:

```bash
git fetch origin {BASE_BRANCH}
git diff origin/{BASE_BRANCH}...HEAD
```

Also get the commit log and changed file list in parallel:

```bash
# Commits on this branch not in base
git log origin/{BASE_BRANCH}...HEAD --pretty=format:"%H %s" --reverse

# Changed file paths only
git diff origin/{BASE_BRANCH}...HEAD --name-only
```

If the log is empty, tell the user: "No commits ahead of `{BASE_BRANCH}`. Nothing to open a PR for." Stop.

---

## Phase 3: Analyse the changes

### 3.1 Classify the change types

Read the commit subjects and diff. Determine which of the following apply:

| Type | Signal |
|---|---|
| **Bug fix** | `fix(...)` commits, regression tests added |
| **New feature** | `feat(...)` commits, new public classes/methods/exports |
| **Breaking change** | Removed/renamed public API, changed return types, made optional params required, `!` in commit subject or `BREAKING CHANGE` footer |
| **Documentation update** | Only `docs/` or docstring changes |
| **Code refactoring** | `refactor(...)` commits, no API surface change |
| **Dependency update** | Changes to `pyproject.toml` dependency pins only |

More than one type can apply.

### 3.2 Detect breaking changes

A change is breaking if any of the following are true in the diff:
- A public function/method signature in `src/` was removed or renamed
- A required parameter was added to a public method
- A return type of a public method changed incompatibly
- A public class was removed or renamed
- A commit subject contains `!` after the type/scope (e.g. `feat!:`) or a `BREAKING CHANGE:` trailer

### 3.3 Infer the related issue number

Check commit messages and the branch name for a `#NNN` reference or an issue number pattern (e.g. branch `fix/123-something`). If found, use it as the linked issue. If not found, leave the placeholder `Closes #<issue_number>` and note it in the summary.

### 3.4 Draft testing steps

From the changed files and commit messages, derive 2–4 concrete steps a reviewer can follow to verify the change. Steps should be specific to the actual code changed (function names, CLI commands, env var names) — not generic placeholders.

### 3.5 Evaluate the checklist

For each checklist item, determine the most accurate state given what you can observe in the diff:

| Item | How to evaluate |
|---|---|
| Read Contributing Guidelines | Always `[x]` — assume the contributor has read them |
| Changes solve the issue | `[x]` if a `Closes #N` reference is present; `[ ]` otherwise |
| Tests added/updated | `[x]` if `tests/` files changed alongside `src/` changes; `[ ]` if `src/` changed with no test changes |
| All tests pass locally | Always `[ ]` — leave for the author to confirm |
| Code follows guidelines | `[x]` if pre-commit/ruff checks pass in CI; `[ ]` if unsure |
| Documentation updated | `[x]` if `docs/` or `user-guide.md` files changed; `[ ]` if new public API was added without docs |
| Type hints for public APIs | `[x]` if all new/modified public functions have return types and parameter annotations in the diff; `[ ]` if any are missing |
| No sensitive information | Always `[x]` — flag in summary if anything suspicious was found in Phase 3 |
| Conventional Commits | `[x]` if all commit subjects match the pattern; `[ ]` if any don't |

---

## Phase 4: Build the PR body

Fill in the template exactly as structured below. Remove the `## Breaking Changes` section entirely if no breaking changes were detected. Remove `## Additional Notes` if there is nothing meaningful to add.

```markdown
> **Disclaimer:** Do not include SAP-internal or customer-specific information in this PR (e.g. internal system URLs, customer names, tenant IDs, or confidential configurations). This is a public repository.

## Description

<clear, specific description of what changed and why — reference class/method names, module paths, and the motivation. 2–5 sentences.>

## Related Issue

Closes #<issue_number>

## Type of Change

- [x or space] Bug fix (non-breaking change that fixes an issue)
- [x or space] New feature (non-breaking change that adds functionality)
- [x or space] Breaking change (fix or feature that would cause existing functionality to change)
- [x or space] Documentation update
- [x or space] Code refactoring
- [x or space] Dependency update

## How to Test

<numbered steps specific to the actual changes — not generic>

## Checklist

- [x or space] I have read the [Contributing Guidelines](../CONTRIBUTING.md)
- [x or space] I have verified that my changes solve the issue
- [x or space] I have added/updated automated tests to cover my changes
- [ ] All tests pass locally
- [x or space] I have verified that my code follows the [Code Guidelines](../docs/GUIDELINES.md)
- [x or space] I have updated documentation (if applicable)
- [x or space] I have added type hints for all public APIs
- [x] My code does not contain sensitive information (credentials, tokens, etc.)
- [x or space] I have followed [Conventional Commits](https://www.conventionalcommits.org/) for commit messages

## Breaking Changes

<only include this section if breaking changes were detected>
- What breaks: <specific API surface that changed>
- Migration path: <what callers must update>
- Alternative approaches considered: <or "N/A">

## Additional Notes

<relevant context for reviewers — remove this section if nothing to add>
```

---

## Phase 5: Create or update the PR

### If no existing PR (`EXISTING_PR` is empty):

Propose a PR title using the Conventional Commit format derived from the dominant change type:
- Single commit: use its subject directly
- Mixed commits: synthesise a title like `feat(scope): add X and fix Y`

Show the user the proposed title, base branch, and body. Ask:
> "Ready to create the PR targeting `{BASE_BRANCH}` with this title and body? Reply `yes`, `no`, or provide an alternate title."

On confirmation, run:

```bash
gh pr create \
  --repo SAP/cloud-sdk-python \
  --base {BASE_BRANCH} \
  --head {CURRENT_BRANCH} \
  --title "{PROPOSED_TITLE}" \
  --body "{PR_BODY}"
```

### If PR already exists (`EXISTING_PR` has a number):

Show the user the proposed body and ask:
> "PR #{NUMBER} already exists ({URL}), targeting `{BASE_BRANCH}`. Update its body with this content? Reply `yes` or `no`."

On confirmation, run:

```bash
gh pr edit {NUMBER} \
  --repo SAP/cloud-sdk-python \
  --body "{PR_BODY}"
```

---

## Phase 6: Summary

After creating or updating the PR, print:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PR Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PR:      #{NUMBER} — {URL}
  Branch:  {CURRENT_BRANCH} → {BASE_BRANCH}
  Action:  created | updated

  Items needing manual attention:
  - <list any checklist boxes left unchecked and why>
  - <issue number if not found automatically>
  - <any other gaps>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
