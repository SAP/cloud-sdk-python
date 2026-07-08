#!/usr/bin/env bash
# check-pr-size.sh — advisory on large PRs (all FLAG tier, initially SHADOW).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
# Resolve BASE_SHA from the PR base ref rather than HEAD~10.
if [ -z "${BASE_SHA:-}" ]; then
  base_ref="${GITHUB_BASE_REF:-main}"
  if git rev-parse --verify "origin/${base_ref}" >/dev/null 2>&1; then
    BASE_SHA=$(git merge-base HEAD "origin/${base_ref}" 2>/dev/null || echo "HEAD~10")
  elif git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
    BASE_SHA=$(git merge-base HEAD "$base_ref" 2>/dev/null || echo "HEAD~10")
  else
    BASE_SHA="HEAD~10"
  fi
fi
HEAD_SHA="${HEAD_SHA:-HEAD}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Helper: `grep -c` returns "0" AND exit 1 on no match. Under `set -e` /
# pipefail the || echo 0 idiom concatenates both, producing "0\n0" and
# breaking arithmetic. Route through wc -l instead.
count_lines() { echo "$1" | { grep -E "$2" 2>/dev/null || true; } | wc -l | tr -d ' '; }

# PR-SIZE-01: additions > 800
additions=$(count_lines "$diff_content" '^\+[^+]')
if [ "$additions" -gt 800 ]; then
  emit_finding "PR-SIZE-01" "FLAG" "." 1 \
    "PR has $additions additions (>800) — consider splitting into stacked PRs for easier review" \
    "See docs/CONTRIBUTING.md § Incremental Delivery for stacked-PR workflow" >> "$findings"
fi

# PR-SIZE-02: > 15 files
files_touched=$(count_lines "$diff_content" '^diff --git')
if [ "$files_touched" -gt 15 ]; then
  emit_finding "PR-SIZE-02" "FLAG" "." 1 \
    "PR touches $files_touched files (>15) — consider splitting by concern" "" >> "$findings"
fi

# PR-SIZE-03: > 3 modules
if [ "$LANGUAGE" = "python" ]; then
  mods_count=$(echo "$diff_content" | { grep -oE 'src/sap_cloud_sdk/[a-z_]+/' 2>/dev/null || true; } | sed 's|src/sap_cloud_sdk/||; s|/$||' | sort -u | wc -l | tr -d ' ')
else
  mods_count=$(echo "$diff_content" | { grep -oE 'src/main/java/com/sap/cloud/sdk/[a-z_]+/' 2>/dev/null || true; } | sed 's|src/main/java/com/sap/cloud/sdk/||; s|/$||' | sort -u | wc -l | tr -d ' ')
fi
if [ "$mods_count" -gt 3 ]; then
  emit_finding "PR-SIZE-03" "FLAG" "." 1 \
    "PR modifies $mods_count modules (>3) — consider one PR per module" "" >> "$findings"
fi

# PR-SIZE-05: > 30 commits (exclude merge commits by looking at parents)
commit_count=$(git log "${BASE_SHA}..${HEAD_SHA}" --no-merges --oneline 2>/dev/null | wc -l | tr -d ' ')
if [ "$commit_count" -gt 30 ]; then
  emit_finding "PR-SIZE-05" "FLAG" "." 1 \
    "PR has $commit_count commits (>30) — consider squashing or splitting" "" >> "$findings"
fi

status=$(status_from_findings < "$findings")
emit_report "pr-size" "$LANGUAGE" "$status" "$STARTED" < "$findings"
