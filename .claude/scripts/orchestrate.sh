#!/usr/bin/env bash
# orchestrate.sh — main entry point. Runs all 20 checks and posts results.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$SCRIPT_DIR/lib"

# shellcheck source=lib/json-emit.sh
source "$LIB/json-emit.sh"
# shellcheck source=lib/github-api.sh
source "$LIB/github-api.sh"

PR_NUMBER="${1:-}"
DRY_RUN="${DRY_RUN:-false}"
if [ "${2:-}" = "--dry-run" ]; then DRY_RUN=true; fi

if [ -z "$PR_NUMBER" ]; then
  echo "Usage: orchestrate.sh <PR_NUMBER> [--dry-run]" >&2
  exit 2
fi

REPO_ROOT="${REPO_ROOT:-$(pwd)}"
export REPO_ROOT
CONFIG_DIR="$REPO_ROOT/.claude/config"
export CONFIG_DIR
if [ -n "${TMPDIR_RUN:-}" ]; then
  mkdir -p "$TMPDIR_RUN"
else
  TMPDIR_RUN="$(mktemp -d)"
fi
trap '[ -n "${KEEP_TMP:-}" ] || rm -rf "$TMPDIR_RUN"' EXIT

echo "▶ SDK Module Review — PR #$PR_NUMBER (dry-run=$DRY_RUN)"
echo "  Working dir: $TMPDIR_RUN"

# 1. Preflight — detect language + hostname + fetch PR data
LANGUAGE=$("$LIB/detect-language.sh" "$REPO_ROOT")
export LANGUAGE
echo "  Language: $LANGUAGE"

if [ "$DRY_RUN" != "true" ]; then
  HOSTNAME=$(detect_hostname)
  check_gh_auth "$HOSTNAME"
fi

# 2. Fetch diff + PR metadata
if [ -f "${DIFF_FILE:-}" ]; then
  cp "$DIFF_FILE" "$TMPDIR_RUN/pr.diff"
elif [ "$DRY_RUN" = "true" ] && [ -n "${LOCAL_DIFF:-}" ]; then
  cp "$LOCAL_DIFF" "$TMPDIR_RUN/pr.diff"
else
  gh pr diff "$PR_NUMBER" > "$TMPDIR_RUN/pr.diff"
fi

if [ "$DRY_RUN" != "true" ]; then
  gh pr view "$PR_NUMBER" --json body -q .body > "$TMPDIR_RUN/pr-body.txt" 2>/dev/null || echo "" > "$TMPDIR_RUN/pr-body.txt"
  HEAD_SHA=$(get_pr_head_sha "$PR_NUMBER")
elif [ -n "${LOCAL_PR_BODY:-}" ] && [ -f "$LOCAL_PR_BODY" ]; then
  cp "$LOCAL_PR_BODY" "$TMPDIR_RUN/pr-body.txt"
  HEAD_SHA="${HEAD_SHA:-HEAD}"
else
  echo "" > "$TMPDIR_RUN/pr-body.txt"
  HEAD_SHA="${HEAD_SHA:-HEAD}"
fi

export DIFF_FILE="$TMPDIR_RUN/pr.diff"
export PR_BODY_FILE="$TMPDIR_RUN/pr-body.txt"
export HEAD_SHA
export BASE_SHA="${BASE_SHA:-$(git merge-base origin/main HEAD 2>/dev/null || echo HEAD~10)}"
export BREAKING_JSON="$TMPDIR_RUN/breaking.json"

# 3. Compute added-lines set (used for hunk attribution)
"$LIB/diff-added-lines.sh" < "$DIFF_FILE" > "$TMPDIR_RUN/added-lines.txt"
export ADDED_LINES_FILE="$TMPDIR_RUN/added-lines.txt"

# 4. Run breaking-change detector
python3 "$LIB/breaking-detector.py" "$BASE_SHA" "$HEAD_SHA" > "$BREAKING_JSON" 2>/dev/null || echo '{"breaking_detected":false,"kinds":[],"details":[]}' > "$BREAKING_JSON"

# 5. Detect disclosure profile from remote
if [ "$DRY_RUN" != "true" ]; then
  remote_url=$(git remote get-url origin 2>/dev/null || echo "")
  if [[ "$remote_url" == *"github.tools.sap"* ]]; then
    export DISCLOSURE_PROFILE="internal"
  else
    export DISCLOSURE_PROFILE="public"
  fi
else
  export DISCLOSURE_PROFILE="${DISCLOSURE_PROFILE:-public}"
fi

# 6. Run all 20 checks in parallel
checks=(secrets license-spdx disclosure hardcode telemetry
        docs bdd patterns versioning commits
        errors-logging testing-depth http-hygiene concurrency
        deps-supply deletion-hygiene constants binding-shape
        quality-gate-parity pr-size)

for check in "${checks[@]}"; do
  script="$SCRIPT_DIR/check-${check}.sh"
  if [ ! -x "$script" ]; then continue; fi
  DIFF_FILE="$DIFF_FILE" PR_BODY_FILE="$PR_BODY_FILE" \
    "$script" < "$DIFF_FILE" > "$TMPDIR_RUN/report-${check}.json" 2> "$TMPDIR_RUN/${check}.err" &
