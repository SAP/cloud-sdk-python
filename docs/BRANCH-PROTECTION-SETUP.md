# Branch Protection Setup — sdk-module-review as required check

This guide is for **repo admins**. It documents how to configure the
`sdk-module-review` action as a required status check so that PRs cannot be
merged until the review passes.

Once configured, every PR against `main` will be blocked from merge until:
1. The `sdk-module-review` action runs
2. The action reports success (no `BLOCK` findings)
3. All other required checks (existing CI, REUSE, etc.) also pass

---

## Prerequisites

- You have **admin** permission on the repo
- The `feat/sdk-review-skill` PR has been merged to `main`, so
  `.github/workflows/sdk-module-review.yml` is live
- At least one PR has run the workflow successfully (so GitHub knows the
  check-name `sdk-module-review` exists — required checks can only be added
  after they've fired at least once)

## Steps (GitHub UI)

1. Navigate to **Settings → Branches → Branch protection rules**
2. If a rule already exists for `main`, edit it. Otherwise click **Add rule**
   and enter `main` as the branch name pattern.
3. Under **Protect matching branches**, enable:
   - ☑ **Require a pull request before merging**
     - ☑ Require approvals: `1` (or more per team convention)
     - ☑ Dismiss stale pull request approvals when new commits are pushed
     - ☑ Require review from Code Owners
   - ☑ **Require status checks to pass before merging**
     - ☑ Require branches to be up to date before merging
     - In the search box, add:
       - `sdk-module-review` ← our skill
       - `test` (or whatever the existing CI is called)
       - `reuse` (if REUSE-check is used)
   - ☑ **Require conversation resolution before merging**
   - ☑ **Do not allow bypassing the above settings** (admins included)
4. Click **Create** or **Save changes**

## Steps (via gh CLI, alternative)

```bash
# cloud-sdk-python (public GitHub)
gh api -X PUT "repos/SAP/cloud-sdk-python/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["sdk-module-review", "test", "reuse"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_conversation_resolution": true
}
EOF

# cloud-sdk-java (internal GHES)
gh api --hostname github.tools.sap -X PUT \
  "repos/application-foundation/cloud-sdk-java/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["sdk-module-review", "ci", "codeql-sast-analysis"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null
}
EOF
```

Adjust the `contexts` list to include the CI check-names actually used by the
repo (see the "Checks" tab of any recent PR to confirm the exact names).

## Verify

After configuration, open a test PR (or use any open PR):

```bash
gh pr view <PR_NUMBER> --json statusCheckRollup -q '.statusCheckRollup[].name'
```

You should see `sdk-module-review` in the list. If the check hasn't run yet
(never fired on this branch), it will appear as "expected" (pending).

## Rollout stages

We recommend a **SHADOW → FLAG → BLOCK** progression to minimise contributor
friction:

### Stage 1 — SHADOW (weeks 1–2)

- The workflow runs on every PR but **rules are downgraded to `SHADOW`**
- Findings are logged to `.claude/telemetry/*.jsonl` but **not posted to the PR**
- Contributors are unaffected; maintainers observe FP rate

To enable SHADOW mode, edit `.claude/config/rules.yaml`:
```yaml
rules:
  # temporarily downgrade all BLOCK to SHADOW for first two weeks
  BND-02: { tier: SHADOW }
  BREAKING-01: { tier: SHADOW }
  # ... etc
```

Or set an env var in the workflow: `SDK_REVIEW_TIER_OVERRIDE=shadow-all`.

### Stage 2 — FLAG (weeks 3–4)

- Rules promoted to `FLAG` — findings posted as inline comments and summary,
  but check-run is **not** required for merge
- Contributors see the review and can act on it
- Maintainers verify FP rate stays < 5 % on real PRs

### Stage 3 — BLOCK (week 5+)

- `sdk-module-review` added as required status check (this document's main topic)
- Merges blocked on `BLOCK` findings
- `BLOCK_LOCKED` rules (secrets, SPDX in public, token URL concat, breaking
  changes without declaration) are non-suppressible

## Rollback

If `sdk-module-review` fires too aggressively and needs to be turned off:

1. Remove `sdk-module-review` from the required-checks list (via UI or `gh api`)
2. Or disable the workflow entirely: `.github/workflows/sdk-module-review.yml` →
   set `on: workflow_dispatch` only (no auto-triggers)
3. Individual noisy rules can be downgraded in `.claude/config/rules.yaml`:
   ```yaml
   rules:
     RULE-ID: { tier: FLAG }   # was BLOCK; downgrade to advisory
     RULE-ID: { tier: SHADOW } # or silence entirely
   ```

`BLOCK_LOCKED` rules cannot be downgraded via config — they are safety-critical
(secrets, license, disclosure in public repo, BTP token URL concat). To
temporarily disable one, remove it from `rules.yaml` altogether and open a
follow-up issue to reintroduce it.

## Troubleshooting

- **Check-run not appearing on new PRs**: verify the workflow file
  `.github/workflows/sdk-module-review.yml` is present on `main` and the
  action has permissions `contents: read`, `pull-requests: write`,
  `checks: write`, `issues: write` (for labels)
- **Check-run runs but never completes**: check the workflow logs for auth
  errors (`gh auth status`) or missing `SIBLING_SDK_TOKEN` secret (cross-repo
  BDD parity is optional — degrades to `FLAG` if unavailable)
- **False positives**: see `docs/PR-REVIEW.md § Suppressing false positives`
  and `§ Tuning noisy rules`
- **Required check missing from branch protection dropdown**: the check must
  have fired at least once on any branch before GitHub lists it. Open a
  throwaway PR to trigger it, or dispatch the workflow manually:
  ```bash
  gh workflow run sdk-module-review.yml -f pr_number=<N>
  ```

## Cross-references

- [`docs/PR-REVIEW.md`](./PR-REVIEW.md) — user-facing docs on what the skill checks
- [`.claude/config/rules.yaml`](../.claude/config/rules.yaml) — rule catalog with tiers
- [`.claude/config/baseline.json`](../.claude/config/baseline.json) — repo-specific exemptions
- [`.github/workflows/sdk-module-review.yml`](../.github/workflows/sdk-module-review.yml) — the workflow
