#!/usr/bin/env bash
# check-pr-size.sh — advisory on large PRs (all FLAG tier, initially SHADOW).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
BASE_SHA="${BASE_SHA:-HEAD~10}"
HEAD_SHA="${HEAD_SHA:-HEAD}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# PR-SIZE-01: additions > 800
additions=$(echo "$diff_content" | grep -cE '^\+[^+]' || echo 0)
if [ "$additions" -gt 800 ]; then
  emit_finding "PR-SIZE-01" "FLAG" "." 1 \
    "PR has $additions additions (>800) — consider splitting into stacked PRs for easier review" \
    "See docs/CONTRIBUTING.md § Incremental Delivery for stacked-PR workflow" >> "$findings"
fi

# PR-SIZE-02: > 15 files
files_touched=$(echo "$diff_content" | grep -cE '^diff --git' || echo 0)
if [ "$files_touched" -gt 15 ]; then
  emit_finding "PR-SIZE-02" "FLAG" "." 1 \
    "PR touches $files_touched files (>15) — consider splitting by concern" "" >> "$findings"
fi

# PR-SIZE-03: > 3 modules
if [ "$LANGUAGE" = "python" ]; then
  mods_count=$(echo "$diff_content" | grep -oE 'src/sap_cloud_sdk/[a-z_]+/' | sed 's|src/sap_cloud_sdk/||; s|/$||' | sort -u | wc -l | tr -d ' ')
else
  mods_count=$(echo "$diff_content" | grep -oE 'src/main/java/com/sap/cloud/sdk/[a-z_]+/' | sed 's|src/main/java/com/sap/cloud/sdk/||; s|/$||' | sort -u | wc -l | tr -d ' ')
fi
if [ "$mods_count" -gt 3 ]; then
  emit_finding "PR-SIZE-03" "FLAG" "." 1 \
    "PR modifies $mods_count modules (>3) — consider one PR per module" "" >> "$findings"
fi

# PR-SIZE-05: > 30 commits
commit_count=$(git log "${BASE_SHA}..${HEAD_SHA}" --oneline 2>/dev/null | grep -v -c '^Merge' || echo 0)
if [ "$commit_count" -gt 30 ]; then
  emit_finding "PR-SIZE-05" "FLAG" "." 1 \
    "PR has $commit_count commits (>30) — consider squashing or splitting" "" >> "$findings"
fi

status=$(status_from_findings < "$findings")
emit_report "pr-size" "$LANGUAGE" "$status" "$STARTED" < "$findings"