done
wait

# 6.5. Collect suppression tuples from files touched by the diff, then filter each report
touched_files=$(grep -oE '^\+\+\+ b/[^[:space:]]+' "$DIFF_FILE" 2>/dev/null | sed 's|^+++ b/||' | sort -u || true)
supp_file="$TMPDIR_RUN/suppressions.txt"
: > "$supp_file"
if [ -n "$touched_files" ]; then
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$REPO_ROOT/$f" ] || continue
    bash "$LIB/suppression.sh" parse_line "$REPO_ROOT/$f" 2>/dev/null | sed "s|^$REPO_ROOT/|| ; s|^\./||" >> "$supp_file" || true
    bash "$LIB/suppression.sh" parse_file "$REPO_ROOT/$f" 2>/dev/null | sed "s|^$REPO_ROOT/|| ; s|^\./||" >> "$supp_file" || true
  done <<< "$touched_files"
fi

for check in "${checks[@]}"; do
  report="$TMPDIR_RUN/report-${check}.json"
  [ -f "$report" ] || continue
  filtered=$(bash "$LIB/apply-suppression.sh" apply "$report" "$supp_file" 2>/dev/null || cat "$report")
  echo "$filtered" > "$report"
done

# 7. Aggregate reports (applies tier gating per rules.yaml)
RULES_YAML="$REPO_ROOT/.claude/config/rules.yaml" \
  "$SCRIPT_DIR/aggregate.sh" "$TMPDIR_RUN" > "$TMPDIR_RUN/summary.json"

# 8. Post signals (unless dry-run)
if [ "$DRY_RUN" = "true" ]; then
  echo ""
  echo "▶ DRY-RUN summary:"
  jq -r '
    "  BLOCK: \(.summary.block_count)  FLAG: \(.summary.flag_count)  SHADOW: \(.summary.shadow_count)",
    "",
    "Findings:",
    (.findings[] | "  [\(.severity)] \(.rule) at \(.file):\(.line) — \(.message)")
  ' "$TMPDIR_RUN/summary.json"
  echo ""
  echo "▶ Full report at: $TMPDIR_RUN/summary.json"
  exit "$(jq -r '.summary.block_count | if . > 0 then 1 else 0 end' "$TMPDIR_RUN/summary.json")"
fi

# 9. Idempotency: delete prior bot artifacts
delete_prior_bot_artifacts "$PR_NUMBER"

# 10. Post inline comments
n_inline=$(jq '.findings | length' "$TMPDIR_RUN/summary.json")
i=0
while [ "$i" -lt "$n_inline" ]; do
  f=$(jq -c ".findings[$i]" "$TMPDIR_RUN/summary.json")
  file=$(echo "$f" | jq -r '.file')
  line=$(echo "$f" | jq -r '.line')
  rule=$(echo "$f" | jq -r '.rule')
  sev=$(echo "$f" | jq -r '.severity')
  msg=$(echo "$f" | jq -r '.message')
  body="<!-- sdk-review:v1 check=$rule id=$rule-$i -->
**[$sev] $rule**

$msg"
  post_inline_comment "$PR_NUMBER" "$HEAD_SHA" "$file" "$line" "$body" || true
  i=$((i + 1))
done

# 11. Post summary comment
summary_body=$(jq -r '
  "<!-- sdk-review:v1 kind=summary -->
## SDK Module Review

| Check | Status | Findings |
|-------|--------|----------|
" + (.per_check_summary | to_entries | map("| \(.key) | \(.value.status) | \(.value.count) |") | join("\n")) + "

<details><summary>Details</summary>

" + (.findings | map("- **[\(.severity)] \(.rule)** at `\(.file):\(.line)` — \(.message)") | join("\n")) + "

</details>

---
_Generated by sdk-review-skill · v1_"
' "$TMPDIR_RUN/summary.json")

post_summary_comment "$PR_NUMBER" "$summary_body"

# 12. Post check-run
conclusion=$(jq -r 'if .summary.block_count > 0 then "failure" elif .summary.flag_count > 0 then "neutral" else "success" end' "$TMPDIR_RUN/summary.json")
title=$(jq -r "\"SDK Review: \(.summary.block_count) BLOCK, \(.summary.flag_count) FLAG\"" "$TMPDIR_RUN/summary.json")
post_or_update_check_run "$HEAD_SHA" "$conclusion" "$title" "$summary_body"

# 13. Apply label
case "$conclusion" in
  success) label="sdk-review: ✅ passed" ;;
  neutral) label="sdk-review: ⚠️ flagged" ;;
  failure) label="sdk-review: ❌ blocked" ;;
esac
apply_label "$PR_NUMBER" "$label"

# 14. Exit
exit "$(jq -r '.summary.block_count | if . > 0 then 1 else 0 end' "$TMPDIR_RUN/summary.json")"
